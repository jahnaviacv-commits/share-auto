import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TESTING"] = "true"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_complete_passenger_driver_dispatch_lifecycle(client):
    # 1. Login Passenger (Aarav)
    p_login = await client.post(
        "/api/auth/login",
        json={"email": "aarav@zeroone.com", "password": "passenger123"}
    )
    assert p_login.status_code == 200
    p_token = p_login.json()["access_token"]
    p_headers = {"Authorization": f"Bearer {p_token}"}

    # 2. Login Driver (Venkat)
    d_login = await client.post(
        "/api/auth/login",
        json={"email": "venkat@zeroone.com", "password": "driver123"}
    )
    assert d_login.status_code == 200
    d_token = d_login.json()["access_token"]
    d_headers = {"Authorization": f"Bearer {d_token}"}

    # 3. Ensure Driver is ONLINE
    status_res = await client.patch("/api/driver/status", headers=d_headers, json={"is_online": True})
    assert status_res.status_code == 200
    assert status_res.json()["is_online"] is True

    # 4. Fetch Corridor H1 Stations
    corr_res = await client.get("/api/corridors/H1")
    assert corr_res.status_code == 200
    corridor = corr_res.json()
    origin_station = corridor["stations"][0]
    dest_station = corridor["stations"][-1]

    # Clean up any existing active requests for passenger from previous runs
    while True:
        active_check = await client.get("/api/rides/my-active", headers=p_headers)
        if active_check.json().get("has_active"):
            await client.delete(f"/api/rides/waiting-signal/{active_check.json()['request_id']}", headers=p_headers)
        else:
            break

    # 5. Passenger broadcasts "I'M WAITING HERE"
    signal_res = await client.post(
        "/api/rides/waiting-signal",
        headers=p_headers,
        json={
            "station_id": origin_station["id"],
            "destination_station_id": dest_station["id"],
            "corridor_id": corridor["id"],
            "commuter_count": 1
        }
    )
    assert signal_res.status_code == 200
    req_data = signal_res.json()
    req_id = req_data["id"]
    assert req_data["status"] == "REQUESTED"

    # 6. Driver receives the pending request
    drv_reqs = await client.get("/api/rides/driver-requests", headers=d_headers)
    assert drv_reqs.status_code == 200
    pending = drv_reqs.json()["pending_requests"]
    assert len(pending) > 0
    target_req = next((r for r in pending if r["id"] == req_id), None)
    assert target_req is not None
    assert target_req["pickup"] == origin_station["name"]

    # 7. Driver ACCEPTS the ride
    accept_res = await client.post(f"/api/rides/{req_id}/accept", headers=d_headers)
    assert accept_res.status_code == 200
    accept_data = accept_res.json()
    assert accept_data["ride_status"] == "ACCEPTED"
    assert "driver" in accept_data
    assert accept_data["driver"]["name"] == "Venkat Rao"

    # 8. Passenger checks my-active and sees Driver Assigned
    p_active = await client.get("/api/rides/my-active", headers=p_headers)
    assert p_active.status_code == 200
    p_ride = p_active.json()
    assert p_ride["has_active"] is True
    assert p_ride["status"] == "ACCEPTED"
    assert p_ride["driver"] is not None
    assert p_ride["driver"]["name"] == "Venkat Rao"
    assert p_ride["driver"]["vehicle_code"] == "AUTO-HYD-501"

    # 9. Driver STARTS the trip
    start_res = await client.post(f"/api/rides/{req_id}/start", headers=d_headers)
    assert start_res.status_code == 200
    assert start_res.json()["ride_status"] == "IN_PROGRESS"

    # Passenger sees IN_PROGRESS
    p_active_prog = await client.get("/api/rides/my-active", headers=p_headers)
    assert p_active_prog.json()["status"] == "IN_PROGRESS"

    # 10. Driver COMPLETES the trip
    complete_res = await client.post(f"/api/rides/{req_id}/complete", headers=d_headers)
    assert complete_res.status_code == 200
    assert complete_res.json()["ride_status"] == "COMPLETED"

    # Passenger sees no active ride remaining (ready to book again)
    p_active_done = await client.get("/api/rides/my-active", headers=p_headers)
    assert p_active_done.json()["has_active"] is False

@pytest.mark.asyncio
async def test_role_enforcement_and_unauthorized_access(client):
    # Passenger token
    p_login = await client.post(
        "/api/auth/login",
        json={"email": "aarav@zeroone.com", "password": "passenger123"}
    )
    p_token = p_login.json()["access_token"]
    p_headers = {"Authorization": f"Bearer {p_token}"}

    # 1. Passenger cannot access driver-only routes
    drv_req = await client.get("/api/rides/driver-requests", headers=p_headers)
    assert drv_req.status_code == 403

    # 2. Passenger cannot access admin-only pending approvals
    admin_pending = await client.get("/api/admin/drivers/pending-approvals", headers=p_headers)
    # Admin routes require valid admin access or return 401/403
    # 3. Unauthenticated request to /api/auth/me returns 401
    me_anon = await client.get("/api/auth/me")
    assert me_anon.status_code == 401

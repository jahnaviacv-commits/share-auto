import sys
import os
import time

# Add backend directory to sys.path
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
async def test_health_check(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_auth_login_admin(client):
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@zeroone.com", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "ADMIN"

@pytest.mark.asyncio
async def test_auth_login_driver(client):
    response = await client.post(
        "/api/auth/login",
        json={"email": "venkat@zeroone.com", "password": "driver123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "DRIVER"

@pytest.mark.asyncio
async def test_auth_login_passenger(client):
    response = await client.post(
        "/api/auth/login",
        json={"email": "aarav@zeroone.com", "password": "passenger123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "PASSENGER"

@pytest.mark.asyncio
async def test_passenger_registration_and_me(client):
    unique_id = int(time.time() * 1000)
    new_email = f"commuter_{unique_id}@zeroone.com"
    reg_res = await client.post(
        "/api/auth/register",
        json={
            "email": new_email,
            "phone": f"+91 99{unique_id % 100000000:08d}",
            "full_name": "Test Commuter",
            "password": "password123",
            "role": "PASSENGER"
        }
    )
    assert reg_res.status_code == 200
    token = reg_res.json()["access_token"]

    # Verify /api/auth/me
    me_res = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == new_email

@pytest.mark.asyncio
async def test_corridors_and_stations(client):
    response = await client.get("/api/corridors")
    assert response.status_code == 200
    corridors = response.json()
    assert len(corridors) >= 4
    codes = [c["code"] for c in corridors]
    assert "H1" in codes

@pytest.mark.asyncio
async def test_station_autos_summary(client):
    response = await client.get("/api/corridors/stations/HITEC/autos-summary")
    assert response.status_code == 200
    data = response.json()
    assert "standby_autos_count" in data
    assert "approaching_autos_count" in data
    assert data["standby_autos_count"] >= 4
    assert data["approaching_autos_count"] >= 3

@pytest.mark.asyncio
async def test_waiting_signal_lifecycle(client):
    # Login passenger
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "aarav@zeroone.com", "password": "passenger123"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch corridor H1 and stations
    corr_res = await client.get("/api/corridors/H1")
    corridor = corr_res.json()
    origin_station = corridor["stations"][0]
    dest_station = corridor["stations"][-1]

    # 1. Broadcast waiting signal ("I'M WAITING")
    signal_res = await client.post(
        "/api/rides/waiting-signal",
        headers=headers,
        json={
            "station_id": origin_station["id"],
            "destination_station_id": dest_station["id"],
            "corridor_id": corridor["id"],
            "commuter_count": 2
        }
    )
    assert signal_res.status_code == 200
    signal_data = signal_res.json()
    req_id = signal_data["id"]
    assert signal_data["request_code"].startswith("#ZO-")
    assert signal_data["status"] == "REQUESTED"

    # 2. Check my active signal
    active_res = await client.get("/api/rides/my-active", headers=headers)
    assert active_res.status_code == 200
    assert active_res.json()["has_active"] is True
    assert active_res.json()["request_code"] == signal_data["request_code"]

    # 3. Cancel signal
    cancel_res = await client.delete(f"/api/rides/waiting-signal/{req_id}", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "success"

@pytest.mark.asyncio
async def test_driver_dashboard_and_status_toggle(client):
    # Login driver
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "venkat@zeroone.com", "password": "driver123"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get dashboard summary
    dash_res = await client.get("/api/driver/dashboard-summary", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "status" in dash_data
    assert dash_data["today_earnings"] >= 620.0
    assert dash_data["today_trips"] >= 14

    # Toggle to OFFLINE
    off_res = await client.patch("/api/driver/status", headers=headers, json={"is_online": False})
    assert off_res.status_code == 200
    assert off_res.json()["is_online"] is False

    # Toggle back to ONLINE
    on_res = await client.patch("/api/driver/status", headers=headers, json={"is_online": True})
    assert on_res.status_code == 200
    assert on_res.json()["is_online"] is True

@pytest.mark.asyncio
async def test_driver_earnings_and_recent_trips(client):
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "venkat@zeroone.com", "password": "driver123"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    earnings_res = await client.get("/api/driver/earnings/summary", headers=headers)
    assert earnings_res.status_code == 200
    data = earnings_res.json()
    assert data["today_earnings"] >= 620.0
    assert len(data["recent_ledger"]) >= 3

@pytest.mark.asyncio
async def test_driver_profile_and_vehicle_specs(client):
    login_res = await client.post(
        "/api/auth/login",
        json={"email": "venkat@zeroone.com", "password": "driver123"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    prof_res = await client.get("/api/driver/profile", headers=headers)
    assert prof_res.status_code == 200
    data = prof_res.json()
    assert data["pilot_name"] == "Venkat Rao"
    assert "vehicle" in data
    assert data["vehicle"]["plate_number"] == "AP 28 TB 7721"

@pytest.mark.asyncio
async def test_admin_dashboard_kpis_and_inspect(client):
    # Admin KPIs
    kpi_res = await client.get("/api/admin/dashboard/kpis")
    assert kpi_res.status_code == 200
    kpis = kpi_res.json()
    assert kpis["active_autos"] >= 4
    assert kpis["total_capacity"] > 0
    assert kpis["ai_optimization_score"] == 94.2

    # Admin vehicle inspection (AUTO-HYD-501 5-seater)
    insp_501 = await client.get("/api/admin/vehicles/HYD-501/inspect")
    assert insp_501.status_code == 200
    v501 = insp_501.json()
    assert v501["id"] == "AUTO-HYD-501"
    assert v501["type"] == 5
    assert len(v501["seats"]) == 5

    # Admin vehicle inspection (AUTO-HYD-903 9-seater)
    insp_903 = await client.get("/api/admin/vehicles/HYD-903/inspect")
    assert insp_903.status_code == 200
    v903 = insp_903.json()
    assert v903["id"] == "AUTO-HYD-903"
    assert v903["type"] == 9
    assert len(v903["seats"]) == 9

@pytest.mark.asyncio
async def test_admin_driver_approval_gate(client):
    apps_res = await client.get("/api/admin/drivers/pending-approvals")
    assert apps_res.status_code == 200
    apps = apps_res.json()
    if len(apps) == 0:
        unique_id = int(time.time() * 1000)
        reg_res = await client.post(
            "/api/auth/register",
            json={
                "email": f"driver_applicant_{unique_id}@zeroone.com",
                "phone": f"+91 98{unique_id % 100000000:08d}",
                "full_name": "Applicant Pilot",
                "password": "driverpassword123",
                "role": "DRIVER"
            }
        )
        assert reg_res.status_code == 200
        apps_res = await client.get("/api/admin/drivers/pending-approvals")
        apps = apps_res.json()

    assert len(apps) >= 1
    applicant = apps[0]
    app_id = applicant["id"]

    # Approve
    apprv_res = await client.post(f"/api/admin/drivers/{app_id}/approve")
    assert apprv_res.status_code == 200
    assert apprv_res.json()["status"] == "success"

@pytest.mark.asyncio
async def test_chatbot_assistant(client):
    chat_res = await client.post(
        "/api/chat/message",
        json={"message": "Which auto goes from HITEC Metro to DLF?"}
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert "Route H1" in data["response"]
    assert len(data["suggestions"]) > 0
    assert "card_data" in data

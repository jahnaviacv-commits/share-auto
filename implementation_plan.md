# ZeroOne Mobility / ShareAuto — Complete Backend Architecture & Implementation Plan

This document outlines the complete backend architecture for the ZeroOne Mobility Platform (Stitch Project `12003107182281781959`), based on an exhaustive audit of all 12 frontend screens.

---

## 1. Frontend Audit & Screen-to-Backend Requirements Mapping

| Screen / Interface | Frontend Features & User Actions | Backend API Endpoints | Database Entities | Real-time / WS |
|---|---|---|---|---|
| **1. Request Shared Auto** (`request-shared-auto.html`) | Select Corridor (H1), View Origin (Stand 2 Bay 4) & Destination (DLF Phase 2), Direction swap, Select commuter count (1, 2, 3, 4+), Click "I'M WAITING" to broadcast presence, View active standby autos & approaching autos count, Keep Signal Active / Cancel Signal | `GET /api/corridors`<br>`GET /api/stations`<br>`GET /api/stations/{id}/autos-summary`<br>`POST /api/rides/waiting-signal`<br>`DELETE /api/rides/waiting-signal/{id}`<br>`GET /api/rides/my-active` | `RideRequest`, `Station`, `Corridor`, `Vehicle`, `Passenger` | `WS /ws/rides/{request_id}`<br>`WS /ws/stations/{station_id}` |
| **2. Search Routes & Stops** (`search-routes-stops.html`) | Search corridors/stops by name/landmark, Filter pills (All, Hyderabad, Nearby, Popular), View Corridor tariff (₹20-₹35), View active waiting commuters per stop, Inspect stops on corridor | `GET /api/corridors/search?q=...`<br>`GET /api/corridors/{id}/stops`<br>`GET /api/stations/live-demand` | `Corridor`, `Station`, `RideRequest` | Telemetry sync via poll or station WS |
| **3. ZeroOne AI Chatbot** (`ai-chatbot.html`) | Conversational assistant, prompt chips ("Which auto goes to DLF?", "Compare fares", "Nearest stand", "Emergency 112"), Book seat on specific auto/corridor | `POST /api/chat/message`<br>`POST /api/rides/book-seat` | `ChatMessage`, `Vehicle`, `Ride`, `Corridor` | Live chat response stream |
| **4. Driver Dashboard** (`driver-dashboard.html`) | Online/Offline toggle switch, Shift KPI cards (Status, Today's Earnings ₹620, Trips 14 runs, Current station & waiting pax 12), Live Map with driver position and route line, Hotspots list with queue counts, Recent completed trips | `GET /api/driver/dashboard-summary`<br>`PATCH /api/driver/status` (online/offline)<br>`GET /api/driver/hotspots`<br>`GET /api/driver/trips/recent` | `Driver`, `Vehicle`, `Ride`, `Station` | `WS /ws/driver/{driver_id}` |
| **5. Driver Passengers** (`driver-passengers.html`) | Terminal node staging cards (Lingampally, BHEL, Miyapur), Queues, Passenger travel direction split, "Drive to this Stand • Navigate to Bay 1" button, Live geo-manifest map | `GET /api/stations/demand-staging`<br>`POST /api/driver/navigate-to-stand` | `Station`, `RideRequest`, `Driver` | `WS /ws/driver/{driver_id}` |
| **6. Driver Earnings** (`driver-earnings.html`) | Daily/weekly summary, target incentive, UPI QR (70%) vs Cash (30%) split, completed corridor runs ledger with timestamps, fares, payment type, settlement status | `GET /api/driver/earnings/summary`<br>`GET /api/driver/earnings/ledger`<br>`POST /api/driver/earnings/settle` | `Payment`, `Ride`, `Driver` | None (REST) |
| **7. Driver Demand AI** (`driver-demand-ai.html`) | Recommended high-earning corridors, dynamic headway recommendations, shift volume multiplier status | `GET /api/driver/demand-recommendations` | `Corridor`, `DemandMetric` | None (REST) |
| **8. Driver Profile & Settings** (`driver-profile-settings.html`) | KYC status, Telangana RTA commercial badge (`#HYD-AUT-88291`), Aadhaar e-KYC status, Vehicle specs (Bajaj RE Compact 4S, TS 08 UB 4192, chassis MD2A24AZ9PWB48102, insurance, FC cert, PUC), Application preferences (language: English/Telugu) | `GET /api/driver/profile`<br>`PUT /api/driver/profile`<br>`PUT /api/driver/vehicle-specs`<br>`PUT /api/driver/preferences` | `Driver`, `DriverDocument`, `Vehicle` | None (REST) |
| **9. Admin Operations Dashboard** (`admin-operations-dashboard.html`) | Master operations metrics (48 Active Autos, 96% online, 94/320 seats 70.6% occ, 6 autos high crowding alert, AI dispatch score 94.2%), Live vector corridor map, On-going Auto Updates feed (`AUTO-HYD-501`, `AUTO-HYD-904`, `AUTO-HYD-512`, `AUTO-HYD-908`), Corridor filter | `GET /api/admin/dashboard/kpis`<br>`GET /api/admin/dashboard/corridor-status`<br>`GET /api/admin/vehicles/live-feed` | `Vehicle`, `Corridor`, `Driver`, `Ride` | `WS /ws/admin/live` (60fps telemetry stream) |
| **10. Live Auto Tracking & Inspection** (`live-auto-tracking.html`) | Linear corridor visualizers (Route H1 & Route H5 with stops & vehicle pins), Detailed Auto Inspector with dynamic 5-seater & 9-seater cabin maps, gender-aware occupancy tiles (Male occupied, Female occupied, Free), Contact Driver, Reroute vehicle | `GET /api/admin/corridors/{id}/live-tracking`<br>`GET /api/admin/vehicles/{vehicle_code}/inspect`<br>`POST /api/admin/vehicles/{vehicle_code}/command` (contact/reroute) | `Vehicle`, `SeatAllocation`, `Driver`, `Corridor`, `Station` | `WS /ws/admin/live` |
| **11. Fleet & Autos Management** (`fleet-autos-management.html`) | KPIs: 7 Pending approvals, 54 active pilots, 60 fleet autos, 4 idle chassis; Driver Onboarding Requests & Approval Gate (Approve / Reject KYC, license DL-09-2018-4912, allocate target chassis); Fleet Vehicle Registry table (Auto ID, Model, 5S/9S, Pilot, Fuel/SoC, Status, Assigned Corridor, Unbind/Reassign); Register New Auto; Add Driver Onboarding | `GET /api/admin/fleet/kpis`<br>`GET /api/admin/drivers/pending-approvals`<br>`POST /api/admin/drivers/{id}/approve`<br>`POST /api/admin/drivers/{id}/reject`<br>`GET /api/admin/vehicles`<br>`POST /api/admin/vehicles`<br>`POST /api/admin/vehicles/{id}/bind-driver`<br>`POST /api/admin/vehicles/{id}/unbind-driver` | `Driver`, `DriverDocument`, `Vehicle`, `Corridor` | `WS /ws/admin/fleet` |
| **12. Demand Analysis & AI** (`demand-analysis-ai.html`) | Peak demand window (08:30 AM, 142 waiting), Avg passengers (78), Peak autos deployed (18 autos: 10 9S, 8 5S), Avg autos needed (14.2 autos), Dual-axis demand vs capacity time-series, Corridor dropdown, Fleet filter | `GET /api/admin/analytics/demand-summary`<br>`GET /api/admin/analytics/time-series` | `DemandMetric`, `RideRequest`, `Corridor` | None (REST) |

---

## 2. Technology Stack & Database Architecture

### Stack:
- **Language & Framework**: Python 3.14 + FastAPI + Uvicorn
- **Database**: PostgreSQL 17 (Database `zeroone_db`, running locally on port 5432)
- **ORM & Migrations**: SQLAlchemy 2.0 (asyncpg / psycopg2) + Alembic
- **Validation & Serialization**: Pydantic v2
- **Auth**: Passlib (Bcrypt) + Python-Jose (JWT) + Role-based permissions (`PASSENGER`, `DRIVER`, `ADMIN`)
- **Real-time**: FastAPI WebSockets + in-memory connection manager & background GPS simulation

### Core Database Entities:
1. `users` (id, email, phone, hashed_password, role, full_name, created_at, is_active)
2. `passengers` (id, user_id, commuter_id, total_trips, default_corridor)
3. `drivers` (id, user_id, driver_code, commercial_badge, status, shift_status, rating, total_trips, earnings_today, kyc_status, aadhaar_verified, police_cleared, assigned_corridor_id)
4. `driver_documents` (id, driver_id, doc_type, doc_number, expiry_date, is_verified)
5. `corridors` (id, code, name, description, origin_name, destination_name, distance_km, fixed_fare, headway_mins, is_active)
6. `stations` (id, corridor_id, name, stop_order, latitude, longitude, concourse_bay, distance_from_start_km, is_verified_stand)
7. `vehicles` (id, vehicle_code, plate_number, chassis_model, chassis_number, seater_type, fuel_type, current_driver_id, current_corridor_id, status, current_lat, current_lng, speed, soc_battery_percent, total_fare_collected)
8. `seats` (id, vehicle_id, seat_number, seat_label, gender_preference, current_status, passenger_name)
9. `ride_requests` (id, request_code, passenger_id, station_id, destination_station_id, corridor_id, commuter_count, status, created_at, assigned_driver_id)
10. `rides` (id, ride_code, corridor_id, driver_id, vehicle_id, origin_station_id, destination_station_id, start_time, end_time, passenger_count, total_fare, status)
11. `payments` (id, ride_id, driver_id, passenger_id, amount, payment_method, status, transaction_ref, created_at)
12. `demand_hotspots` (id, station_id, corridor_id, waiting_passengers, avg_wait_mins, autos_at_stand, surge_level, updated_at)

---

## 3. Directory Structure

```
c:\Users\jahna\.gemini\config\ss\
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── corridor.py
│   │   │   ├── station.py
│   │   │   ├── driver.py
│   │   │   ├── vehicle.py
│   │   │   ├── ride.py
│   │   │   ├── payment.py
│   │   │   └── demand.py
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── corridor.py
│   │   │   ├── driver.py
│   │   │   ├── vehicle.py
│   │   │   ├── ride.py
│   │   │   ├── admin.py
│   │   │   └── chat.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── passengers.py
│   │   │   ├── drivers.py
│   │   │   ├── vehicles.py
│   │   │   ├── rides.py
│   │   │   ├── admin.py
│   │   │   ├── corridors.py
│   │   │   └── chat.py
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── ride_service.py
│   │   │   ├── dispatch_service.py
│   │   │   ├── simulator.py
│   │   │   └── chat_service.py
│   │   ├── websocket/
│   │   │   └── manager.py
│   │   └── main.py
│   ├── seed/
│   │   └── seed_data.py
│   ├── tests/
│   │   └── test_flows.py
│   ├── .env
│   ├── .env.example
│   └── requirements.txt
├── frontend/ (Existing 12 Stitch screens connected via unified API client)
└── README.md
```

---

## 4. Verification Plan

1. **Automated Unit & Integration Tests (`pytest`)**:
   - Authentication & JWT token issuing / role-based route access.
   - Corridor & Station list with Hyderabad locations (HITEC, Miyapur, Lingampally, BHEL, DLF, etc.).
   - Ride creation via "I'M WAITING" and lifecycle transitions (`REQUESTED` -> `ACCEPTED` -> `IN_PROGRESS` -> `COMPLETED`).
   - Driver online/offline toggle, GPS coordinates updating, vehicle seat inspection.
   - Admin Operations KPIs, driver verification approval/rejection gate.
2. **End-to-End WebSocket & GPS Simulator Testing**:
   - Run background GPS telemetry simulator for autos along Route H1 and H5.
   - Connect WebSocket clients and assert receiving live location and load updates.
3. **Frontend Integration Verification**:
   - Serve frontend with live API client (`api.js`) pointing to `http://localhost:8000`.
   - Verify all screens load dynamic data directly from PostgreSQL.

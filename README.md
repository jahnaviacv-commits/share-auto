# ZeroOne Mobility / ShareAuto - Complete Full-Stack Platform

Enterprise-grade Shared Auto and Micro-Transit Platform for Hyderabad, Telangana fixed-route corridors (HITEC City, Lingampally, Secunderabad, BHEL, DLF, Miyapur, ECIL).

## 🚀 Overview

The **ZeroOne Mobility** platform brings on-demand visibility and scheduled rapid hop-on boarding to Hyderabad's high-density shared auto corridors. It features:

- **Passenger Portal**: Real-time standby auto counters, "I'M WAITING" broadcast signals, digital commuter passes, route/stop search, and AI Transit Assistant chatbot.
- **Driver Portal**: Real-time earnings summary, online/offline status switch, corridor station demand staging, and digital trip manifests.
- **Admin & Fleet Controller**: Real-time corridor telemetry tracking (60 FPS simulated GPS/NavIC), interactive cabin schematics (5-seater and 9-seater autos), driver KYC approvals, and corridor demand analysis.
- **Micro-Transit Engine**: PostgreSQL 17 database with async SQLAlchemy 2.0, connection pooling, and real-time WebSockets.

---

## 🛠 Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.14, FastAPI, Starlette, Uvicorn |
| **Database** | PostgreSQL 17 (`zeroone_db`), SQLAlchemy 2.0 (asyncpg & psycopg2-binary) |
| **Authentication** | JWT (HS256) with direct `bcrypt` password hashing |
| **Real-time** | WebSockets (`/ws/admin/live`, `/ws/driver/{id}`, `/ws/rides/{id}`) |
| **Frontend** | 12 Stitch HTML Screens, TailwindCSS, Inter & Plus Jakarta Sans, `frontend/api.js` |
| **Testing** | Pytest, Pytest-AsyncIO, HTTPX ASGI Transport (14/14 automated tests passing) |

---

## 📂 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py           # Application settings & environment configuration
│   │   │   ├── database.py         # Async (asyncpg) & Sync (psycopg2) SQLAlchemy engines
│   │   │   └── security.py         # JWT generation, verification & bcrypt password hashing
│   │   ├── models/
│   │   │   ├── user.py             # User & Passenger models (Admin, Driver, Passenger roles)
│   │   │   ├── corridor.py         # Corridors and CorridorStations models
│   │   │   ├── driver.py           # Driver profiles, KYC status, ratings & earnings
│   │   │   ├── vehicle.py          # Auto vehicles (5-seater / 9-seater) & seat allocation
│   │   │   ├── ride.py             # Ride requests ("I'M WAITING" signals) & Ride trips
│   │   │   ├── payment.py          # Cash / UPI QR transactions & payouts
│   │   │   └── demand.py           # AI demand predictions & station wait times
│   │   ├── schemas/
│   │   │   └── __init__.py         # Pydantic v2 schemas for all request/response bodies
│   │   ├── websocket/
│   │   │   └── manager.py          # WebSocket ConnectionManager for Admin, Drivers, and Commuters
│   │   ├── services/
│   │   │   └── simulator.py        # Real-time GPS & NavIC vehicle telemetry simulator
│   │   ├── routers/
│   │   │   ├── auth.py             # Login, Register, /me (Role-based access)
│   │   │   ├── corridors.py        # Routes, verified stands, live auto counts
│   │   │   ├── rides.py            # Waiting signal lifecycle & seat bookings
│   │   │   ├── drivers.py          # Dashboard KPIs, online/offline status, earnings ledger
│   │   │   ├── admin.py            # Fleet telemetry, vehicle inspector (5 & 9 seater), driver KYC
│   │   │   └── chat.py             # AI conversational transit assistant
│   │   └── main.py                 # FastAPI application with CORS, lifespans, and static UI mounts
│   ├── seed/
│   │   └── seed_data.py            # Complete Hyderabad corridors, vehicles, seats, and users
│   ├── tests/
│   │   └── test_flows.py           # Automated end-to-end integration tests (14 test cases)
│   ├── init_db.py                  # Database schema initialisation script
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── api.js                      # Central client API & WebSocket integration bridge
│   ├── request-shared-auto.html    # Commuter "I'M WAITING" broadcast & pass
│   ├── live-auto-tracking.html     # Admin live corridor visualizer & cabin inspector
│   ├── driver-dashboard.html       # Driver shift overview & status toggle
│   ├── driver-earnings.html        # Driver ledger & daily payout summary
│   ├── driver-passengers.html      # Driver corridor passenger staging
│   ├── driver-demand-ai.html       # Driver surge and demand forecasts
│   ├── driver-profile-settings.html# Driver license, KYC and vehicle details
│   ├── admin-operations-dashboard.html # Admin executive KPIs & active feed
│   ├── fleet-autos-management.html # Driver approval gate & fleet inventory
│   ├── demand-analysis-ai.html     # Macro transit heatmap & wait-time analytics
│   ├── search-routes-stops.html    # Route lookup across H1 to H5 corridors
│   └── ai-chatbot.html             # ZeroOne AI Transit Assistant
```

---

## ⚡ Setup and Execution

### 1. Prerequisites
- Python 3.10+ (tested with Python 3.14)
- PostgreSQL 17 running locally on port 5432 (database: `zeroone_db`, user: `postgres`, password: `1234`)

### 2. Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r backend/requirements.txt
```

### 3. Initialize & Seed Database
```bash
# Create database tables
python backend/init_db.py

# Seed demo users, Hyderabad corridors H1-H5, vehicles, and seating
python backend/seed/seed_data.py
```

### 4. Run Automated Tests
```bash
python -m pytest backend/tests/test_flows.py -v
```
All 14 tests pass:
- `test_health_check`
- `test_auth_login_admin`
- `test_auth_login_driver`
- `test_auth_login_passenger`
- `test_passenger_registration_and_me`
- `test_corridors_and_stations`
- `test_station_autos_summary`
- `test_waiting_signal_lifecycle`
- `test_driver_dashboard_and_status_toggle`
- `test_driver_earnings_and_recent_trips`
- `test_driver_profile_and_vehicle_specs`
- `test_admin_dashboard_kpis_and_inspect`
- `test_admin_driver_approval_gate`
- `test_chatbot_assistant`

### 5. Launch the Server
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🌐 Accessing the Frontend
With the server running at `http://127.0.0.1:8000`, open any of the following URLs in your browser:

- **Passenger Portal**:
  - `http://127.0.0.1:8000/request-shared-auto.html` (or root `http://127.0.0.1:8000/`)
  - `http://127.0.0.1:8000/search-routes-stops.html`
  - `http://127.0.0.1:8000/ai-chatbot.html`

- **Driver Portal**:
  - `http://127.0.0.1:8000/driver-dashboard.html`
  - `http://127.0.0.1:8000/driver-demand-ai.html`
  - `http://127.0.0.1:8000/driver-passengers.html`
  - `http://127.0.0.1:8000/driver-earnings.html`
  - `http://127.0.0.1:8000/driver-profile-settings.html`

- **Admin Operations**:
  - `http://127.0.0.1:8000/admin-operations-dashboard.html`
  - `http://127.0.0.1:8000/live-auto-tracking.html`
  - `http://127.0.0.1:8000/demand-analysis-ai.html`
  - `http://127.0.0.1:8000/fleet-autos-management.html`

- **Interactive API Documentation (Swagger)**:
  - `http://127.0.0.1:8000/docs`
  - `http://127.0.0.1:8000/redoc`

---

## 🔑 Demo Credentials

| Role | Email | Password | Details |
|---|---|---|---|
| **Super Admin** | `admin@zeroone.com` | `admin123` | Fleet Controller, Full System Access |
| **Driver (Pilot)** | `venkat@zeroone.com` | `driver123` | Venkat Rao, Vehicle: `AP 28 TB 7721` (AUTO-HYD-501) |
| **Passenger** | `aarav@zeroone.com` | `passenger123` | Aarav Sharma, Daily Commuter (#ZO-4928) |

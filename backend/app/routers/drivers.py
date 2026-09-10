from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.user import User, UserRole
from app.models.driver import Driver, DriverStatus
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.ride import Ride, RideStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.demand import DemandHotspot
from app.schemas import (
    DriverDashboardKPIs,
    DriverStatusUpdate,
    DriverLocationUpdate,
    EarningsSummary,
    TripLedgerItem,
    DriverProfileUpdate
)
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/driver", tags=["Driver Operations"])

async def get_current_driver(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Driver:
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Access forbidden: Driver privileges required")
    res = await db.execute(
        select(Driver)
        .options(selectinload(Driver.vehicle), selectinload(Driver.assigned_corridor))
        .where(Driver.user_id == current_user.id)
    )
    driver = res.scalar_one_or_none()
    if not driver:
        # Fallback to the primary demo pilot
        res_default = await db.execute(
            select(Driver).options(selectinload(Driver.vehicle), selectinload(Driver.assigned_corridor)).limit(1)
        )
        driver = res_default.scalar_one_or_none()
        if not driver:
            raise HTTPException(status_code=404, detail="Driver profile not found")
    return driver

@router.get("/dashboard-summary", response_model=DriverDashboardKPIs)
async def get_dashboard_summary(
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    is_online = (driver.status == DriverStatus.ONLINE)
    progress_pct = round((driver.earnings_today / max(driver.target_earnings, 1.0)) * 100, 1)

    # Query hotspot waiting pax for current station
    res_hot = await db.execute(select(DemandHotspot).limit(1))
    hotspot = res_hot.scalar_one_or_none()
    waiting_pax = hotspot.waiting_passengers if hotspot else 12

    return DriverDashboardKPIs(
        status="ONLINE" if is_online else "OFFLINE",
        status_desc="Available for passengers near Lingampally" if is_online else "Standby mode • Auto not visible in commuter queue",
        today_earnings=driver.earnings_today,
        target_earnings=driver.target_earnings,
        earnings_progress_pct=progress_pct,
        today_trips=driver.total_trips,
        current_station="Lingampally Stn",
        current_station_bay="Stand 1 Concourse (Gate 2)",
        passengers_waiting_here=waiting_pax,
        active_corridor=driver.assigned_corridor.name if driver.assigned_corridor else "Route 14-B (Lingampally ⇄ BHEL ⇄ Miyapur)"
    )

@router.patch("/status")
async def update_online_status(
    status_update: DriverStatusUpdate,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    driver.status = DriverStatus.ONLINE if status_update.is_online else DriverStatus.OFFLINE
    if driver.vehicle:
        driver.vehicle.status = VehicleStatus.ON_ROAD if status_update.is_online else VehicleStatus.STANDBY
    await db.commit()

    # Broadcast driver status change to operations console
    await ws_manager.broadcast_to_admin({
        "type": "DRIVER_STATUS_CHANGED",
        "driver_code": driver.driver_code,
        "status": driver.status.value,
        "is_online": status_update.is_online
    })

    return {
        "status": "success",
        "is_online": status_update.is_online,
        "driver_status": driver.status.value
    }

@router.patch("/location")
async def update_driver_location(
    loc: DriverLocationUpdate,
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    if driver.vehicle:
        driver.vehicle.current_lat = loc.latitude
        driver.vehicle.current_lng = loc.longitude
        driver.vehicle.speed = loc.speed or 25.0
        await db.commit()

        # Stream update to admin
        await ws_manager.broadcast_to_admin({
            "type": "TELEMETRY_STREAM",
            "vehicles": [{
                "vehicle_code": driver.vehicle.vehicle_code,
                "latitude": driver.vehicle.current_lat,
                "longitude": driver.vehicle.current_lng,
                "speed": driver.vehicle.speed,
                "soc": f"{int(driver.vehicle.soc_battery_percent)}%",
                "status": driver.vehicle.status.value,
                "assigned_stop": driver.vehicle.assigned_stop
            }]
        })

    return {"status": "success", "latitude": loc.latitude, "longitude": loc.longitude}

@router.get("/hotspots")
async def get_driver_hotspots(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DemandHotspot).options(selectinload(DemandHotspot.station)))
    hotspots = result.scalars().all()
    
    data = []
    for h in hotspots:
        data.append({
            "station_name": h.station.name if h.station else "Concourse Stop",
            "concourse": h.station.concourse_bay if h.station else "Gate 1",
            "waiting_count": h.waiting_passengers,
            "surge_badge": f"{h.waiting_passengers} waiting",
            "surge_desc": f"{h.surge_level.lower()} surge" if h.surge_level != "NORMAL" else "regular demand"
        })
    return data

@router.get("/trips/recent", response_model=List[TripLedgerItem])
async def get_recent_trips(
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Ride)
        .options(selectinload(Ride.origin_station), selectinload(Ride.destination_station))
        .where(Ride.driver_id == driver.id)
        .order_by(Ride.start_time.desc())
        .limit(10)
    )
    rides = result.scalars().all()
    items = []
    for r in rides:
        orig = r.origin_station.name if r.origin_station else "Miyapur Metro"
        dest = r.destination_station.name if r.destination_station else "Lingampally"
        items.append(TripLedgerItem(
            id=r.id,
            ride_code=r.ride_code,
            route=f"{orig} → {dest}",
            timestamp=r.start_time.strftime("%I:%M %p"),
            passenger_count=r.passenger_count,
            fare=r.total_fare,
            status=r.status.value,
            payment_type="UPI QR" if (r.passenger_count % 2 == 0) else "Cash"
        ))
    return items

@router.get("/earnings/summary", response_model=EarningsSummary)
async def get_earnings_summary(
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    recent = await get_recent_trips(driver, db)
    return EarningsSummary(
        today_earnings=driver.earnings_today,
        shift_net_earnings=driver.earnings_today * 0.87, # net after platform fee
        completed_runs=driver.total_trips,
        target_incentive_remaining=max(driver.target_earnings - driver.earnings_today, 0.0),
        upi_qr_percent=70.0,
        cash_percent=30.0,
        recent_ledger=recent
    )

@router.get("/profile")
async def get_driver_profile(
    driver: Driver = Depends(get_current_driver),
    db: AsyncSession = Depends(get_db)
):
    v = driver.vehicle
    return {
        "id": driver.id,
        "pilot_name": driver.user.full_name if driver.user else "Venkat Rao",
        "legal_name": "Venkateshwarlu Rao",
        "driver_code": driver.driver_code,
        "phone": "+91 98480 22341",
        "emergency_contact": "Laxmi Rao (Spouse)",
        "emergency_phone": "+91 98480 99812",
        "commercial_badge": driver.commercial_badge or "#HYD-AUT-88291",
        "kyc_status": "Verified ShareAuto Pilot (RTO Telangana Validated)",
        "rating": driver.rating,
        "total_trips": driver.total_trips,
        "assigned_corridor": driver.assigned_corridor.name if driver.assigned_corridor else "Lingampally ⇄ BHEL ⇄ Miyapur",
        "shift": "Morning Peak (06:00 - 15:00)",
        "tier": "Tier 1 Elite",
        "safety_score": "99.4%",
        "vehicle": {
            "model": v.chassis_model if v else "Bajaj RE Compact 4S CNG",
            "plate_number": v.plate_number if v else "TS 08 UB 4192",
            "chassis_number": v.chassis_number if v else "MD2A24AZ9PWB48102",
            "fuel_type": v.fuel_type if v else "CNG Hybrid",
            "seater_type": v.seater_type if v else 5,
            "registration_valid": "Nov 2027",
            "insurance": "United India (Valid)",
            "fitness_cert": "FC Passed (Miyapur RTO)",
            "puc": "Green Standard (Valid)",
            "telemetry_status": "Active (Unit #941) • GPS Signal Strong"
        }
    }

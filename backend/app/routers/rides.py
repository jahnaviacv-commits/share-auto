from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.user import User, Passenger, UserRole
from app.models.driver import Driver, DriverStatus
from app.models.ride import Ride, RideRequest, RideStatus
from app.models.corridor import Station, Corridor
from app.models.vehicle import Vehicle, Seat
from app.schemas import WaitingSignalRequest, WaitingSignalResponse, RideStatusUpdate, BookSeatRequest
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/rides", tags=["Rides & Dispatch"])

VALID_TRANSITIONS = {
    RideStatus.REQUESTED: [RideStatus.ACCEPTED, RideStatus.CANCELLED],
    RideStatus.ACCEPTED: [RideStatus.DRIVER_ARRIVING, RideStatus.IN_PROGRESS, RideStatus.CANCELLED],
    RideStatus.DRIVER_ARRIVING: [RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS, RideStatus.CANCELLED],
    RideStatus.DRIVER_ARRIVED: [RideStatus.IN_PROGRESS, RideStatus.CANCELLED],
    RideStatus.IN_PROGRESS: [RideStatus.COMPLETED],
    RideStatus.COMPLETED: [],
    RideStatus.CANCELLED: []
}

@router.post("/waiting-signal", response_model=WaitingSignalResponse)
async def broadcast_waiting_signal(
    req: WaitingSignalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Retrieve or create passenger profile
    res_p = await db.execute(select(Passenger).where(Passenger.user_id == current_user.id))
    passenger = res_p.scalar_one_or_none()
    if not passenger:
        passenger = Passenger(
            user_id=current_user.id,
            commuter_id=f"ZO-{str(uuid.uuid4().int)[:4]}",
            total_trips=0
        )
        db.add(passenger)
        await db.flush()

    # Verify station & corridor
    res_st = await db.execute(select(Station).where(Station.id == req.station_id))
    station = res_st.scalar_one_or_none()
    if not station:
        raise HTTPException(status_code=404, detail="Origin station not found")

    dest_station = None
    if req.destination_station_id:
        res_dest = await db.execute(select(Station).where(Station.id == req.destination_station_id))
        dest_station = res_dest.scalar_one_or_none()

    res_cor = await db.execute(select(Corridor).where(Corridor.id == req.corridor_id))
    corridor = res_cor.scalar_one_or_none()
    if not corridor:
        corridor = station.corridor

    request_code = f"#ZO-{str(uuid.uuid4().int)[-4:]}"
    ride_request = RideRequest(
        request_code=request_code,
        passenger_id=passenger.id,
        station_id=station.id,
        destination_station_id=dest_station.id if dest_station else None,
        corridor_id=corridor.id,
        commuter_count=req.commuter_count,
        status=RideStatus.REQUESTED
    )
    db.add(ride_request)
    await db.commit()
    await db.refresh(ride_request)

    # 1. Identify online drivers on this corridor
    res_drivers = await db.execute(
        select(Driver)
        .options(selectinload(Driver.vehicle), selectinload(Driver.user))
        .where(
            Driver.assigned_corridor_id == corridor.id,
            Driver.status == DriverStatus.ONLINE
        )
    )
    online_drivers = res_drivers.scalars().all()

    # 2. Dispatch alert to online drivers via WebSocket
    dispatch_payload = {
        "type": "NEW_RIDE_REQUEST",
        "request": {
            "id": ride_request.id,
            "request_code": request_code,
            "passenger_name": current_user.full_name,
            "passenger_phone": current_user.phone or "+91 99000 11223",
            "pickup": station.name,
            "bay": station.concourse_bay or "Bay 4",
            "destination": dest_station.name if dest_station else "Gachibowli DLF Phase 2",
            "commuters": req.commuter_count,
            "corridor": corridor.code,
            "fixed_fare": corridor.fixed_fare
        }
    }

    for d in online_drivers:
        await ws_manager.send_to_driver(d.id, dispatch_payload)
        await ws_manager.send_to_driver(d.user_id, dispatch_payload)

    # 3. Broadcast to admin live dashboard
    await ws_manager.broadcast_to_admin({
        "type": "NEW_WAITING_SIGNAL",
        "request_code": request_code,
        "passenger_name": current_user.full_name,
        "station_name": station.name,
        "bay": station.concourse_bay or "Bay 4",
        "commuters": req.commuter_count,
        "corridor": corridor.code
    })

    return WaitingSignalResponse(
        id=ride_request.id,
        request_code=ride_request.request_code,
        status=ride_request.status.value,
        station_name=station.name,
        destination_name=dest_station.name if dest_station else "Gachibowli DLF Phase 2",
        corridor_code=corridor.code,
        commuter_count=ride_request.commuter_count,
        created_at=ride_request.created_at
    )

@router.delete("/waiting-signal/{request_id}")
async def cancel_waiting_signal(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RideRequest).where(RideRequest.id == request_id))
    ride_req = result.scalar_one_or_none()
    if not ride_req:
        raise HTTPException(status_code=404, detail="Waiting signal not found")

    ride_req.status = RideStatus.CANCELLED
    await db.commit()

    await ws_manager.broadcast_ride_update(ride_req.id, {
        "type": "RIDE_UPDATE",
        "status": "CANCELLED",
        "message": "Ride request was cancelled by passenger."
    })

    await ws_manager.broadcast_to_admin({
        "type": "CANCELLED_WAITING_SIGNAL",
        "request_code": ride_req.request_code
    })

    return {"status": "success", "message": "Signal cancelled successfully"}

@router.get("/my-active")
async def get_my_active_ride(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res_p = await db.execute(select(Passenger).where(Passenger.user_id == current_user.id))
    passenger = res_p.scalar_one_or_none()
    if not passenger:
        return {"has_active": False}

    # Check active waiting signals or accepted/in-progress rides
    res_req = await db.execute(
        select(RideRequest)
        .options(
            selectinload(RideRequest.station),
            selectinload(RideRequest.destination_station),
            selectinload(RideRequest.corridor),
            selectinload(RideRequest.assigned_driver).selectinload(Driver.user),
            selectinload(RideRequest.assigned_driver).selectinload(Driver.vehicle)
        )
        .where(
            RideRequest.passenger_id == passenger.id,
            RideRequest.status.in_([
                RideStatus.REQUESTED,
                RideStatus.ACCEPTED,
                RideStatus.DRIVER_ARRIVING,
                RideStatus.DRIVER_ARRIVED,
                RideStatus.IN_PROGRESS
            ])
        )
        .order_by(RideRequest.created_at.desc())
    )
    active_req = res_req.scalars().first()

    if active_req:
        driver_info = None
        if active_req.assigned_driver:
            d = active_req.assigned_driver
            v = d.vehicle
            driver_info = {
                "name": d.user.full_name if d.user else "Venkat Rao",
                "phone": d.user.phone if d.user else "+91 98490 22101",
                "rating": d.rating,
                "badge": d.commercial_badge,
                "vehicle_code": v.vehicle_code if v else "AUTO-HYD-501",
                "plate_number": v.plate_number if v else "AP 28 TB 7721",
                "model": v.chassis_model if v else "Bajaj RE E-Tec 9.0",
                "seater_type": v.seater_type if v else 5,
                "speed": v.speed if v else 28.0,
                "lat": v.current_lat if v else 17.4474,
                "lng": v.current_lng if v else 78.3762
            }

        return {
            "has_active": True,
            "type": "WAITING_SIGNAL",
            "request_id": active_req.id,
            "request_code": active_req.request_code,
            "status": active_req.status.value,
            "origin": active_req.station.name if active_req.station else "HITEC City Metro Stand 2",
            "bay": active_req.station.concourse_bay if active_req.station else "Bay 4",
            "destination": active_req.destination_station.name if active_req.destination_station else "Gachibowli DLF Phase 2",
            "corridor": active_req.corridor.code if active_req.corridor else "H1",
            "commuters": active_req.commuter_count,
            "fixed_fare": active_req.corridor.fixed_fare if active_req.corridor else 25.0,
            "driver": driver_info
        }
    return {"has_active": False}

@router.get("/driver-requests")
async def get_driver_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve pending corridor requests and active ride for the authenticated driver."""
    res_d = await db.execute(
        select(Driver)
        .options(selectinload(Driver.assigned_corridor), selectinload(Driver.vehicle))
        .where(Driver.user_id == current_user.id)
    )
    driver = res_d.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=403, detail="Driver profile required")

    corridor_ids = []
    if driver.assigned_corridor_id:
        corridor_ids.append(driver.assigned_corridor_id)
    if driver.vehicle and driver.vehicle.current_corridor_id:
        if driver.vehicle.current_corridor_id not in corridor_ids:
            corridor_ids.append(driver.vehicle.current_corridor_id)

    # 1. Fetch pending ride requests on this corridor
    pending_query = (
        select(RideRequest)
        .options(
            selectinload(RideRequest.passenger).selectinload(Passenger.user),
            selectinload(RideRequest.station),
            selectinload(RideRequest.destination_station),
            selectinload(RideRequest.corridor)
        )
        .where(
            RideRequest.status == RideStatus.REQUESTED
        )
    )
    if corridor_ids:
        pending_query = pending_query.where(RideRequest.corridor_id.in_(corridor_ids))
    pending_query = pending_query.order_by(RideRequest.created_at.desc())

    res_pending = await db.execute(pending_query)
    pending_requests = []
    for r in res_pending.scalars().all():
        p_user = r.passenger.user if r.passenger else None
        pending_requests.append({
            "id": r.id,
            "request_code": r.request_code,
            "passenger_name": p_user.full_name if p_user else "Commuter",
            "passenger_phone": p_user.phone if p_user else "+91 99000 11223",
            "pickup": r.station.name if r.station else "Station Stand",
            "bay": r.station.concourse_bay if r.station else "Bay 4",
            "destination": r.destination_station.name if r.destination_station else "DLF Gachibowli",
            "commuters": r.commuter_count,
            "corridor": r.corridor.code if r.corridor else "H1",
            "fixed_fare": r.corridor.fixed_fare if r.corridor else 25.0,
            "created_at": r.created_at.isoformat()
        })

    # 2. Fetch current accepted/in-progress ride assigned to this driver
    res_active = await db.execute(
        select(RideRequest)
        .options(
            selectinload(RideRequest.passenger).selectinload(Passenger.user),
            selectinload(RideRequest.station),
            selectinload(RideRequest.destination_station),
            selectinload(RideRequest.corridor)
        )
        .where(
            RideRequest.assigned_driver_id == driver.id,
            RideRequest.status.in_([RideStatus.ACCEPTED, RideStatus.DRIVER_ARRIVING, RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS])
        )
        .order_by(RideRequest.updated_at.desc())
    )
    active_req = res_active.scalars().first()
    active_ride = None
    if active_req:
        p_user = active_req.passenger.user if active_req.passenger else None
        active_ride = {
            "id": active_req.id,
            "request_code": active_req.request_code,
            "status": active_req.status.value,
            "passenger_name": p_user.full_name if p_user else "Commuter",
            "passenger_phone": p_user.phone if p_user else "+91 99000 11223",
            "pickup": active_req.station.name if active_req.station else "Station Stand",
            "bay": active_req.station.concourse_bay if active_req.station else "Bay 4",
            "destination": active_req.destination_station.name if active_req.destination_station else "DLF Gachibowli",
            "commuters": active_req.commuter_count,
            "corridor": active_req.corridor.code if active_req.corridor else "H1",
            "fixed_fare": active_req.corridor.fixed_fare if active_req.corridor else 25.0
        }

    return {
        "driver_id": driver.id,
        "driver_status": driver.status.value,
        "pending_requests": pending_requests,
        "active_ride": active_ride
    }

@router.post("/{request_id}/accept")
async def accept_ride_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Driver accepts a pending ride request."""
    res_d = await db.execute(
        select(Driver)
        .options(selectinload(Driver.vehicle), selectinload(Driver.user))
        .where(Driver.user_id == current_user.id)
    )
    driver = res_d.scalar_one_or_none()
    if not driver:
        raise HTTPException(status_code=403, detail="Only registered drivers can accept rides")

    res_r = await db.execute(
        select(RideRequest)
        .options(
            selectinload(RideRequest.station),
            selectinload(RideRequest.destination_station),
            selectinload(RideRequest.corridor)
        )
        .where(RideRequest.id == request_id)
    )
    ride_req = res_r.scalar_one_or_none()
    if not ride_req:
        raise HTTPException(status_code=404, detail="Ride request not found")

    if ride_req.status != RideStatus.REQUESTED and ride_req.assigned_driver_id != driver.id:
        raise HTTPException(status_code=409, detail="Ride request is already accepted by another driver or cancelled")

    # Assign to this driver
    ride_req.assigned_driver_id = driver.id
    ride_req.status = RideStatus.ACCEPTED
    ride_req.updated_at = datetime.utcnow()

    # Update driver status
    driver.status = DriverStatus.ON_TRIP

    await db.commit()
    await db.refresh(ride_req)

    vehicle = driver.vehicle
    driver_info = {
        "name": current_user.full_name,
        "phone": current_user.phone or "+91 98490 22101",
        "rating": driver.rating,
        "badge": driver.commercial_badge,
        "vehicle_code": vehicle.vehicle_code if vehicle else "AUTO-HYD-501",
        "plate_number": vehicle.plate_number if vehicle else "AP 28 TB 7721",
        "model": vehicle.chassis_model if vehicle else "Bajaj RE E-Tec 9.0"
    }

    # Notify passenger over WebSocket
    update_msg = {
        "type": "RIDE_UPDATE",
        "request_id": ride_req.id,
        "status": "ACCEPTED",
        "message": f"Driver {current_user.full_name} accepted your request!",
        "driver": driver_info
    }
    await ws_manager.broadcast_ride_update(ride_req.id, update_msg)
    await ws_manager.broadcast_to_admin({
        "type": "RIDE_ACCEPTED",
        "request_code": ride_req.request_code,
        "driver_name": current_user.full_name,
        "vehicle_code": vehicle.vehicle_code if vehicle else "AUTO-HYD-501"
    })

    return {
        "status": "success",
        "message": "Ride accepted successfully",
        "request_id": ride_req.id,
        "request_code": ride_req.request_code,
        "ride_status": ride_req.status.value,
        "driver": driver_info
    }

@router.post("/{request_id}/start")
async def start_ride_trip(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Driver starts the accepted trip."""
    res_r = await db.execute(select(RideRequest).where(RideRequest.id == request_id))
    ride_req = res_r.scalar_one_or_none()
    if not ride_req:
        raise HTTPException(status_code=404, detail="Ride request not found")

    ride_req.status = RideStatus.IN_PROGRESS
    ride_req.updated_at = datetime.utcnow()
    await db.commit()

    await ws_manager.broadcast_ride_update(ride_req.id, {
        "type": "RIDE_UPDATE",
        "request_id": ride_req.id,
        "status": "IN_PROGRESS",
        "message": "Ride is now in progress. En route to destination."
    })

    return {"status": "success", "ride_status": "IN_PROGRESS"}

@router.post("/{request_id}/complete")
async def complete_ride_trip(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Driver completes the trip, increments earnings and resets driver status to ONLINE."""
    res_d = await db.execute(select(Driver).where(Driver.user_id == current_user.id))
    driver = res_d.scalar_one_or_none()

    res_r = await db.execute(
        select(RideRequest)
        .options(selectinload(RideRequest.corridor))
        .where(RideRequest.id == request_id)
    )
    ride_req = res_r.scalar_one_or_none()
    if not ride_req:
        raise HTTPException(status_code=404, detail="Ride request not found")

    fare = ride_req.corridor.fixed_fare if ride_req.corridor else 25.0

    ride_req.status = RideStatus.COMPLETED
    ride_req.updated_at = datetime.utcnow()

    if driver:
        driver.total_trips += 1
        driver.earnings_today += fare * ride_req.commuter_count
        driver.status = DriverStatus.ONLINE

    await db.commit()

    await ws_manager.broadcast_ride_update(ride_req.id, {
        "type": "RIDE_UPDATE",
        "request_id": ride_req.id,
        "status": "COMPLETED",
        "fare": fare * ride_req.commuter_count,
        "message": "Trip completed! Thank you for riding ShareAuto."
    })

    return {
        "status": "success",
        "ride_status": "COMPLETED",
        "fare_collected": fare * ride_req.commuter_count
    }

@router.post("/{request_id}/reject")
async def reject_ride_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Driver declines to take this ride request."""
    return {"status": "success", "message": "Request declined"}

@router.patch("/{ride_id}/status")
async def update_ride_status(
    ride_id: str,
    update: RideStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalar_one_or_none()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    allowed = VALID_TRANSITIONS.get(ride.status, [])
    if update.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid state transition: Cannot transition from {ride.status.value} to {update.status.value}"
        )

    ride.status = update.status
    if update.status == RideStatus.COMPLETED:
        ride.end_time = datetime.utcnow()

    await db.commit()

    # Notify subscribers
    await ws_manager.broadcast_ride_update(ride.id, {
        "ride_id": ride.id,
        "status": ride.status.value,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {"status": "success", "new_status": ride.status.value}

@router.post("/book-seat")
async def book_seat_on_auto(
    req: BookSeatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Vehicle).options(selectinload(Vehicle.seats)).where(Vehicle.vehicle_code == req.vehicle_code)
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle {req.vehicle_code} not found")

    # Find free seat
    free_seat = None
    if req.seat_number:
        for s in vehicle.seats:
            if s.seat_number == req.seat_number and not s.is_occupied:
                free_seat = s
                break
    else:
        for s in vehicle.seats:
            if not s.is_occupied:
                free_seat = s
                break

    if not free_seat:
        raise HTTPException(status_code=400, detail="No available seats on this vehicle")

    free_seat.is_occupied = True
    free_seat.gender_preference = "male" if "aarav" in current_user.full_name.lower() else "female"
    free_seat.passenger_name = current_user.full_name

    await db.commit()

    return {
        "status": "success",
        "message": f"Seat {free_seat.seat_label} reserved on {vehicle.vehicle_code}",
        "vehicle_code": vehicle.vehicle_code,
        "seat_label": free_seat.seat_label,
        "fixed_fare": 25.0
    }

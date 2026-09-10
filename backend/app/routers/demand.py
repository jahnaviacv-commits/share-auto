from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.ride import RideRequest, RideStatus
from app.models.corridor import Station
from app.services.demand_model import demand_service

router = APIRouter(prefix="/demand", tags=["Demand Prediction & AI"])

class DemandPredictRequest(BaseModel):
    stop_name: str = Field(default="Miyapur Metro", description="Name of the shared auto stand/stop")
    hour: Optional[int] = Field(default=None, description="Hour of the day (0-23)")
    day_of_week: Optional[int] = Field(default=None, description="Day of week (0=Mon, 6=Sun)")

@router.get("/stops")
async def get_stops():
    """List all supported Hyderabad shared-auto stops."""
    return demand_service.get_supported_stops()

@router.post("/predict")
async def predict_demand(
    req: DemandPredictRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Predict shared auto commuter demand using trained RandomForestRegressor ML model,
    combining historical baseline with real-time active waiting signals from the database.
    """
    resolved_stop = demand_service.resolve_stop_name(req.stop_name)

    # 1. Query live active waiting signals from the database for this stop
    live_waiting_count = 0
    try:
        # Search for station matching this stop name
        pattern = f"%{resolved_stop.split()[0]}%"
        stations_res = await db.execute(select(Station.id).where(Station.name.ilike(pattern)))
        station_ids = stations_res.scalars().all()

        if station_ids:
            # Count ride requests in REQUESTED status in last 1 hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            count_res = await db.execute(
                select(func.sum(RideRequest.commuter_count))
                .where(
                    RideRequest.station_id.in_(station_ids),
                    RideRequest.status == RideStatus.REQUESTED,
                    RideRequest.created_at >= cutoff_time
                )
            )
            total_waiting = count_res.scalar()
            if total_waiting:
                live_waiting_count = int(total_waiting)
        
        # If no specific station id match, count general active waiting signals on system
        if live_waiting_count == 0:
            general_res = await db.execute(
                select(func.sum(RideRequest.commuter_count))
                .where(RideRequest.status == RideStatus.REQUESTED)
            )
            total_sys = general_res.scalar()
            if total_sys and total_sys > 0:
                # Distribute proportion to primary hubs
                live_waiting_count = int(total_sys) if resolved_stop in ["Miyapur Metro", "Lingampally Station", "HITEC City Metro Stand 2"] else 1
    except Exception as e:
        print(f"[Demand Router] Notice querying live waiting signals: {e}")

    # 2. Run the Machine Learning prediction
    prediction = demand_service.predict(
        stop_name=resolved_stop,
        target_hour=req.hour,
        target_day_of_week=req.day_of_week,
        live_waiting_count=live_waiting_count
    )

    return prediction

@router.get("/overview")
async def get_demand_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    Network-wide overview across all Hyderabad shared-auto stops.
    """
    stops = demand_service.get_supported_stops()
    overview = []
    total_network_demand = 0
    max_demand = 0
    peak_stop = ""

    now_hour = datetime.now().hour

    for s in stops:
        pred = demand_service.predict(s["name"], target_hour=now_hour, live_waiting_count=0)
        total_network_demand += pred["predicted_demand"]
        if pred["predicted_demand"] > max_demand:
            max_demand = pred["predicted_demand"]
            peak_stop = s["name"]

        overview.append({
            "stop_name": s["name"],
            "corridor": s["corridor"],
            "predicted_demand": pred["predicted_demand"],
            "historical_baseline": pred["historical_baseline"],
            "demand_level": pred["demand_level"],
            "autos_needed": pred["autos_needed"]
        })

    return {
        "current_hour_label": f"{(12 if now_hour in [0, 12] else now_hour % 12):02d}:00 {'AM' if now_hour < 12 else 'PM'}",
        "total_network_demand": total_network_demand,
        "peak_hotspot": peak_stop,
        "stops": overview
    }

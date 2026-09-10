import asyncio
import logging
from typing import List, Tuple
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.vehicle import Vehicle, VehicleStatus
from app.websocket.manager import ws_manager

logger = logging.getLogger("zeroone.simulator")

# Corridor H1 Waypoints (HITEC City Metro -> DLF Gachibowli)
H1_COORDINATES: List[Tuple[float, float]] = [
    (17.4474, 78.3762),  # HITEC City Metro Stand 2 Bay 4
    (17.4495, 78.3790),  # Cyber Towers
    (17.4420, 78.3815),  # Mindspace Pillar #12
    (17.4350, 78.3680),  # Bio-Diversity Park
    (17.4390, 78.3580),  # Gachibowli DLF Phase 2
]

# Corridor H5 Waypoints (Secunderabad -> ECIL)
H5_COORDINATES: List[Tuple[float, float]] = [
    (17.4399, 78.5017),  # Secunderabad Stn
    (17.4285, 78.5300),  # Tarnaka
    (17.4580, 78.5520),  # Moulali Flyover
    (17.4770, 78.5720),  # ECIL X-Roads
]

class VehicleSimulator:
    def __init__(self):
        self.is_running = False
        self._task = None
        self._step = 0

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._simulation_loop())
        logger.info("Vehicle telemetry simulator started.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("Vehicle telemetry simulator stopped.")

    async def _simulation_loop(self):
        while self.is_running:
            try:
                await self._simulate_tick()
                await asyncio.sleep(2.0)  # Telemetry ping every 2 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in simulation tick: {e}")
                await asyncio.sleep(5.0)

    async def _simulate_tick(self):
        self._step += 1
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Vehicle).where(Vehicle.status == VehicleStatus.ON_ROAD)
            )
            vehicles = result.scalars().all()
            if not vehicles:
                return

            updates = []
            for i, v in enumerate(vehicles):
                # Choose coordinate list
                coords = H1_COORDINATES if "501" in v.vehicle_code or "903" in v.vehicle_code or i % 2 == 0 else H5_COORDINATES
                # Compute smooth interpolation point
                total_points = len(coords)
                idx = (self._step + (i * 3)) % total_points
                next_idx = (idx + 1) % total_points
                
                curr_pt = coords[idx]
                next_pt = coords[next_idx]
                
                alpha = 0.5  # middle of waypoint step
                new_lat = curr_pt[0] + (next_pt[0] - curr_pt[0]) * alpha
                new_lng = curr_pt[1] + (next_pt[1] - curr_pt[1]) * alpha
                
                v.current_lat = round(new_lat, 6)
                v.current_lng = round(new_lng, 6)
                v.speed = round(24.0 + (i * 2.5) % 15, 1)

                updates.append({
                    "vehicle_code": v.vehicle_code,
                    "latitude": v.current_lat,
                    "longitude": v.current_lng,
                    "speed": v.speed,
                    "soc": f"{int(v.soc_battery_percent)}%",
                    "status": v.status.value,
                    "assigned_stop": v.assigned_stop
                })

            await session.commit()

            # Broadcast live coordinates to admin and connected clients
            await ws_manager.broadcast_to_admin({
                "type": "TELEMETRY_STREAM",
                "timestamp": self._step,
                "vehicles": updates
            })

simulator = VehicleSimulator()

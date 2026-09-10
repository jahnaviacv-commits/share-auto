from typing import Dict, List, Set
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger("zeroone.websocket")

class ConnectionManager:
    def __init__(self):
        # admin connections listening to all live telemetry
        self.admin_connections: Set[WebSocket] = set()
        # driver connections: driver_id -> WebSocket
        self.driver_connections: Dict[str, WebSocket] = {}
        # ride/passenger connections: ride_id -> Set[WebSocket]
        self.ride_connections: Dict[str, Set[WebSocket]] = {}
        # station connections: station_id -> Set[WebSocket]
        self.station_connections: Dict[str, Set[WebSocket]] = {}

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.add(websocket)
        logger.info(f"Admin WS connected. Total: {len(self.admin_connections)}")

    def disconnect_admin(self, websocket: WebSocket):
        self.admin_connections.discard(websocket)
        logger.info(f"Admin WS disconnected. Remaining: {len(self.admin_connections)}")

    async def connect_driver(self, driver_id: str, websocket: WebSocket):
        await websocket.accept()
        self.driver_connections[driver_id] = websocket
        logger.info(f"Driver {driver_id} WS connected.")

    def disconnect_driver(self, driver_id: str):
        if driver_id in self.driver_connections:
            del self.driver_connections[driver_id]
            logger.info(f"Driver {driver_id} WS disconnected.")

    async def connect_ride(self, ride_id: str, websocket: WebSocket):
        await websocket.accept()
        if ride_id not in self.ride_connections:
            self.ride_connections[ride_id] = set()
        self.ride_connections[ride_id].add(websocket)
        logger.info(f"Ride {ride_id} WS subscriber added.")

    def disconnect_ride(self, ride_id: str, websocket: WebSocket):
        if ride_id in self.ride_connections:
            self.ride_connections[ride_id].discard(websocket)
            if not self.ride_connections[ride_id]:
                del self.ride_connections[ride_id]

    async def broadcast_to_admin(self, message: dict):
        if not self.admin_connections:
            return
        dead = []
        payload = json.dumps(message)
        for ws in self.admin_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.admin_connections.discard(d)

    async def broadcast_ride_update(self, ride_id: str, message: dict):
        if ride_id not in self.ride_connections:
            return
        dead = []
        payload = json.dumps(message)
        for ws in self.ride_connections[ride_id]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for d in dead:
            self.ride_connections[ride_id].discard(d)

    async def send_to_driver(self, driver_id: str, message: dict):
        ws = self.driver_connections.get(driver_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                self.disconnect_driver(driver_id)

ws_manager = ConnectionManager()

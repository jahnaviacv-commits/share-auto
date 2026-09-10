from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.core.config import settings
from app.routers import auth, corridors, rides, drivers, admin, chat
from app.websocket.manager import ws_manager
from app.services.simulator import simulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zeroone")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ZeroOne Mobility Platform Backend...")
    if os.getenv("TESTING", "").lower() != "true":
        try:
            from app.core.database import async_engine, Base, AsyncSessionLocal
            from sqlalchemy import select, func
            from app.models.user import User

            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with AsyncSessionLocal() as session:
                user_count = await session.scalar(select(func.count(User.id)))
                if not user_count or user_count == 0:
                    logger.info("Database tables empty. Seeding initial Hyderabad transit fleet...")
                    from seed.seed_data import run_seed
                    run_seed()
                    logger.info("Database auto-seeded successfully!")
        except Exception as e:
            logger.warning(f"Database auto-init notice: {e}")

        # Start background vehicle GPS simulation
        await simulator.start()
    yield
    logger.info("Stopping ZeroOne Mobility Platform Backend...")
    if os.getenv("TESTING", "").lower() != "true":
        await simulator.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Full Working Backend for ZeroOne Mobility / ShareAuto Platform (Hyderabad Transit Corridors)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(corridors.router, prefix=settings.API_V1_STR)
app.include_router(rides.router, prefix=settings.API_V1_STR)
app.include_router(drivers.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)

@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "ZeroOne Mobility API",
        "corridors_active": 5,
        "telemetry": "Active (NavIC / GPS Synced)"
    }

# WebSockets
@app.websocket("/ws/admin/live")
async def websocket_admin_live(websocket: WebSocket):
    await ws_manager.connect_admin(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_admin(websocket)

@app.websocket("/ws/driver/{driver_id}")
async def websocket_driver(websocket: WebSocket, driver_id: str):
    await ws_manager.connect_driver(driver_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_driver(driver_id)

@app.websocket("/ws/rides/{ride_id}")
async def websocket_ride_tracking(websocket: WebSocket, ride_id: str):
    await ws_manager.connect_ride(ride_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect_ride(ride_id, websocket)

# Mount Frontend Static Files
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if not os.path.exists(frontend_dir):
    frontend_dir = os.path.abspath("frontend")

if os.path.exists(frontend_dir):
    @app.get("/")
    async def index_redirect():
        return RedirectResponse(url="/index.html")

    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

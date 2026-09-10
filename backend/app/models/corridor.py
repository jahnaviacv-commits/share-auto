import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class Corridor(Base):
    __tablename__ = "corridors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(20), unique=True, index=True, nullable=False)  # e.g. H1, H2, H3, H4, H5
    name = Column(String(255), nullable=False)                         # e.g. Route H1 Express
    description = Column(String(500), nullable=True)                  # e.g. HITEC City Metro ↔ Gachibowli DLF Phase 2
    origin_name = Column(String(255), nullable=False)
    destination_name = Column(String(255), nullable=False)
    distance_km = Column(Float, nullable=False, default=7.9)
    fixed_fare = Column(Float, nullable=False, default=25.0)           # ₹25
    headway_mins = Column(Integer, nullable=False, default=3)          # 2-3 mins
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    stations = relationship("Station", back_populates="corridor", order_by="Station.stop_order", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="current_corridor")
    rides = relationship("Ride", back_populates="corridor")
    hotspots = relationship("DemandHotspot", back_populates="corridor")

class Station(Base):
    __tablename__ = "stations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    corridor_id = Column(String(36), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    stop_order = Column(Integer, nullable=False, default=1)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    concourse_bay = Column(String(100), nullable=True)                # e.g. "Bay 4", "Gate 2"
    distance_from_start_km = Column(Float, nullable=False, default=0.0)
    is_verified_stand = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    corridor = relationship("Corridor", back_populates="stations")
    pickup_requests = relationship("RideRequest", foreign_keys="RideRequest.station_id", back_populates="station")
    hotspot = relationship("DemandHotspot", back_populates="station", uselist=False)

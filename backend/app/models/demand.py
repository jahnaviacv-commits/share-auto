import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class DemandHotspot(Base):
    __tablename__ = "demand_hotspots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    station_id = Column(String(36), ForeignKey("stations.id", ondelete="CASCADE"), unique=True, nullable=False)
    corridor_id = Column(String(36), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False)
    
    waiting_passengers = Column(Integer, default=0, nullable=False)
    avg_wait_mins = Column(Float, default=4.0, nullable=False)
    autos_at_stand = Column(Integer, default=2, nullable=False)
    surge_level = Column(String(20), default="MEDIUM", nullable=False) # HIGH, MEDIUM, NORMAL
    
    split_primary_count = Column(Integer, default=18, nullable=False)
    split_secondary_count = Column(Integer, default=12, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    station = relationship("Station", back_populates="hotspot")
    corridor = relationship("Corridor", back_populates="hotspots")

class DemandMetric(Base):
    __tablename__ = "demand_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    corridor_id = Column(String(36), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    time_bin = Column(String(20), nullable=False)                     # e.g. "08:30 AM"
    passenger_demand = Column(Integer, default=50, nullable=False)
    capacity_deployed = Column(Integer, default=60, nullable=False)
    load_factor_percent = Column(Float, default=75.0, nullable=False)

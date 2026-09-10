import uuid
from datetime import datetime
import enum
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class RideStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    DRIVER_ARRIVING = "DRIVER_ARRIVING"
    DRIVER_ARRIVED = "DRIVER_ARRIVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class RideRequest(Base):
    __tablename__ = "ride_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_code = Column(String(50), unique=True, index=True, nullable=False) # e.g. #ZO-4928
    passenger_id = Column(String(36), ForeignKey("passengers.id", ondelete="CASCADE"), nullable=False)
    station_id = Column(String(36), ForeignKey("stations.id", ondelete="CASCADE"), nullable=False)
    destination_station_id = Column(String(36), ForeignKey("stations.id", ondelete="SET NULL"), nullable=True)
    corridor_id = Column(String(36), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False)
    commuter_count = Column(Integer, default=1, nullable=False)
    status = Column(Enum(RideStatus), default=RideStatus.REQUESTED, nullable=False)
    
    assigned_driver_id = Column(String(36), ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    passenger = relationship("Passenger", back_populates="ride_requests")
    station = relationship("Station", foreign_keys=[station_id], back_populates="pickup_requests")
    destination_station = relationship("Station", foreign_keys=[destination_station_id])
    corridor = relationship("Corridor")
    assigned_driver = relationship("Driver")

class Ride(Base):
    __tablename__ = "rides"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ride_code = Column(String(50), unique=True, index=True, nullable=False)     # e.g. RIDE-8812
    corridor_id = Column(String(36), ForeignKey("corridors.id", ondelete="CASCADE"), nullable=False)
    driver_id = Column(String(36), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    origin_station_id = Column(String(36), ForeignKey("stations.id", ondelete="SET NULL"), nullable=True)
    destination_station_id = Column(String(36), ForeignKey("stations.id", ondelete="SET NULL"), nullable=True)
    
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    passenger_count = Column(Integer, default=4, nullable=False)
    fare_per_passenger = Column(Float, default=20.0, nullable=False)
    total_fare = Column(Float, default=80.0, nullable=False)
    status = Column(Enum(RideStatus), default=RideStatus.IN_PROGRESS, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    corridor = relationship("Corridor", back_populates="rides")
    driver = relationship("Driver", back_populates="rides")
    vehicle = relationship("Vehicle", back_populates="rides")
    origin_station = relationship("Station", foreign_keys=[origin_station_id])
    destination_station = relationship("Station", foreign_keys=[destination_station_id])
    payments = relationship("Payment", back_populates="ride", cascade="all, delete-orphan")

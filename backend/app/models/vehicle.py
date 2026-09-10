import uuid
from datetime import datetime
import enum
from sqlalchemy import Column, String, Boolean, Float, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class VehicleStatus(str, enum.Enum):
    ON_ROAD = "ON_ROAD"
    STANDBY = "STANDBY"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_code = Column(String(50), unique=True, index=True, nullable=False)   # AUTO-HYD-501, AUTO-HYD-903
    plate_number = Column(String(50), unique=True, index=True, nullable=False)   # TS 08 UB 4192, AP 28 TB 7721
    chassis_model = Column(String(255), nullable=False)                         # Bajaj RE E-Tec 9.0 (5-Seater Feeder)
    chassis_number = Column(String(100), nullable=True)                         # MD2A24AZ9PWB48102
    seater_type = Column(Integer, default=5, nullable=False)                     # 5 or 9
    fuel_type = Column(String(50), default="CNG Hybrid", nullable=False)        # CNG Hybrid, EV, CNG
    
    current_driver_id = Column(String(36), ForeignKey("drivers.id", ondelete="SET NULL"), unique=True, nullable=True)
    current_corridor_id = Column(String(36), ForeignKey("corridors.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(VehicleStatus), default=VehicleStatus.ON_ROAD, nullable=False)
    
    # Telemetry
    current_lat = Column(Float, nullable=False, default=17.4474)                 # HITEC City
    current_lng = Column(Float, nullable=False, default=78.3762)
    speed = Column(Float, default=28.0, nullable=False)                          # km/h
    soc_battery_percent = Column(Float, default=82.0, nullable=False)            # 82%
    assigned_stop = Column(String(255), default="Mindspace Pillar #12", nullable=True)
    total_fare_collected = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    current_driver = relationship("Driver", back_populates="vehicle")
    current_corridor = relationship("Corridor", back_populates="vehicles")
    seats = relationship("Seat", back_populates="vehicle", cascade="all, delete-orphan", order_by="Seat.seat_number")
    rides = relationship("Ride", back_populates="vehicle")

class Seat(Base):
    __tablename__ = "seats"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id = Column(String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    seat_number = Column(Integer, nullable=False)                     # 1, 2, 3...
    seat_label = Column(String(50), nullable=False)                   # "Seat 1", "S1"
    gender_preference = Column(String(20), default="free", nullable=False) # "male", "female", "free"
    passenger_name = Column(String(100), nullable=True)
    is_occupied = Column(Boolean, default=False, nullable=False)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="seats")

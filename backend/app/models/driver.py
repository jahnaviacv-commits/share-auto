import uuid
from datetime import datetime
import enum
from sqlalchemy import Column, String, Boolean, Float, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class DriverStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    ON_TRIP = "ON_TRIP"
    BREAK = "BREAK"

class KYCStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FLAGGED = "FLAGGED"

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    driver_code = Column(String(50), unique=True, index=True, nullable=False)  # e.g. ZO-DRV-4102
    commercial_badge = Column(String(100), nullable=True)                      # e.g. #HYD-AUT-88291
    license_number = Column(String(100), nullable=True)                        # e.g. DL-09-2018-4912
    experience_years = Column(Integer, default=5, nullable=False)
    
    status = Column(Enum(DriverStatus), default=DriverStatus.OFFLINE, nullable=False)
    rating = Column(Float, default=4.9, nullable=False)
    total_trips = Column(Integer, default=0, nullable=False)
    earnings_today = Column(Float, default=0.0, nullable=False)
    target_earnings = Column(Float, default=800.0, nullable=False)
    
    # Compliance & KYC Gate
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.APPROVED, nullable=False)
    aadhaar_verified = Column(Boolean, default=True, nullable=False)
    police_cleared = Column(Boolean, default=True, nullable=False)
    rejection_reason = Column(String(500), nullable=True)

    assigned_corridor_id = Column(String(36), ForeignKey("corridors.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="driver_profile")
    documents = relationship("DriverDocument", back_populates="driver", cascade="all, delete-orphan")
    assigned_corridor = relationship("Corridor")
    vehicle = relationship("Vehicle", back_populates="current_driver", uselist=False)
    rides = relationship("Ride", back_populates="driver")
    payments = relationship("Payment", back_populates="driver")

class DriverDocument(Base):
    __tablename__ = "driver_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    driver_id = Column(String(36), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(String(50), nullable=False)  # DRIVING_LICENSE, AADHAAR, POLICE_CLEARANCE, PAN
    doc_number = Column(String(100), nullable=False)
    expiry_date = Column(DateTime, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    driver = relationship("Driver", back_populates="documents")

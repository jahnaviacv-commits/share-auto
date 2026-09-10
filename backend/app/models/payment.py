import uuid
from datetime import datetime
import enum
from sqlalchemy import Column, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class PaymentMethod(str, enum.Enum):
    UPI_QR = "UPI_QR"
    CASH = "CASH"
    WALLET = "WALLET"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ride_id = Column(String(36), ForeignKey("rides.id", ondelete="CASCADE"), nullable=False)
    driver_id = Column(String(36), ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)
    passenger_id = Column(String(36), ForeignKey("passengers.id", ondelete="SET NULL"), nullable=True)
    
    amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.UPI_QR, nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.COMPLETED, nullable=False)
    transaction_ref = Column(String(100), unique=True, index=True, nullable=False) # e.g. UPI-TXN-90218
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ride = relationship("Ride", back_populates="payments")
    driver = relationship("Driver", back_populates="payments")
    passenger = relationship("Passenger")

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.user import UserRole
from app.models.driver import DriverStatus, KYCStatus
from app.models.vehicle import VehicleStatus
from app.models.ride import RideStatus
from app.models.payment import PaymentMethod, PaymentStatus

# Auth Schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    password: str
    role: UserRole = UserRole.PASSENGER

class LoginRequest(BaseModel):
    email: Optional[str] = None
    identifier: Optional[str] = None
    username: Optional[str] = None
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    full_name: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    phone: Optional[str] = None
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

# Corridor & Station Schemas
class StationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    stop_order: int
    latitude: float
    longitude: float
    concourse_bay: Optional[str] = None
    distance_from_start_km: float
    is_verified_stand: bool

class CorridorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: Optional[str] = None
    origin_name: str
    destination_name: str
    distance_km: float
    fixed_fare: float
    headway_mins: int
    is_active: bool
    stations: List[StationResponse] = []

# Vehicle & Seat Schemas
class SeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seat_number: int
    seat_label: str
    gender_preference: str  # male, female, free
    passenger_name: Optional[str] = None
    is_occupied: bool

class VehicleResponse(BaseModel):
    id: str
    vehicle_code: str
    plate_number: str
    chassis_model: str
    seater_type: int
    fuel_type: str
    status: str
    current_lat: float
    current_lng: float
    speed: float
    soc_battery_percent: float
    assigned_stop: Optional[str] = None
    total_fare_collected: float
    driver_name: Optional[str] = None
    driver_badge: Optional[str] = None
    driver_rating: Optional[float] = None
    occupied_seats: int = 0
    available_seats: int = 0
    corridor_code: Optional[str] = None

class VehicleInspectResponse(BaseModel):
    id: str
    chassis: str
    driverName: str
    driverBadge: str
    driverPhone: str
    speed: str
    soc: str
    fare: str
    assignedStop: str
    type: int  # 5 or 9
    seats: List[Dict[str, Any]]

class VehicleCommandRequest(BaseModel):
    action: str  # "Contact Driver", "Reroute"
    target_stop: Optional[str] = None

# Ride Request & Booking Schemas
class WaitingSignalRequest(BaseModel):
    station_id: str
    destination_station_id: Optional[str] = None
    corridor_id: str
    commuter_count: int = 1

class WaitingSignalResponse(BaseModel):
    id: str
    request_code: str
    status: str
    station_name: str
    destination_name: Optional[str] = None
    corridor_code: str
    commuter_count: int
    created_at: datetime

class RideStatusUpdate(BaseModel):
    status: RideStatus

class BookSeatRequest(BaseModel):
    vehicle_code: str
    seat_number: Optional[int] = None
    corridor_id: Optional[str] = None

# Driver Schemas
class DriverStatusUpdate(BaseModel):
    is_online: bool

class DriverLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    speed: Optional[float] = 0.0

class DriverDashboardKPIs(BaseModel):
    status: str
    status_desc: str
    today_earnings: float
    target_earnings: float
    earnings_progress_pct: float
    today_trips: int
    current_station: str
    current_station_bay: str
    passengers_waiting_here: int
    active_corridor: str

class TripLedgerItem(BaseModel):
    id: str
    ride_code: str
    route: str
    timestamp: str
    passenger_count: int
    fare: float
    status: str
    payment_type: str

class EarningsSummary(BaseModel):
    today_earnings: float
    shift_net_earnings: float
    completed_runs: int
    target_incentive_remaining: float
    upi_qr_percent: float
    cash_percent: float
    recent_ledger: List[TripLedgerItem]

class DriverProfileUpdate(BaseModel):
    legal_name: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    language: Optional[str] = "en"

# Admin Schemas
class AdminKPIs(BaseModel):
    active_autos: int
    online_percentage: float
    five_seaters_count: int
    nine_seaters_count: int
    total_capacity: int
    occupied_seats: int
    available_seats: int
    occupancy_pct: float
    male_passengers: int
    female_passengers: int
    high_crowding_autos_count: int
    ai_optimization_score: float
    avg_wait_time_mins: float
    last_updated: str

class DriverApprovalItem(BaseModel):
    id: str
    applicant_name: str
    application_code: str
    phone: str
    age: int
    experience_years: int
    assigned_corridor: str
    dl_number: str
    target_chassis: str
    target_chassis_desc: str
    kyc_status: str

class FleetVehicleItem(BaseModel):
    id: str
    vehicle_code: str
    plate_number: str
    chassis_model: str
    seater_type: int
    pilot_name: Optional[str] = None
    soc_battery_percent: float
    status: str
    assigned_corridor: str

# Chat Schemas
class ChatMessageRequest(BaseModel):
    message: str

class ChatMessageResponse(BaseModel):
    response: str
    suggestions: List[str] = []
    card_data: Optional[Dict[str, Any]] = None

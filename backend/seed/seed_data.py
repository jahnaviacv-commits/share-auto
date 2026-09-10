import sys
import os
from datetime import datetime, timedelta
import uuid

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import sync_engine, Base, SyncSessionLocal
from app.core.security import get_password_hash
from app.models import (
    User, Passenger, Driver, DriverDocument,
    Corridor, Station, Vehicle, Seat,
    Ride, RideRequest, Payment, DemandHotspot, DemandMetric,
    UserRole, DriverStatus, KYCStatus, VehicleStatus,
    RideStatus, PaymentMethod, PaymentStatus
)

def run_seed():
    print("Beginning database seed for ZeroOne Mobility Platform...")
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)

    with SyncSessionLocal() as session:
        # 1. Users
        admin_user = User(
            email="admin@zeroone.com",
            phone="+91 98000 00001",
            full_name="Fleet Controller (Super Admin)",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN
        )
        session.add(admin_user)

        passenger_user = User(
            email="aarav@zeroone.com",
            phone="+91 98490 12345",
            full_name="Aarav Sharma",
            hashed_password=get_password_hash("passenger123"),
            role=UserRole.PASSENGER
        )
        session.add(passenger_user)

        venkat_user = User(
            email="venkat@zeroone.com",
            phone="+91 98480 22341",
            full_name="Venkat Rao",
            hashed_password=get_password_hash("driver123"),
            role=UserRole.DRIVER
        )
        session.add(venkat_user)

        narsimha_user = User(
            email="narsimha@zeroone.com",
            phone="+91 98492 11042",
            full_name="K. Narsimha Rao",
            hashed_password=get_password_hash("driver123"),
            role=UserRole.DRIVER
        )
        session.add(narsimha_user)

        ramesh_user = User(
            email="ramesh@zeroone.com",
            phone="+91 98481 33445",
            full_name="Ramesh Goud",
            hashed_password=get_password_hash("driver123"),
            role=UserRole.DRIVER
        )
        session.add(ramesh_user)

        suresh_user = User(
            email="suresh@zeroone.com",
            phone="+91 98482 55667",
            full_name="Suresh Kumar",
            hashed_password=get_password_hash("driver123"),
            role=UserRole.DRIVER
        )
        session.add(suresh_user)

        session.flush()

        # 2. Corridors
        corridor_h1 = Corridor(
            code="H1",
            name="Route H1 Express",
            description="HITEC City Metro ⇄ Gachibowli DLF Phase 2",
            origin_name="HITEC City Metro Stand 2",
            destination_name="Gachibowli DLF Phase 2",
            distance_km=7.9,
            fixed_fare=25.0,
            headway_mins=3,
            is_active=True
        )
        session.add(corridor_h1)

        corridor_h2 = Corridor(
            code="H2",
            name="Route H2 Metro Connector",
            description="Kukatpally JNTU ⇄ HITEC City Cyber Gateway",
            origin_name="Kukatpally JNTU",
            destination_name="HITEC City Cyber Gateway",
            distance_km=6.4,
            fixed_fare=25.0,
            headway_mins=4,
            is_active=True
        )
        session.add(corridor_h2)

        corridor_h3 = Corridor(
            code="H3",
            name="Route H3 Financial Hub Express",
            description="Miyapur Metro ⇄ Financial District / Waverock",
            origin_name="Miyapur Metro Cross",
            destination_name="Financial District",
            distance_km=11.2,
            fixed_fare=35.0,
            headway_mins=5,
            is_active=True
        )
        session.add(corridor_h3)

        corridor_h4 = Corridor(
            code="H4",
            name="Route H4 Secunderabad East Link",
            description="Secunderabad Station ⇄ ECIL Cross Roads",
            origin_name="Secunderabad Station",
            destination_name="ECIL Cross Roads",
            distance_km=9.8,
            fixed_fare=25.0,
            headway_mins=5,
            is_active=True
        )
        session.add(corridor_h4)

        corridor_h5 = Corridor(
            code="H5",
            name="Route H5 Old City Artery",
            description="Secunderabad Railway Station ↔ ECIL Cross Roads",
            origin_name="Secunderabad Stn",
            destination_name="ECIL X-Roads",
            distance_km=9.8,
            fixed_fare=25.0,
            headway_mins=4,
            is_active=True
        )
        session.add(corridor_h5)

        session.flush()

        # 3. Stations for H1
        h1_st1 = Station(corridor_id=corridor_h1.id, name="HITEC City Metro Stand 2", stop_order=1, latitude=17.4474, longitude=78.3762, concourse_bay="Bay 4", distance_from_start_km=0.0, is_verified_stand=True)
        h1_st2 = Station(corridor_id=corridor_h1.id, name="Cyber Towers", stop_order=2, latitude=17.4495, longitude=78.3790, concourse_bay="Pillar 14", distance_from_start_km=1.8, is_verified_stand=True)
        h1_st3 = Station(corridor_id=corridor_h1.id, name="Mindspace Junction", stop_order=3, latitude=17.4420, longitude=78.3815, concourse_bay="Gate 1", distance_from_start_km=3.4, is_verified_stand=True)
        h1_st4 = Station(corridor_id=corridor_h1.id, name="Bio-Diversity Park", stop_order=4, latitude=17.4350, longitude=78.3680, concourse_bay="Bay 2", distance_from_start_km=5.6, is_verified_stand=True)
        h1_st5 = Station(corridor_id=corridor_h1.id, name="Gachibowli DLF Phase 2", stop_order=5, latitude=17.4390, longitude=78.3580, concourse_bay="Terminus Bay", distance_from_start_km=7.9, is_verified_stand=True)
        session.add_all([h1_st1, h1_st2, h1_st3, h1_st4, h1_st5])

        # Stations for H3 / Lingampally Corridors
        st_ling = Station(corridor_id=corridor_h3.id, name="Lingampally Station", stop_order=1, latitude=17.4834, longitude=78.3180, concourse_bay="Bay 1 & 2", distance_from_start_km=0.0, is_verified_stand=True)
        st_nalla = Station(corridor_id=corridor_h3.id, name="Nallagandla Flyover", stop_order=2, latitude=17.4780, longitude=78.3050, concourse_bay="Stand 3", distance_from_start_km=2.4, is_verified_stand=True)
        st_tella = Station(corridor_id=corridor_h3.id, name="Tellapur Junction", stop_order=3, latitude=17.4650, longitude=78.2910, concourse_bay="Bay A", distance_from_start_km=4.8, is_verified_stand=True)
        st_osman = Station(corridor_id=corridor_h3.id, name="Osman Nagar Cross", stop_order=4, latitude=17.4580, longitude=78.2750, concourse_bay="Main Gate", distance_from_start_km=7.2, is_verified_stand=True)
        st_patan = Station(corridor_id=corridor_h3.id, name="Patancheru ICRISAT", stop_order=5, latitude=17.5250, longitude=78.2610, concourse_bay="Highway Bay 1", distance_from_start_km=11.5, is_verified_stand=True)
        st_bhel = Station(corridor_id=corridor_h3.id, name="BHEL Township Gate", stop_order=6, latitude=17.4912, longitude=78.3050, concourse_bay="Main Checkpost #B-2", distance_from_start_km=14.0, is_verified_stand=True)
        st_miya = Station(corridor_id=corridor_h3.id, name="Miyapur Metro Cross", stop_order=7, latitude=17.4968, longitude=78.3610, concourse_bay="Pillar 24 South", distance_from_start_km=19.2, is_verified_stand=True)
        session.add_all([st_ling, st_nalla, st_tella, st_osman, st_patan, st_bhel, st_miya])

        session.flush()

        # 4. Passenger Profile
        passenger = Passenger(
            user_id=passenger_user.id,
            commuter_id="ZO-4928",
            total_trips=24,
            default_corridor_id=corridor_h1.id
        )
        session.add(passenger)

        # 5. Driver Profiles
        venkat_driver = Driver(
            user_id=venkat_user.id,
            driver_code="ZO-DRV-4102",
            commercial_badge="#HYD-AUT-88291",
            license_number="DL-09-2018-4912",
            experience_years=8,
            status=DriverStatus.ONLINE,
            rating=4.92,
            total_trips=14,
            earnings_today=620.0,
            target_earnings=800.0,
            kyc_status=KYCStatus.APPROVED,
            aadhaar_verified=True,
            police_cleared=True,
            assigned_corridor_id=corridor_h1.id
        )
        session.add(venkat_driver)

        ramesh_driver = Driver(
            user_id=ramesh_user.id,
            driver_code="ZO-DRV-3011",
            commercial_badge="#HYD-AUT-66230",
            license_number="DL-09-2017-3011",
            experience_years=9,
            status=DriverStatus.ONLINE,
            rating=4.88,
            total_trips=18,
            earnings_today=780.0,
            target_earnings=800.0,
            kyc_status=KYCStatus.APPROVED,
            aadhaar_verified=True,
            police_cleared=True,
            assigned_corridor_id=corridor_h1.id
        )
        session.add(ramesh_driver)

        suresh_driver = Driver(
            user_id=suresh_user.id,
            driver_code="ZO-DRV-5088",
            commercial_badge="#HYD-AUT-55119",
            license_number="DL-09-2019-5088",
            experience_years=6,
            status=DriverStatus.ONLINE,
            rating=4.85,
            total_trips=12,
            earnings_today=540.0,
            target_earnings=800.0,
            kyc_status=KYCStatus.APPROVED,
            aadhaar_verified=True,
            police_cleared=True,
            assigned_corridor_id=corridor_h1.id
        )
        session.add(suresh_driver)

        narsimha_driver = Driver(
            user_id=narsimha_user.id,
            driver_code="ZO-DRV-8841",
            commercial_badge="#HYD-AUT-77190",
            license_number="DL-09-2018-8841",
            experience_years=11,
            status=DriverStatus.OFFLINE,
            rating=4.8,
            total_trips=0,
            earnings_today=0.0,
            target_earnings=800.0,
            kyc_status=KYCStatus.PENDING,
            aadhaar_verified=True,
            police_cleared=True,
            assigned_corridor_id=corridor_h1.id
        )
        session.add(narsimha_driver)

        session.flush()

        # 6. Vehicles
        # HYD-501 (5-seater feeder)
        auto_501 = Vehicle(
            vehicle_code="AUTO-HYD-501",
            plate_number="AP 28 TB 7721",
            chassis_model="Bajaj RE E-Tec 9.0 (5-Seater Feeder)",
            chassis_number="MD2A24AZ9PWB48102",
            seater_type=5,
            fuel_type="CNG Hybrid",
            current_driver_id=venkat_driver.id,
            current_corridor_id=corridor_h1.id,
            status=VehicleStatus.ON_ROAD,
            current_lat=17.4474,
            current_lng=78.3762,
            speed=32.0,
            soc_battery_percent=82.0,
            assigned_stop="Mindspace Metro Pillar #12",
            total_fare_collected=840.0
        )
        session.add(auto_501)

        # HYD-903 (9-seater maxi)
        auto_903 = Vehicle(
            vehicle_code="AUTO-HYD-903",
            plate_number="TS 08 UB 4192",
            chassis_model="Mahindra Treo Plus XL (9-Seater Maxi)",
            chassis_number="MD2A99XL9PWB10041",
            seater_type=9,
            fuel_type="EV",
            current_driver_id=ramesh_driver.id,
            current_corridor_id=corridor_h1.id,
            status=VehicleStatus.ON_ROAD,
            current_lat=17.4420,
            current_lng=78.3815,
            speed=28.0,
            soc_battery_percent=64.0,
            assigned_stop="Bio-Diversity Flyover Node",
            total_fare_collected=1240.0
        )
        session.add(auto_903)

        # HYD-508 (5-seater, full capacity)
        auto_508 = Vehicle(
            vehicle_code="AUTO-HYD-508",
            plate_number="TS 07 EA 9912",
            chassis_model="Piaggio Ape E-City (5-Seater Feeder)",
            chassis_number="MD2A55EC9PWB99120",
            seater_type=5,
            fuel_type="EV",
            current_driver_id=suresh_driver.id,
            current_corridor_id=corridor_h1.id,
            status=VehicleStatus.ON_ROAD,
            current_lat=17.4495,
            current_lng=78.3790,
            speed=36.0,
            soc_battery_percent=91.0,
            assigned_stop="Bharat Nagar Platform Gate 2",
            total_fare_collected=620.0
        )
        session.add(auto_508)

        # HYD-911 (9-seater)
        auto_911 = Vehicle(
            vehicle_code="AUTO-HYD-911",
            plate_number="TS 09 XY 3021",
            chassis_model="Atul Elite Cargo/Passenger (9-Seater)",
            chassis_number="MD2A33EL9PWB77102",
            seater_type=9,
            fuel_type="CNG",
            current_corridor_id=corridor_h5.id,
            status=VehicleStatus.ON_ROAD,
            current_lat=17.4399,
            current_lng=78.5017,
            speed=24.0,
            soc_battery_percent=45.0,
            assigned_stop="Erragadda Rythu Bazar",
            total_fare_collected=480.0
        )
        session.add(auto_911)

        # Extra vehicles for dashboard metrics
        auto_904 = Vehicle(
            vehicle_code="AUTO-HYD-904",
            plate_number="TS 08 UB 9040",
            chassis_model="Mahindra Treo 9-Seater",
            seater_type=9,
            fuel_type="EV",
            current_corridor_id=corridor_h2.id,
            status=VehicleStatus.ON_ROAD,
            current_lat=17.4380,
            current_lng=78.4480,
            speed=26.0,
            soc_battery_percent=78.0,
            assigned_stop="Mythrivanam Junction",
            total_fare_collected=960.0
        )
        auto_512 = Vehicle(
            vehicle_code="AUTO-HYD-512",
            plate_number="TS 09 AB 5120",
            chassis_model="Bajaj RE 5-Seater",
            seater_type=5,
            fuel_type="CNG",
            current_corridor_id=corridor_h4.id,
            status=VehicleStatus.ON_ROAD,
            current_lat=17.4420,
            current_lng=78.4980,
            speed=0.0,
            soc_battery_percent=88.0,
            assigned_stop="Paradise Circle",
            total_fare_collected=750.0
        )
        auto_908 = Vehicle(
            vehicle_code="AUTO-HYD-908",
            plate_number="TS 07 CD 9080",
            chassis_model="Atul 9-Seater Cruiser",
            seater_type=9,
            fuel_type="CNG",
            current_corridor_id=corridor_h3.id,
            status=VehicleStatus.ON_ROAD,
            current_lat=17.4850,
            current_lng=78.3550,
            speed=30.0,
            soc_battery_percent=70.0,
            assigned_stop="Forum Sujana Mall",
            total_fare_collected=540.0
        )
        session.add_all([auto_904, auto_512, auto_908])

        session.flush()

        # 7. Cabin Seats Setup
        # AUTO-HYD-501 (4 occupied, 1 free)
        seats_501 = [
            Seat(vehicle_id=auto_501.id, seat_number=1, seat_label="Seat 1", gender_preference="male", passenger_name="Arun V.", is_occupied=True),
            Seat(vehicle_id=auto_501.id, seat_number=2, seat_label="Seat 2", gender_preference="male", passenger_name="Praveen", is_occupied=True),
            Seat(vehicle_id=auto_501.id, seat_number=3, seat_label="Seat 3", gender_preference="female", passenger_name="Sneha", is_occupied=True),
            Seat(vehicle_id=auto_501.id, seat_number=4, seat_label="Seat 4", gender_preference="female", passenger_name="Deepa", is_occupied=True),
            Seat(vehicle_id=auto_501.id, seat_number=5, seat_label="Seat 5", gender_preference="free", passenger_name=None, is_occupied=False),
        ]
        session.add_all(seats_501)

        # AUTO-HYD-903 (5 occupied, 4 free)
        seats_903 = [
            Seat(vehicle_id=auto_903.id, seat_number=1, seat_label="S1", gender_preference="male", passenger_name="Vikram", is_occupied=True),
            Seat(vehicle_id=auto_903.id, seat_number=2, seat_label="S2", gender_preference="male", passenger_name="Kiran", is_occupied=True),
            Seat(vehicle_id=auto_903.id, seat_number=3, seat_label="S3", gender_preference="male", passenger_name="Siddharth", is_occupied=True),
            Seat(vehicle_id=auto_903.id, seat_number=4, seat_label="S4", gender_preference="female", passenger_name="Pooja", is_occupied=True),
            Seat(vehicle_id=auto_903.id, seat_number=5, seat_label="S5", gender_preference="female", passenger_name="Ananya", is_occupied=True),
            Seat(vehicle_id=auto_903.id, seat_number=6, seat_label="S6", gender_preference="free", passenger_name=None, is_occupied=False),
            Seat(vehicle_id=auto_903.id, seat_number=7, seat_label="S7", gender_preference="free", passenger_name=None, is_occupied=False),
            Seat(vehicle_id=auto_903.id, seat_number=8, seat_label="S8", gender_preference="free", passenger_name=None, is_occupied=False),
            Seat(vehicle_id=auto_903.id, seat_number=9, seat_label="S9", gender_preference="free", passenger_name=None, is_occupied=False),
        ]
        session.add_all(seats_903)

        # AUTO-HYD-508 (5 occupied -> 100% Full)
        seats_508 = [
            Seat(vehicle_id=auto_508.id, seat_number=1, seat_label="Seat 1", gender_preference="male", passenger_name="Ramesh", is_occupied=True),
            Seat(vehicle_id=auto_508.id, seat_number=2, seat_label="Seat 2", gender_preference="male", passenger_name="Naresh", is_occupied=True),
            Seat(vehicle_id=auto_508.id, seat_number=3, seat_label="Seat 3", gender_preference="male", passenger_name="Govind", is_occupied=True),
            Seat(vehicle_id=auto_508.id, seat_number=4, seat_label="Seat 4", gender_preference="female", passenger_name="Lakshmi", is_occupied=True),
            Seat(vehicle_id=auto_508.id, seat_number=5, seat_label="Seat 5", gender_preference="female", passenger_name="Saritha", is_occupied=True),
        ]
        session.add_all(seats_508)

        # 8. Demand Hotspots
        hot_ling = DemandHotspot(
            station_id=st_ling.id,
            corridor_id=corridor_h3.id,
            waiting_passengers=30,
            avg_wait_mins=4.0,
            autos_at_stand=2,
            surge_level="HIGH",
            split_primary_count=18,
            split_secondary_count=12
        )
        hot_bhel = DemandHotspot(
            station_id=st_bhel.id,
            corridor_id=corridor_h3.id,
            waiting_passengers=18,
            avg_wait_mins=6.0,
            autos_at_stand=4,
            surge_level="MEDIUM",
            split_primary_count=11,
            split_secondary_count=7
        )
        hot_miya = DemandHotspot(
            station_id=st_miya.id,
            corridor_id=corridor_h3.id,
            waiting_passengers=12,
            avg_wait_mins=3.0,
            autos_at_stand=5,
            surge_level="NORMAL",
            split_primary_count=8,
            split_secondary_count=4
        )
        session.add_all([hot_ling, hot_bhel, hot_miya])

        # 9. Recent Completed Trips & Ledger for Venkat Rao
        now = datetime.utcnow()
        trip1 = Ride(
            ride_code="RUN-HYD-9121",
            corridor_id=corridor_h3.id,
            driver_id=venkat_driver.id,
            vehicle_id=auto_501.id,
            origin_station_id=st_miya.id,
            destination_station_id=st_ling.id,
            start_time=now - timedelta(minutes=48),
            end_time=now - timedelta(minutes=24),
            passenger_count=4,
            fare_per_passenger=20.0,
            total_fare=80.0,
            status=RideStatus.COMPLETED
        )
        trip2 = Ride(
            ride_code="RUN-HYD-9118",
            corridor_id=corridor_h3.id,
            driver_id=venkat_driver.id,
            vehicle_id=auto_501.id,
            origin_station_id=st_ling.id,
            destination_station_id=st_bhel.id,
            start_time=now - timedelta(minutes=85),
            end_time=now - timedelta(minutes=65),
            passenger_count=3,
            fare_per_passenger=20.0,
            total_fare=60.0,
            status=RideStatus.COMPLETED
        )
        trip3 = Ride(
            ride_code="RUN-HYD-9112",
            corridor_id=corridor_h3.id,
            driver_id=venkat_driver.id,
            vehicle_id=auto_501.id,
            origin_station_id=st_bhel.id,
            destination_station_id=st_miya.id,
            start_time=now - timedelta(minutes=130),
            end_time=now - timedelta(minutes=105),
            passenger_count=4,
            fare_per_passenger=20.0,
            total_fare=80.0,
            status=RideStatus.COMPLETED
        )
        session.add_all([trip1, trip2, trip3])
        session.flush()

        # Payments
        pay1 = Payment(ride_id=trip1.id, driver_id=venkat_driver.id, amount=80.0, payment_method=PaymentMethod.UPI_QR, status=PaymentStatus.COMPLETED, transaction_ref="UPI-QR-89104")
        pay2 = Payment(ride_id=trip2.id, driver_id=venkat_driver.id, amount=60.0, payment_method=PaymentMethod.CASH, status=PaymentStatus.COMPLETED, transaction_ref="CASH-TXN-89092")
        pay3 = Payment(ride_id=trip3.id, driver_id=venkat_driver.id, amount=80.0, payment_method=PaymentMethod.UPI_QR, status=PaymentStatus.COMPLETED, transaction_ref="UPI-QR-89078")
        session.add_all([pay1, pay2, pay3])

        # Active waiting signal demo
        req_demo = RideRequest(
            request_code="#ZO-4928",
            passenger_id=passenger.id,
            station_id=h1_st1.id,
            destination_station_id=h1_st5.id,
            corridor_id=corridor_h1.id,
            commuter_count=1,
            status=RideStatus.REQUESTED
        )
        session.add(req_demo)

        session.commit()
        print("Database seed completed successfully!")

if __name__ == "__main__":
    run_seed()

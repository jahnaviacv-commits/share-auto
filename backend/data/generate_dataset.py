"""
Generate realistic historical baseline dataset for Hyderabad Shared-Auto mobility demand.
Stops include:
- Miyapur Metro
- BHEL
- Lingampally Station
- Nallagandla
- Tellapur
- Osman Nagar
- Patancheru
- HITEC City Metro Stand 2

Represents 30 days of hourly aggregated commuter demand at key shared-auto pickup stands.
"""
import csv
import random
from datetime import datetime, timedelta

STOPS_CONFIG = {
    "Miyapur Metro": {"base": 24, "morning_mult": 1.6, "evening_mult": 2.2, "hub_type": "metro_interchange"},
    "BHEL": {"base": 16, "morning_mult": 1.8, "evening_mult": 1.5, "hub_type": "industrial_township"},
    "Lingampally Station": {"base": 28, "morning_mult": 2.0, "evening_mult": 2.3, "hub_type": "railway_interchange"},
    "Nallagandla": {"base": 18, "morning_mult": 2.1, "evening_mult": 1.7, "hub_type": "it_residential"},
    "Tellapur": {"base": 20, "morning_mult": 2.2, "evening_mult": 1.8, "hub_type": "it_residential"},
    "Osman Nagar": {"base": 12, "morning_mult": 1.7, "evening_mult": 1.4, "hub_type": "connecting_feeder"},
    "Patancheru": {"base": 15, "morning_mult": 1.6, "evening_mult": 1.6, "hub_type": "outer_industrial"},
    "HITEC City Metro Stand 2": {"base": 30, "morning_mult": 2.4, "evening_mult": 2.5, "hub_type": "core_it_hub"}
}

def generate_data(filepath="backend/data/hyderabad_shared_auto_demand.csv", days=30):
    start_date = datetime(2026, 8, 1, 0, 0, 0)
    fieldnames = [
        "timestamp", "stop_name", "hour", "day_of_week", "is_weekend",
        "is_peak_hour", "historical_avg_demand", "weather_factor",
        "recent_waiting_signals", "passenger_demand"
    ]

    random.seed(42)
    rows = []

    for d in range(days):
        current_day = start_date + timedelta(days=d)
        day_of_week = current_day.weekday() # 0 = Monday, 6 = Sunday
        is_weekend = 1 if day_of_week in [5, 6] else 0

        # Simulate weather: 85% clear, 10% cloudy, 5% rain
        weather_roll = random.random()
        weather = "RAIN" if weather_roll < 0.08 else ("CLOUDY" if weather_roll < 0.20 else "CLEAR")
        weather_mult = 1.35 if weather == "RAIN" else (1.05 if weather == "CLOUDY" else 1.0)

        for hour in range(24):
            is_morning_peak = 1 if (8 <= hour <= 11) else 0
            is_evening_peak = 1 if (17 <= hour <= 21) else 0
            is_peak_hour = 1 if (is_morning_peak or is_evening_peak) else 0

            # Time multiplier curve
            if 0 <= hour <= 4:
                time_mult = 0.15
            elif 5 <= hour <= 7:
                time_mult = 0.6
            elif is_morning_peak:
                time_mult = 1.9 if not is_weekend else 1.1
            elif 12 <= hour <= 16:
                time_mult = 0.85
            elif is_evening_peak:
                time_mult = 2.1 if not is_weekend else 1.3
            else: # 22-23
                time_mult = 0.4

            for stop_name, cfg in STOPS_CONFIG.items():
                base = cfg["base"]
                if is_morning_peak:
                    spec_mult = cfg["morning_mult"]
                elif is_evening_peak:
                    spec_mult = cfg["evening_mult"]
                else:
                    spec_mult = 1.0

                historical_avg = round(base * time_mult * (0.8 if is_weekend else 1.0), 1)

                # Simulated recent waiting signals correlate with demand
                waiting_signals = max(0, int(round(historical_avg * 0.25 + random.uniform(-2, 3))))

                # Noise & weather effect
                actual_demand = max(1, int(round(
                    historical_avg * spec_mult * weather_mult * random.uniform(0.9, 1.12) + (waiting_signals * 0.4)
                )))

                timestamp_str = (current_day + timedelta(hours=hour)).strftime("%Y-%m-%d %H:00:00")

                rows.append({
                    "timestamp": timestamp_str,
                    "stop_name": stop_name,
                    "hour": hour,
                    "day_of_week": day_of_week,
                    "is_weekend": is_weekend,
                    "is_peak_hour": is_peak_hour,
                    "historical_avg_demand": historical_avg,
                    "weather_factor": weather,
                    "recent_waiting_signals": waiting_signals,
                    "passenger_demand": actual_demand
                })

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} records in {filepath}")

if __name__ == "__main__":
    generate_data()

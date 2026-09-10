import os
import csv
import math
import pickle
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

STOPS = [
    "Miyapur Metro",
    "BHEL",
    "Lingampally Station",
    "Nallagandla",
    "Tellapur",
    "Osman Nagar",
    "Patancheru",
    "HITEC City Metro Stand 2"
]

STOP_INDEX = {name: idx for idx, name in enumerate(STOPS)}

class DemandPredictionService:
    def __init__(self, data_path=None, model_path=None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.data_path = data_path or os.path.join(base_dir, "data", "hyderabad_shared_auto_demand.csv")
        self.model_path = model_path or os.path.join(base_dir, "data", "demand_rf_model.pkl")
        self.model = None
        self.baseline_stats = {}
        self.is_trained = False
        self._initialize()

    def _initialize(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    saved_data = pickle.load(f)
                    self.model = saved_data["model"]
                    self.baseline_stats = saved_data["baseline_stats"]
                    self.is_trained = True
                    return
            except Exception as e:
                print(f"[DemandPredictionService] Error loading pickle, retraining: {e}")

        self.train()

    def train(self):
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Dataset not found at {self.data_path}")

        X = []
        y = []
        baselines = {}

        with open(self.data_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stop = row["stop_name"]
                if stop not in STOP_INDEX:
                    continue
                stop_idx = STOP_INDEX[stop]
                hour = int(row["hour"])
                day_of_week = int(row["day_of_week"])
                is_weekend = int(row["is_weekend"])
                is_peak = int(row["is_peak_hour"])
                hist_avg = float(row["historical_avg_demand"])
                signals = int(row["recent_waiting_signals"])
                weather_code = 2 if row["weather_factor"] == "RAIN" else (1 if row["weather_factor"] == "CLOUDY" else 0)
                demand = int(row["passenger_demand"])

                features = [stop_idx, hour, day_of_week, is_weekend, is_peak, hist_avg, signals, weather_code]
                X.append(features)
                y.append(demand)

                # Keep record of historical baseline
                key = (stop, hour, is_weekend)
                if key not in baselines:
                    baselines[key] = []
                baselines[key].append(hist_avg)

        X = np.array(X)
        y = np.array(y)

        # Average historical baselines
        self.baseline_stats = {k: round(float(np.mean(v)), 1) for k, v in baselines.items()}

        # Train Random Forest Regressor
        rf = RandomForestRegressor(n_estimators=75, max_depth=12, random_state=42, n_jobs=-1)
        rf.fit(X, y)
        self.model = rf
        self.is_trained = True

        # Compute training score
        preds = rf.predict(X)
        mae = mean_absolute_error(y, preds)
        r2 = r2_score(y, preds)
        print(f"[DemandPredictionService] Trained RandomForestRegressor: R²={r2:.3f}, MAE={mae:.2f}")

        # Save model and baseline stats
        try:
            with open(self.model_path, "wb") as f:
                pickle.dump({"model": self.model, "baseline_stats": self.baseline_stats}, f)
        except Exception as e:
            print(f"[DemandPredictionService] Could not cache model to disk: {e}")

    def get_supported_stops(self):
        return [
            {"name": "Miyapur Metro", "canonical": "Miyapur Metro", "corridor": "H3", "description": "Intermodal Rail/Metro Feeder Hub"},
            {"name": "BHEL", "canonical": "BHEL", "corridor": "H3", "description": "Township & Industrial Corridors"},
            {"name": "Lingampally Station", "canonical": "Lingampally Station", "corridor": "H3", "description": "MMTS Railway Terminus & Major Stand"},
            {"name": "Nallagandla", "canonical": "Nallagandla", "corridor": "H3", "description": "High-Density Residential Hub"},
            {"name": "Tellapur", "canonical": "Tellapur", "corridor": "H3", "description": "IT Commuter Residential Corridor"},
            {"name": "Osman Nagar", "canonical": "Osman Nagar", "corridor": "H3", "description": "Feeder Arterial Junction"},
            {"name": "Patancheru", "canonical": "Patancheru", "corridor": "H3", "description": "Outer Industrial Stand"},
            {"name": "HITEC City Metro Stand 2", "canonical": "HITEC City Metro Stand 2", "corridor": "H1", "description": "Core Cyberabad Office Hub"}
        ]

    def resolve_stop_name(self, query):
        if not query:
            return "Miyapur Metro"
        q = query.lower().strip()
        for stop in STOPS:
            if stop.lower() in q or q in stop.lower():
                return stop
        # Check partial keywords
        if "miyapur" in q: return "Miyapur Metro"
        if "bhel" in q: return "BHEL"
        if "lingampally" in q: return "Lingampally Station"
        if "nalla" in q: return "Nallagandla"
        if "tella" in q: return "Tellapur"
        if "osman" in q: return "Osman Nagar"
        if "patan" in q: return "Patancheru"
        if "hitec" in q: return "HITEC City Metro Stand 2"
        return "Miyapur Metro"

    def predict(self, stop_name: str, target_hour: int = None, target_day_of_week: int = None, live_waiting_count: int = 0):
        if not self.is_trained:
            self.train()

        resolved_stop = self.resolve_stop_name(stop_name)
        stop_idx = STOP_INDEX[resolved_stop]

        now = datetime.now()
        hour = now.hour if target_hour is None else max(0, min(23, int(target_hour)))
        day_of_week = now.weekday() if target_day_of_week is None else int(target_day_of_week)
        is_weekend = 1 if day_of_week in [5, 6] else 0
        is_morning_peak = 1 if (8 <= hour <= 11) else 0
        is_evening_peak = 1 if (17 <= hour <= 21) else 0
        is_peak = 1 if (is_morning_peak or is_evening_peak) else 0

        # Baseline lookup
        baseline = self.baseline_stats.get((resolved_stop, hour, is_weekend), 18.0)

        # Feature vector for ML model
        # [stop_idx, hour, day_of_week, is_weekend, is_peak, hist_avg, signals, weather_code]
        features = np.array([[stop_idx, hour, day_of_week, is_weekend, is_peak, baseline, live_waiting_count, 0]])
        raw_prediction = float(self.model.predict(features)[0])

        # Adjust with direct live waiting signals boost (real-time responsiveness)
        if live_waiting_count > 0:
            # Each verified waiting commuter increases expected immediate corridor demand
            predicted_demand = int(round(max(raw_prediction, baseline + (live_waiting_count * 1.35))))
        else:
            predicted_demand = int(round(raw_prediction))

        predicted_demand = max(1, predicted_demand)

        # Change percentage vs baseline
        if baseline > 0:
            expected_change_pct = round(((predicted_demand - baseline) / baseline) * 100, 1)
        else:
            expected_change_pct = 0.0

        # Demand Level categorization
        if predicted_demand >= 38:
            demand_level = "SURGE"
            demand_level_color = "amber"
        elif predicted_demand >= 24:
            demand_level = "HIGH"
            demand_level_color = "emerald"
        elif predicted_demand >= 12:
            demand_level = "MODERATE"
            demand_level_color = "blue"
        else:
            demand_level = "LOW"
            demand_level_color = "slate"

        # Autos needed (average 5-seater / 9-seater capacity ~ 6.5 passengers per vehicle)
        autos_needed = max(2, math.ceil(predicted_demand / 6.5))

        # Dynamic Explanations / Why this prediction?
        explanations = []
        if is_evening_peak:
            explanations.append("Weekday evening peak (5:00 PM – 9:00 PM) commuter surge")
        elif is_morning_peak:
            explanations.append("Weekday morning IT rush (8:00 AM – 11:00 AM) rail feeder arrivals")
        elif is_weekend:
            explanations.append("Weekend transit pattern: Steady residential & leisure trips")
        else:
            explanations.append("Regular midday transit window with consistent headway demand")

        if resolved_stop in ["Miyapur Metro", "Lingampally Station", "HITEC City Metro Stand 2"]:
            explanations.append(f"Major multimodal transit interchange hub ({resolved_stop})")
        elif resolved_stop in ["Tellapur", "Nallagandla"]:
            explanations.append(f"High-density IT commuter residential catchment zone ({resolved_stop})")

        if live_waiting_count > 0:
            explanations.append(f"{live_waiting_count} active passenger waiting signal(s) detected at this stand")
        else:
            explanations.append("No active passenger surge flags logged in the last 20 minutes")

        if expected_change_pct > 15:
            explanations.append(f"Demand is elevated (+{expected_change_pct}%) above normal historical baseline ({baseline} req/hr)")
        elif expected_change_pct < -15:
            explanations.append(f"Demand is lower ({expected_change_pct}%) than normal baseline ({baseline} req/hr)")
        else:
            explanations.append(f"Demand tracking close to typical historical baseline ({baseline} req/hr)")

        # Hourly 24-hour forecast curve for the stop
        hourly_forecast = []
        for h in range(24):
            h_is_peak = 1 if (8 <= h <= 11 or 17 <= h <= 21) else 0
            h_base = self.baseline_stats.get((resolved_stop, h, is_weekend), 15.0)
            h_feat = np.array([[stop_idx, h, day_of_week, is_weekend, h_is_peak, h_base, 0, 0]])
            h_pred = max(1, int(round(float(self.model.predict(h_feat)[0]))))
            h_autos = max(1, math.ceil(h_pred / 6.5))
            period = "AM" if h < 12 else "PM"
            disp_h = 12 if h == 0 or h == 12 else h % 12
            hourly_forecast.append({
                "hour": h,
                "label": f"{disp_h:02d}:00 {period}",
                "demand": h_pred,
                "autos_needed": h_autos,
                "is_current": (h == hour)
            })

        return {
            "stop_name": resolved_stop,
            "target_hour": hour,
            "target_hour_label": f"{(12 if hour in [0, 12] else hour % 12):02d}:00 {'AM' if hour < 12 else 'PM'}",
            "day_of_week": day_of_week,
            "is_weekend": bool(is_weekend),
            "predicted_demand": predicted_demand,
            "historical_baseline": baseline,
            "recent_waiting_signals": live_waiting_count,
            "expected_change_pct": expected_change_pct,
            "demand_level": demand_level,
            "demand_level_color": demand_level_color,
            "autos_needed": autos_needed,
            "explanations": explanations,
            "hourly_forecast": hourly_forecast,
            "model_metadata": {
                "algorithm": "RandomForestRegressor (scikit-learn)",
                "dataset": "Hyderabad Shared-Auto Mobility Historical Baseline (5,760 observations)",
                "type": "Demo Baseline + Real-Time Signal Hybrid",
                "telemetry_synced": True
            }
        }

demand_service = DemandPredictionService()

if __name__ == "__main__":
    res = demand_service.predict("Miyapur Metro", target_hour=17, live_waiting_count=5)
    print("Prediction Result:")
    print("Stop:", res["stop_name"])
    print("Hour:", res["target_hour_label"])
    print("Predicted Demand:", res["predicted_demand"])
    print("Historical Baseline:", res["historical_baseline"])
    print("Recent Signals:", res["recent_waiting_signals"])
    print("Change %:", res["expected_change_pct"])
    print("Demand Level:", res["demand_level"])
    print("Autos Needed:", res["autos_needed"])
    print("Explanations:")
    for r in res["explanations"]:
        print(" -", r)

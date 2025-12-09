
import json
import os
from datetime import datetime, date

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

DRIVERS_PATH = os.path.join(DATA_DIR, "drivers.json")
TRIPS_PATH = os.path.join(DATA_DIR, "trips.json")
ADMIN_LOGINS_PATH = os.path.join(DATA_DIR, "admin_logins.json")

# ----------------------------
# LANGUAGE LABELS (simple)
# ----------------------------
LANG_OPTIONS = ["English"]

labels = {
    "English": {
        "title_admin": "Mali Ride – Admin Dashboard",
        "subtitle": "Uber-style demo for Mali with distance-based pricing and nearest-driver matching.",
        "admin_auth": "Admin access",
        "admin_code_label": "Admin code",
        "admin_code_hint": "For production you would protect this page with a real secret.",
        "admin_code_wrong": "Wrong admin code.",
        "admin_locked": "Admin dashboard locked. Enter the admin code in the sidebar.",
        "metric_drivers": "Drivers",
        "metric_available": "Available",
        "metric_busy": "On trip",
        "metric_offline": "Offline",
        "metric_trips": "Trips",
        "metric_revenue": "Total fares",
        "metric_platform_revenue": "Platform revenue",
        "metric_driver_earnings": "Driver earnings",
        "drivers_table_header": "Registered drivers",
        "trips_table_header": "Trips",
        "download_drivers": "Download drivers as CSV",
        "download_trips": "Download trips as CSV",
        "no_drivers": "No drivers registered yet.",
        "status_options": ["Available", "On trip", "Offline"],
    }
}

ADMIN_CODE = "KaTaaAdmin2027"  # for post-demo mode

# ----------------------------
# Basic JSON helpers
# ----------------------------
def _read_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass

# ----------------------------
# DRIVERS
# ----------------------------
def load_drivers_from_db():
    return _read_json(DRIVERS_PATH)

def save_driver_to_db(driver):
    drivers = load_drivers_from_db()
    drivers.append(driver)
    _write_json(DRIVERS_PATH, drivers)

def update_driver_in_db(username, updates: dict):
    drivers = load_drivers_from_db()
    for d in drivers:
        if d.get("username") == username:
            d.update(updates)
            break
    _write_json(DRIVERS_PATH, drivers)

# ----------------------------
# TRIPS
# ----------------------------
def load_trips_from_db():
    return _read_json(TRIPS_PATH)

def save_trip_to_db(trip):
    trips = load_trips_from_db()
    trips.append(trip)
    _write_json(TRIPS_PATH, trips)

# ----------------------------
# ADMIN LOGIN TRACKING
# ----------------------------
def save_admin_login_to_db(info: dict):
    logins = _read_json(ADMIN_LOGINS_PATH)
    logins.append(info)
    _write_json(ADMIN_LOGINS_PATH, logins)

def load_admin_logins_from_db(limit: int = 300):
    logins = _read_json(ADMIN_LOGINS_PATH)
    # sort newest first
    for l in logins:
        ts = l.get("timestamp_iso")
        try:
            l["_ts"] = datetime.fromisoformat(ts)
        except Exception:
            l["_ts"] = datetime.min
    logins_sorted = sorted(logins, key=lambda x: x.get("_ts"), reverse=True)
    for l in logins_sorted:
        l.pop("_ts", None)
    return logins_sorted[:limit]

# ----------------------------
# COMMISSION TIERS - BAMAKO LAUNCH PROMO
# ----------------------------
def get_commission_pct(weekly_trips):
    # Launch promo: extremely competitive vs. Heetch
    if weekly_trips >= 60:
        return 8
    elif weekly_trips >= 40:
        return 10
    elif weekly_trips >= 20:
        return 12
    else:
        return 14

# ----------------------------
# PROMOTIONS
# ----------------------------
PROMO_CODES = {
    "WELCOME50": 0.50,
    "MALI10": 0.10,
    "EVENING15": 0.15,
    "STUDENT20": 0.20,
}

def apply_promo(code: str, fare: float):
    if not code:
        return fare, 0.0
    c = code.strip().upper()
    disc = PROMO_CODES.get(c)
    if not disc:
        return fare, 0.0
    discount = round(fare * disc)
    final = max(0, fare - discount)
    return final, discount

# ----------------------------
# GEO / PRICING HELPERS
# ----------------------------
from math import radians, sin, cos, atan2, sqrt

EARTH_KM = 6371.0

def haversine_miles(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    except Exception:
        return 0.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    km = EARTH_KM * c
    return km * 0.621371

BASE_FARE_XOF = 500
PER_MILE_XOF = 300

def compute_fare(distance_miles: float):
    return round(BASE_FARE_XOF + PER_MILE_XOF * max(distance_miles, 0))

MALI_CITIES = ["Bamako", "Sikasso", "Kayes", "Mopti", "Ségou"]
BKO_NEIGHBORHOODS = [
    "ACI 2000", "Kalaban Coura", "Badalabougou", "Lafiabougou", "Niarela"
]

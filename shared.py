
import json
import os
from datetime import datetime, date, timedelta
from math import radians, sin, cos, atan2, sqrt

import pandas as pd

# ----------------------------
# DATA STORAGE (LOCAL JSON "DB")
# ----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DRIVERS_PATH = os.path.join(DATA_DIR, "drivers.json")
TRIPS_PATH = os.path.join(DATA_DIR, "trips.json")
ADMIN_LOGINS_PATH = os.path.join(DATA_DIR, "admin_logins.json")

# ----------------------------
# LANGUAGE LABELS (English only demo)
# ----------------------------
LANG_OPTIONS = ["English"]

labels = {
    "English": {
        "title_admin": "Mali Ride – Admin Dashboard",
        "subtitle": "Real-time view of drivers, trips, promotions, and mobile usage for Mali.",
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

# In case you later want to lock admin:
ADMIN_CODE = "KaTaaAdmin2027"

# ----------------------------
# BASIC JSON HELPERS
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
    updated = []
    for d in drivers:
        if d.get("username") == username:
            d.update(updates)
        updated.append(d)
    _write_json(DRIVERS_PATH, updated)

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
# ADMIN LOGIN TRACKING (OPTIONAL)
# ----------------------------
def save_admin_login_to_db(info: dict):
    logins = _read_json(ADMIN_LOGINS_PATH)
    logins.append(info)
    _write_json(ADMIN_LOGINS_PATH, logins)

def load_admin_logins_from_db(limit: int = 300):
    logins = _read_json(ADMIN_LOGINS_PATH)
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
# COMMISSION TIERS (HEETCH-BEATING FOR BAMAKO)
# ----------------------------
def get_commission_pct(weekly_trips: int) -> int:
    """
    Launch promo tiers:
    - 60+ trips / week: 8%
    - 40–59 trips: 10%
    - 20–39 trips: 12%
    - 0–19 trips: 14%
    """
    if weekly_trips >= 60:
        return 8
    elif weekly_trips >= 40:
        return 10
    elif weekly_trips >= 20:
        return 12
    return 14

# ----------------------------
# PROMO CODES
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
    if disc is None:
        return fare, 0.0
    discount = round(fare * disc)
    final = max(0, fare - discount)
    return final, discount

# ----------------------------
# GEO / PRICING HELPERS
# ----------------------------
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

# ----------------------------
# CANCELLATION & RATING SETTINGS
# ----------------------------
PASSENGER_LATE_CANCEL_PCT = 0.75   # 75% of fare
DRIVER_CANCEL_PENALTY_PCT = 0.35   # 35% penalty -> company

DRIVER_RATING_START = 5.0
DRIVER_RATING_MIN = 1.0
DRIVER_RATING_CANCEL_PENALTY = 0.2  # rating drop per bad cancellation

def passenger_can_cancel(trip: dict, now_utc: datetime | None = None) -> bool:
    """
    Returns True if passenger is allowed to cancel with no fee.
    Rule: free cancellation only if >= 4 hours before scheduled time.
    """
    if now_utc is None:
        now_utc = datetime.utcnow()

    sched = trip.get("scheduled_for")
    if not sched:
        # if no scheduled time, treat as immediate -> no free window
        return False

    if isinstance(sched, str):
        try:
            sched = datetime.fromisoformat(sched)
        except Exception:
            return False

    return sched - now_utc >= timedelta(hours=4)

def apply_passenger_cancellation(trip: dict) -> dict:
    """
    Apply passenger cancellation rule:
    - If within 4h window => 75% fee of travel fare.
    - Fee goes to company (platform); driver earns 0 on this trip.
    """
    fare = float(trip.get("price_xof", 0))
    cancel_fee = round(fare * PASSENGER_LATE_CANCEL_PCT)

    trip["status"] = "cancelled_by_passenger"
    trip["cancellation_reason"] = "late_passenger"
    trip["cancellation_fee_xof"] = cancel_fee
    trip["platform_commission_xof"] = cancel_fee
    trip["driver_earnings_xof"] = 0
    return trip

def apply_driver_cancellation(trip: dict) -> dict:
    """
    Apply driver cancellation:
    - Company collects 35% of scheduled fare as penalty.
    - Driver gets 0 on this trip.
    """
    fare = float(trip.get("price_xof", 0))
    penalty = round(fare * DRIVER_CANCEL_PENALTY_PCT)

    trip["status"] = "cancelled_by_driver"
    trip["cancellation_reason"] = "driver_cancel"
    trip["cancellation_fee_xof"] = penalty
    trip["platform_commission_xof"] = penalty
    trip["driver_earnings_xof"] = 0
    return trip

def penalize_driver_rating(driver: dict) -> dict:
    """
    Drop rating a bit each time they cancel a scheduled trip.
    """
    rating = float(driver.get("rating", DRIVER_RATING_START))
    rating -= DRIVER_RATING_CANCEL_PENALTY
    rating = max(DRIVER_RATING_MIN, rating)
    driver["rating"] = round(rating, 2)
    driver["cancel_count"] = int(driver.get("cancel_count", 0)) + 1
    return driver

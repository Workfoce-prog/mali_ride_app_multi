
import streamlit as st
import pandas as pd
from datetime import datetime, date, time

from core.shared import (
    LANG_OPTIONS,
    labels,
    load_drivers_from_db,
    load_trips_from_db,
    save_trip_to_db,
    haversine_miles,
    compute_fare,
    apply_promo,
    passenger_can_cancel,
    apply_passenger_cancellation,
    TRIPS_PATH,
    _write_json,
    MALI_CITIES,
    BKO_NEIGHBORHOODS,
)

st.set_page_config(page_title="Mali Ride – Passenger App", layout="wide")

st.sidebar.markdown("### 🌍 Language / Langue / Kan")
lang = st.sidebar.selectbox("", LANG_OPTIONS, index=0)

def L(key):
    return labels.get(lang, labels["English"]).get(key, key)

st.title("🚕 Mali Ride – Passenger Demo")
st.caption("Request a ride, apply promos, and manage scheduled trips for the investor demo.")

# ----------------------------
# LOAD DRIVERS
# ----------------------------
drivers = load_drivers_from_db()
if not drivers:
    st.info("No drivers found yet. Add some drivers in the Driver App or seed the drivers.json file.")

# ----------------------------
# PICKUP / DROPOFF
# ----------------------------
col_loc1, col_loc2 = st.columns(2)
with col_loc1:
    st.subheader("Pickup location")
    pickup_city = st.selectbox("City", MALI_CITIES, index=0)
    pickup_neigh = st.selectbox("Neighborhood (optional)", [""] + BKO_NEIGHBORHOODS)
    pickup_lat = st.number_input("Pickup latitude", value=12.6392)
    pickup_lon = st.number_input("Pickup longitude", value=-8.0029)
with col_loc2:
    st.subheader("Dropoff location")
    drop_city = st.selectbox("Dropoff city", MALI_CITIES, index=0, key="drop_city")
    drop_neigh = st.selectbox("Dropoff neighborhood (optional)", [""] + BKO_NEIGHBORHOODS, key="drop_neigh")
    drop_lat = st.number_input("Dropoff latitude", value=12.6400)
    drop_lon = st.number_input("Dropoff longitude", value=-8.0100)

# ----------------------------
# SCHEDULING
# ----------------------------
st.markdown("### 🕒 Trip time")

default_date = date.today()
default_time = datetime.utcnow().time().replace(second=0, microsecond=0)

trip_date = st.date_input("Trip date", value=default_date)
trip_time = st.time_input("Trip time", value=default_time)
scheduled_for = datetime.combine(trip_date, trip_time)

st.info(
    "❗ **Cancellation policy**:\n\n"
    "- Free cancellation only if **4 hours or more** before the scheduled time.\n"
    "- If you cancel within 4 hours of the trip, you pay **75% of the fare** as a fee.\n"
)

# ----------------------------
# DRIVER SELECTION
# ----------------------------
st.markdown("### 🎯 Choose a driver")
if drivers:
    df_drivers = pd.DataFrame(drivers)
    display_cols = [c for c in ["username", "first_name", "last_name", "city", "transport_type", "rating"] if c in df_drivers.columns]
    st.dataframe(df_drivers[display_cols])

    chosen_username = st.selectbox(
        "Preferred driver (for demo)",
        options=df_drivers["username"].tolist()
    )
else:
    chosen_username = None

# ----------------------------
# PRICING & PROMOS
# ----------------------------
st.markdown("### 💰 Pricing & promotions")

distance_miles = haversine_miles(pickup_lat, pickup_lon, drop_lat, drop_lon)
base_fare = compute_fare(distance_miles)

promo_code = st.text_input("Promo code (optional)")
referral_code = st.text_input("Referral code (optional)")

fare_after_promo, discount = apply_promo(promo_code, base_fare)

st.write(f"**Distance estimate:** {distance_miles:.2f} miles")
st.write(f"**Base fare:** {base_fare:,.0f} XOF")
st.write(f"**Discount:** {discount:,.0f} XOF")
st.write(f"**Final price:** {fare_after_promo:,.0f} XOF")

# ----------------------------
# CONFIRM RIDE
# ----------------------------
if st.button("Confirm ride"):
    if not chosen_username:
        st.error("No driver selected.")
    else:
        # Compute weekly trips for dynamic commission
        trips_history = load_trips_from_db()
        df_trips_hist = pd.DataFrame(trips_history)
        weekly_trips = 0
        from core.shared import get_commission_pct
        if not df_trips_hist.empty and "created_at" in df_trips_hist.columns and "driver_username" in df_trips_hist.columns:
            df_trips_hist["created_at"] = pd.to_datetime(df_trips_hist["created_at"], errors="coerce")
            now = pd.Timestamp.utcnow()
            last_7 = now - pd.Timedelta(days=7)
            mask = (
                (df_trips_hist["driver_username"] == chosen_username)
                & (df_trips_hist["created_at"] >= last_7)
                & (df_trips_hist["created_at"] <= now)
            )
            weekly_trips = int(mask.sum())

        commission_pct = get_commission_pct(weekly_trips + 1)
        platform_commission = round(fare_after_promo * commission_pct / 100)
        driver_earnings = fare_after_promo - platform_commission

        trip = {
            "driver_username": chosen_username,
            "pickup_lat": pickup_lat,
            "pickup_lon": pickup_lon,
            "drop_lat": drop_lat,
            "drop_lon": drop_lon,
            "distance_miles": distance_miles,
            "price_xof": fare_after_promo,
            "price_before_discount_xof": base_fare,
            "discount_xof": discount,
            "promo_code": promo_code.upper() if promo_code else "",
            "referral_code": referral_code.upper() if referral_code else "",
            "platform_commission_xof": platform_commission,
            "driver_earnings_xof": driver_earnings,
            "platform_pct": commission_pct,
            "driver_pct": 100 - commission_pct,
            "city": pickup_city,
            "routing_provider": "demo_haversine",
            "created_at": pd.Timestamp.utcnow().isoformat(),
            "route_summary": f"{pickup_city} {pickup_neigh or ''} → {drop_city} {drop_neigh or ''}",
            "client_app": "passenger_mobile_demo",
            "status": "scheduled",
            "scheduled_for": scheduled_for.isoformat(),
        }
        save_trip_to_db(trip)
        st.success("Ride confirmed and stored. This will now appear in the admin & investor dashboards.")

# ----------------------------
# MANAGE SCHEDULED TRIPS (DEMO VIEW)
# ----------------------------
st.markdown("---")
st.subheader("🗓️ My scheduled trips (demo view)")

all_trips = load_trips_from_db()
df_my = pd.DataFrame(all_trips)

if not df_my.empty:
    if "status" not in df_my.columns:
        df_my["status"] = "scheduled"

    df_sched = df_my[df_my["status"].isin(["scheduled", "cancelled_by_passenger", "cancelled_by_driver"])].copy()
    if not df_sched.empty:
        st.dataframe(df_sched)

        trip_indices = df_sched.index.tolist()
        chosen_idx = st.selectbox("Select a scheduled trip to cancel", trip_indices)

        if st.button("Cancel selected trip"):
            now_utc = datetime.utcnow()
            trips_list = all_trips
            trip = trips_list[chosen_idx]

            if passenger_can_cancel(trip, now_utc=now_utc):
                trip["status"] = "cancelled_by_passenger"
                trip["cancellation_reason"] = "free_passenger_cancel"
                trip["cancellation_fee_xof"] = 0
                trip["platform_commission_xof"] = 0
                trip["driver_earnings_xof"] = 0
                st.success("Trip cancelled with no fee (4+ hours in advance).")
            else:
                trip = apply_passenger_cancellation(trip)
                st.warning(
                    f"Trip cancelled less than 4 hours before. "
                    f"A fee of {trip['cancellation_fee_xof']:,.0f} XOF applies."
                )

            trips_list[chosen_idx] = trip
            _write_json(TRIPS_PATH, trips_list)
    else:
        st.info("No scheduled trips.")
else:
    st.info("No trips found.")

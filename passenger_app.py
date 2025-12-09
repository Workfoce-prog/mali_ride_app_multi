
import streamlit as st
import pandas as pd
from datetime import datetime

from core.shared import (
    LANG_OPTIONS,
    labels,
    load_drivers_from_db,
    save_trip_to_db,
    load_trips_from_db,
    haversine_miles,
    compute_fare,
    apply_promo,
    get_commission_pct,
    MALI_CITIES,
    BKO_NEIGHBORHOODS,
)

st.set_page_config(page_title="Mali Ride – Passenger App", layout="wide")

st.sidebar.markdown("### 🌍 Language / Langue / Kan")
lang = st.sidebar.selectbox("", LANG_OPTIONS, index=0)

def L(key):
    return labels.get(lang, labels["English"]).get(key, key)

st.title("🚕 Mali Ride – Passenger Demo")
st.caption("Request a ride, see pricing, and trigger trips for the investor dashboards.")

drivers = load_drivers_from_db()
if not drivers:
    st.info("No drivers found yet. Add some drivers in the Driver App or seed the drivers.json file.")

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

st.markdown("### 🎯 Choose a driver")
if drivers:
    df_drivers = pd.DataFrame(drivers)
    st.dataframe(df_drivers[["username", "first_name", "last_name", "city", "transport_type"]])

    chosen_username = st.selectbox(
        "Preferred driver (for demo)",
        options=df_drivers["username"].tolist()
    )
else:
    chosen_username = None

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

if st.button("Confirm ride"):
    if not chosen_username:
        st.error("No driver selected.")
    else:
        # Compute weekly trips for dynamic commission
        trips_history = load_trips_from_db()
        df_trips = pd.DataFrame(trips_history)
        weekly_trips = 0
        if not df_trips.empty and "created_at" in df_trips.columns and "driver_username" in df_trips.columns:
            df_trips["created_at"] = pd.to_datetime(df_trips["created_at"], errors="coerce")
            now = pd.Timestamp.utcnow()
            last_7 = now - pd.Timedelta(days=7)
            mask = (
                (df_trips["driver_username"] == chosen_username)
                & (df_trips["created_at"] >= last_7)
                & (df_trips["created_at"] <= now)
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
        }
        save_trip_to_db(trip)
        st.success("Ride confirmed and stored. This will now appear in the admin & investor dashboards.")

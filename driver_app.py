
import streamlit as st
import pandas as pd
from datetime import datetime

from core.shared import (
    LANG_OPTIONS,
    labels,
    load_drivers_from_db,
    save_driver_to_db,
    update_driver_in_db,
    load_trips_from_db,
    get_commission_pct,
    MALI_CITIES,
)

st.set_page_config(page_title="Mali Ride – Driver App", layout="wide")

st.sidebar.markdown("### 🌍 Language / Langue / Kan")
lang = st.sidebar.selectbox("", LANG_OPTIONS, index=0)

def L(key):
    return labels.get(lang, labels["English"]).get(key, key)

st.title("🚖 Mali Ride – Driver Demo")
st.caption("Register drivers and view their earnings based on recent trips.")

drivers = load_drivers_from_db()
if "logged_driver" not in st.session_state:
    st.session_state["logged_driver"] = None

st.markdown("## 👤 Register a new driver")
with st.form("register_driver"):
    username = st.text_input("Username (unique ID)")
    first_name = st.text_input("First name")
    last_name = st.text_input("Last name")
    age = st.number_input("Age", min_value=18, max_value=80, value=30)
    city = st.selectbox("City", MALI_CITIES)
    transport_type = st.selectbox("Transport type", ["Moto", "Car", "Taxi", "Tricycle"])
    submitted = st.form_submit_button("Add driver")
    if submitted:
        if not username:
            st.error("Username is required.")
        else:
            driver = {
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "age": age,
                "city": city,
                "transport_type": transport_type,
                "status": "Available",
            }
            save_driver_to_db(driver)
            st.success("Driver added.")
            drivers = load_drivers_from_db()

st.markdown("## 🚕 Existing drivers")
if drivers:
    df = pd.DataFrame(drivers)
    st.dataframe(df)
    login_username = st.selectbox("Log in as driver", options=df["username"].tolist())
    if st.button("Log in as this driver"):
        st.session_state["logged_driver"] = login_username
else:
    st.info("No drivers registered yet.")

if st.session_state["logged_driver"]:
    username_logged = st.session_state["logged_driver"]
    st.markdown(f"### Dashboard for driver: `{username_logged}`")

    # Earnings & trips tracker (last 7 days)
    trips_history = load_trips_from_db()
    weekly_trips = 0
    total_driver_earnings = 0
    total_platform_commission = 0

    try:
        df_trips = pd.DataFrame(trips_history)
        if not df_trips.empty and "created_at" in df_trips.columns and "driver_username" in df_trips.columns:
            df_trips["created_at"] = pd.to_datetime(df_trips["created_at"], errors="coerce")
            now = pd.Timestamp.utcnow()
            last_7 = now - pd.Timedelta(days=7)
            mask = (
                (df_trips["driver_username"] == username_logged)
                & (df_trips["created_at"] >= last_7)
                & (df_trips["created_at"] <= now)
            )
            df_week = df_trips[mask].copy()
            weekly_trips = len(df_week)
            if "driver_earnings_xof" in df_week.columns:
                total_driver_earnings = float(df_week["driver_earnings_xof"].sum())
            if "platform_commission_xof" in df_week.columns:
                total_platform_commission = float(df_week["platform_commission_xof"].sum())
    except Exception:
        pass

    current_commission_pct = get_commission_pct(weekly_trips)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Trips (last 7 days)", weekly_trips)
    col_b.metric("Driver earnings (XOF)", f"{total_driver_earnings:,.0f}")
    col_c.metric("Current commission (%)", f"{current_commission_pct}%")

    st.caption("Commission tier is based on trips in the last 7 days (launch promo tiers).")

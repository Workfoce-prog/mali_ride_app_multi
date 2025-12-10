
import streamlit as st
import pandas as pd
from datetime import datetime

import streamlit as st
import pandas as pd
from datetime import datetime

from shared import (
    LANG_OPTIONS,
    labels,
    load_drivers_from_db,
    save_driver_to_db,
    update_driver_in_db,
    load_trips_from_db,
    get_commission_pct,
    apply_driver_cancellation,
    penalize_driver_rating,
    TRIPS_PATH,
    _write_json,
    MALI_CITIES,
)

st.set_page_config(page_title="Mali Ride – Driver App", layout="wide")

st.sidebar.markdown("### 🌍 Language / Langue / Kan")
lang = st.sidebar.selectbox("", LANG_OPTIONS, index=0)

def L(key):
    return labels.get(lang, labels.get("English", {})).get(key, key)

st.title("🚖 Mali Ride – Driver Demo")
st.caption("Register drivers and view their earnings, penalties, and ratings based on recent trips.")


def L(key):
    return labels.get(lang, labels["English"]).get(key, key)

st.title("🚖 Mali Ride – Driver Demo")
st.caption("Register drivers and view their earnings, penalties, and ratings based on recent trips.")

drivers = load_drivers_from_db()
if "logged_driver" not in st.session_state:
    st.session_state["logged_driver"] = None

# ----------------------------
# REGISTER NEW DRIVER
# ----------------------------
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
            # initialize rating & cancel_count
            driver = {
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "age": age,
                "city": city,
                "transport_type": transport_type,
                "status": "Available",
                "rating": 5.0,
                "rating_count": 0,
                "cancel_count": 0,
            }
            save_driver_to_db(driver)
            st.success("Driver added.")
            drivers = load_drivers_from_db()

# ----------------------------
# EXISTING DRIVERS
# ----------------------------
st.markdown("## 🚕 Existing drivers")
if drivers:
    df = pd.DataFrame(drivers)
    display_cols = [c for c in ["username", "first_name", "last_name", "city", "transport_type", "rating", "cancel_count"] if c in df.columns]
    st.dataframe(df[display_cols])

    login_username = st.selectbox("Log in as driver", options=df["username"].tolist())
    if st.button("Log in as this driver"):
        st.session_state["logged_driver"] = login_username
else:
    st.info("No drivers registered yet.")

# ----------------------------
# DRIVER DASHBOARD
# ----------------------------
if st.session_state["logged_driver"]:
    username_logged = st.session_state["logged_driver"]
    st.markdown(f"### Dashboard for driver: `{username_logged}`")

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

    current_driver = next((d for d in drivers if d.get("username") == username_logged), None)
    rating_val = current_driver.get("rating", 5.0) if current_driver else 5.0
    cancel_count = current_driver.get("cancel_count", 0) if current_driver else 0

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Trips (last 7 days)", weekly_trips)
    col_b.metric("Driver earnings (XOF)", f"{total_driver_earnings:,.0f}")
    col_c.metric("Current commission (%)", f"{current_commission_pct}%")
    col_d.metric("Rating", f"{rating_val:.2f}")
    st.caption(f"Driver cancellations (lifetime): {cancel_count}")

    st.caption("Commission tier is based on trips in the last 7 days (launch promo tiers).")

    # ----------------------------
    # SCHEDULED TRIPS VIEW + CANCELLATION
    # ----------------------------
    st.markdown("---")
    st.subheader("🗓️ My scheduled trips")

    all_trips = load_trips_from_db()
    df_all = pd.DataFrame(all_trips)

    if not df_all.empty:
        if "status" not in df_all.columns:
            df_all["status"] = "scheduled"

        df_my_sched = df_all[
            (df_all["driver_username"] == username_logged)
            & (df_all["status"].isin(["scheduled", "cancelled_by_driver"]))
        ].copy()

        if not df_my_sched.empty:
            st.dataframe(df_my_sched)

            trip_indices = df_my_sched.index.tolist()
            chosen_idx = st.selectbox("Select a scheduled trip to cancel", trip_indices, key="driver_cancel_select")

            if st.button("Cancel selected scheduled trip", key="driver_cancel_button"):
                trips_list = all_trips
                trip = trips_list[chosen_idx]

                trip = apply_driver_cancellation(trip)

                # penalize driver rating
                drivers_list = load_drivers_from_db()
                for d in drivers_list:
                    if d.get("username") == username_logged:
                        penalized = penalize_driver_rating(d)
                        update_driver_in_db(username_logged, penalized)
                        break

                trips_list[chosen_idx] = trip
                _write_json(TRIPS_PATH, trips_list)

                st.error(
                    f"Trip cancelled by driver. A penalty of {trip['cancellation_fee_xof']:,.0f} XOF "
                    f"is charged to the company and your rating has been reduced."
                )
        else:
            st.info("No scheduled trips for this driver.")
    else:
        st.info("No trips found.")

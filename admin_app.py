
import streamlit as st
import pandas as pd
from datetime import date

from core.shared import (
    LANG_OPTIONS,
    labels,
    load_drivers_from_db,
    load_trips_from_db,
    ADMIN_CODE,
)

st.set_page_config(page_title="Mali Ride – Admin Dashboard", layout="wide")

# ----------------------------
# LANGUAGE
# ----------------------------
st.sidebar.markdown("### 🌍 Language / Langue / Kan")
lang = st.sidebar.selectbox("", LANG_OPTIONS, index=0)

def L(key):
    return labels.get(lang, labels["English"]).get(key, key)

st.title(L("title_admin"))
st.caption(L("subtitle"))

# ----------------------------
# SIDEBAR – ADMIN (FULLY UNLOCKED FOR REAL-TIME DEMO)
# ----------------------------
st.sidebar.markdown("### 🔑 " + L("admin_auth"))

st.sidebar.success(
    "✅ Admin dashboard is currently **UNLOCKED** for real-time demo.\n"
    "Anyone with the link can view all metrics and app analytics."
)

# Always treat admin as authenticated in this demo
st.session_state["admin_ok"] = True

# ----------------------------
# LOAD DATA
# ----------------------------
drivers = load_drivers_from_db()
trips = load_trips_from_db()

df_trips = pd.DataFrame(trips) if trips else pd.DataFrame()
if not df_trips.empty and "created_at" in df_trips.columns:
    df_trips["created_at"] = pd.to_datetime(df_trips["created_at"], errors="coerce")
    df_trips["date_only"] = df_trips["created_at"].dt.date

# ----------------------------
# FILTERS
# ----------------------------
if not df_trips.empty:
    st.markdown("### 🔎 Filters (trips)")

    colf1, colf2, colf3 = st.columns(3)

    with colf1:
        if "city" in df_trips.columns:
            city_options = sorted([c for c in df_trips["city"].dropna().unique()])
        else:
            city_options = []
        city_filter = st.multiselect(
            "City (from trips)",
            city_options,
            default=city_options if city_options else None,
        )

    with colf2:
        if "created_at" in df_trips.columns and df_trips["created_at"].notna().any():
            dates = df_trips["created_at"].dropna()
            min_date = dates.min().date()
            max_date = dates.max().date()
        else:
            today = date.today()
            min_date = max_date = today

        start_date, end_date = st.date_input(
            "Date range (created_at)",
            value=(min_date, max_date),
        )

    with colf3:
        if "routing_provider" in df_trips.columns:
            provider_options = sorted([p for p in df_trips["routing_provider"].dropna().unique()])
        else:
            provider_options = []
        provider_filter = st.multiselect(
            "Routing provider",
            provider_options,
            default=provider_options if provider_options else None,
        )

    df_trips_filtered = df_trips.copy()

    if city_options and city_filter:
        df_trips_filtered = df_trips_filtered[df_trips_filtered["city"].isin(city_filter)]

    if "created_at" in df_trips_filtered.columns and df_trips_filtered["created_at"].notna().any():
        df_trips_filtered = df_trips_filtered[
            (df_trips_filtered["created_at"].dt.date >= start_date)
            & (df_trips_filtered["created_at"].dt.date <= end_date)
        ]

    if provider_options and provider_filter and "routing_provider" in df_trips_filtered.columns:
        df_trips_filtered = df_trips_filtered[df_trips_filtered["routing_provider"].isin(provider_filter)]
else:
    df_trips_filtered = df_trips

# ----------------------------
# TOP-LEVEL METRICS
# ----------------------------
st.header("📊 Platform metrics")

col_a, col_b, col_c, col_d = st.columns(4)
col_e, col_f, col_g, col_h = st.columns(4)

status_options = L("status_options")
status_available = status_options[0]
status_busy = status_options[1]
status_offline = status_options[2] if len(status_options) > 2 else "Offline"

n_available = sum(1 for d in drivers if d.get("status") == status_available)
n_busy = sum(1 for d in drivers if d.get("status") == status_busy)
n_offline = sum(1 for d in drivers if d.get("status") == status_offline)

if not df_trips_filtered.empty:
    total_gross = float(df_trips_filtered.get("price_xof", pd.Series([0]*len(df_trips_filtered))).sum())
    total_platform = float(df_trips_filtered.get("platform_commission_xof", pd.Series([0]*len(df_trips_filtered))).sum())
    total_driver = float(df_trips_filtered.get("driver_earnings_xof", pd.Series([0]*len(df_trips_filtered))).sum())
    n_trips = len(df_trips_filtered)
else:
    total_gross = total_platform = total_driver = 0.0
    n_trips = 0

with col_a:
    st.metric(L("metric_drivers"), len(drivers))
with col_b:
    st.metric(L("metric_available"), n_available)
with col_c:
    st.metric(L("metric_busy"), n_busy)
with col_d:
    st.metric(L("metric_offline"), n_offline)
with col_e:
    st.metric(L("metric_trips") + " (filtered)", n_trips)
with col_f:
    st.metric(L("metric_revenue") + " (filtered)", f"{total_gross:,.0f}")
with col_g:
    st.metric(L("metric_platform_revenue") + " (filtered)", f"{total_platform:,.0f}")
with col_h:
    st.metric(L("metric_driver_earnings") + " (filtered)", f"{total_driver:,.0f}")

# ----------------------------
# APP MODULES OVERVIEW TABS
# ----------------------------
st.markdown("---")
st.subheader("📱 App modules overview (Driver, Passenger, Promotions, Mobile)")

tab_driver, tab_passenger, tab_promos, tab_mobile = st.tabs(
    ["🚖 Driver app", "🚕 Passenger app", "💸 Promotions", "📱 Mobile usage"]
)

# ---------- DRIVER APP VIEW ----------
with tab_driver:
    st.markdown("### 🚖 Driver app – supply, earnings & ratings")

    if drivers:
        df_drivers = pd.DataFrame(drivers)
        pref_cols = ["username", "first_name", "last_name", "city", "transport_type", "rating", "cancel_count"]
        cols = [c for c in pref_cols if c in df_drivers.columns] + [c for c in df_drivers.columns if c not in pref_cols]
        st.markdown("**Registered drivers (from Driver app)**")
        st.dataframe(df_drivers[cols])

        if not df_trips_filtered.empty and "driver_username" in df_trips_filtered.columns:
            df_d = df_trips_filtered.copy()
            agg = df_d.groupby("driver_username").agg(
                trips_count=("price_xof", "count"),
                total_revenue_xof=("price_xof", "sum"),
                driver_earnings_xof=("driver_earnings_xof", "sum")
                if "driver_earnings_xof" in df_d.columns
                else ("price_xof", "sum"),
            ).reset_index()

            if "username" in df_drivers.columns:
                join_cols = ["username", "first_name", "last_name", "city", "transport_type", "rating", "cancel_count"]
                join_cols = [c for c in join_cols if c in df_drivers.columns]
                df_info = df_drivers[join_cols].copy()
                agg = agg.merge(df_info, how="left", left_on="driver_username", right_on="username")

                agg["driver_name"] = agg.apply(
                    lambda r: f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                    if (pd.notna(r.get('first_name', '')) or pd.notna(r.get('last_name', '')))
                    else r["driver_username"],
                    axis=1
                )
            else:
                agg["driver_name"] = agg["driver_username"]

            agg = agg.sort_values("driver_earnings_xof", ascending=False)

            st.markdown("**Top drivers by earnings (filtered)**")
            top_n = st.slider("Top N drivers (Driver app view)", 3, 50, 10, key="top_driver_tab")
            top_drivers = agg.head(top_n)
            st.dataframe(top_drivers)

            st.markdown("**Earnings by driver (XOF)**")
            st.bar_chart(top_drivers.set_index("driver_name")["driver_earnings_xof"])
        else:
            st.info("No trips for drivers in the current filter range.")
    else:
        st.info("No drivers registered yet – use the Driver app to add some.")

# ---------- PASSENGER APP VIEW ----------
with tab_passenger:
    st.markdown("### 🚕 Passenger app – demand & trips view")

    if not df_trips_filtered.empty:
        if "date_only" in df_trips_filtered.columns:
            trips_by_day = df_trips_filtered.groupby("date_only").agg(
                trips_count=("price_xof", "count"),
                revenue_xof=("price_xof", "sum"),
            ).reset_index()

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown("**Trips per day (Passenger app)**")
                st.line_chart(trips_by_day.set_index("date_only")["trips_count"])
            with col_p2:
                st.markdown("**Revenue per day (XOF)**")
                st.line_chart(trips_by_day.set_index("date_only")["revenue_xof"])

        if "city" in df_trips_filtered.columns:
            df_city = df_trips_filtered.dropna(subset=["city"]).copy()
            city_group = df_city.groupby("city").agg(
                trips_count=("price_xof", "count"),
                avg_fare_xof=("price_xof", "mean"),
                total_revenue_xof=("price_xof", "sum"),
            ).reset_index()
            city_group["avg_fare_xof"] = city_group["avg_fare_xof"].round(0)

            st.markdown("**Trips by city (Passenger demand)**")
            st.dataframe(city_group)
            st.bar_chart(city_group.set_index("city")["trips_count"])

        if "distance_miles" in df_trips_filtered.columns:
            st.markdown("**Distance vs fare (per trip)**")
            dist_fare = df_trips_filtered[["distance_miles", "price_xof"]].dropna()
            if not dist_fare.empty:
                st.scatter_chart(dist_fare, x="distance_miles", y="price_xof")
            else:
                st.info("No valid distance/fare data to plot.")
    else:
        st.info("No passenger trips in the current filter range.")

# ---------- PROMOTIONS & REFERRALS ----------
with tab_promos:
    st.markdown("### 💸 Promotions & referrals – campaign performance")

    if not df_trips_filtered.empty:
        if "promo_code" in df_trips_filtered.columns:
            df_promo = df_trips_filtered.copy()
            df_promo = df_promo[df_promo["promo_code"].notna() & (df_promo["promo_code"] != "")]
            if not df_promo.empty:
                promo_group = df_promo.groupby("promo_code").agg(
                    trips_count=("price_xof", "count"),
                    total_gross_before_xof=("price_before_discount_xof", "sum")
                    if "price_before_discount_xof" in df_promo.columns
                    else ("price_xof", "sum"),
                    total_discount_xof=("discount_xof", "sum")
                    if "discount_xof" in df_promo.columns
                    else ("price_xof", "sum"),
                    total_net_xof=("price_xof", "sum"),
                ).reset_index()
                promo_group["avg_discount_per_trip_xof"] = (
                    promo_group["total_discount_xof"] / promo_group["trips_count"]
                ).round(2)

                st.markdown("**Promo performance (from Passenger app)**")
                st.dataframe(promo_group)

                col_pr1, col_pr2 = st.columns(2)
                with col_pr1:
                    st.markdown("Trips by promo code")
                    st.bar_chart(promo_group.set_index("promo_code")["trips_count"])
                with col_pr2:
                    st.markdown("Total discount by promo code (XOF)")
                    st.bar_chart(promo_group.set_index("promo_code")["total_discount_xof"])
            else:
                st.info("No promo codes used in the current filter range.")
        else:
            st.info("Promo code information not available in trips.")

        st.markdown("---")

        if "referral_code" in df_trips_filtered.columns:
            df_ref = df_trips_filtered.copy()
            df_ref = df_ref[df_ref["referral_code"].notna() & (df_ref["referral_code"] != "")]
            if not df_ref.empty:
                ref_group = df_ref.groupby("referral_code").agg(
                    trips_count=("price_xof", "count"),
                    total_revenue_xof=("price_xof", "sum"),
                    avg_fare_xof=("price_xof", "mean"),
                ).reset_index()
                ref_group["avg_fare_xof"] = ref_group["avg_fare_xof"].round(0)

                st.markdown("**Referral performance**")
                st.dataframe(ref_group)
                st.markdown("Trips by referral code")
                st.bar_chart(ref_group.set_index("referral_code")["trips_count"])
            else:
                st.info("No referral codes used in the current filter range.")
        else:
            st.info("Referral code information not available in trips.")
    else:
        st.info("No trips available for promotion/referral analysis.")

# ---------- MOBILE USAGE ----------
with tab_mobile:
    st.markdown("### 📱 Mobile usage – client apps overview")

    if not df_trips_filtered.empty and "client_app" in df_trips_filtered.columns:
        df_ch = df_trips_filtered.dropna(subset=["client_app"]).copy()
        if not df_ch.empty:
            ch_group = df_ch.groupby("client_app").size().reset_index(name="trips_count")
            st.markdown("**Trips by platform (Passenger / Driver / Web)**")
            st.dataframe(ch_group)
            st.bar_chart(ch_group.set_index("client_app")["trips_count"])
        else:
            st.info("No client_app data available in filtered trips.")
    else:
        st.info(
            "No client_app field found – add `client_app` when saving trips "
            "(e.g., 'passenger_mobile', 'driver_mobile', 'web_admin') to see real split here."
        )

# ----------------------------
# RAW TABLES AT BOTTOM
# ----------------------------
st.markdown("---")
st.subheader(L("drivers_table_header"))
if drivers:
    df_dr = pd.DataFrame(drivers)
    pref_cols = ["username", "first_name", "last_name", "city", "transport_type", "rating", "cancel_count"]
    cols = [c for c in pref_cols if c in df_dr.columns] + [c for c in df_dr.columns if c not in pref_cols]
    st.dataframe(df_dr[cols])
else:
    st.info(L("no_drivers"))

st.markdown("---")
st.subheader(L("trips_table_header") + " (filtered)")
if not df_trips_filtered.empty:
    st.dataframe(df_trips_filtered)
else:
    st.info("No trips (for current filters).")


import streamlit as st
import pandas as pd

from core.shared import (
    load_drivers_from_db,
    load_trips_from_db,
)

st.set_page_config(page_title="Mali Ride – Investor Overview", layout="wide")

st.title("📈 Mali Ride – Investor Dashboard")
st.caption(
    "High-level KPIs across drivers, passengers, promotions, cancellations, and mobile usage.\n"
    "This view is designed for investor demos and strategic partners."
)

drivers = load_drivers_from_db()
trips = load_trips_from_db()
df_trips = pd.DataFrame(trips) if trips else pd.DataFrame()

if not df_trips.empty and "created_at" in df_trips.columns:
    df_trips["created_at"] = pd.to_datetime(df_trips["created_at"], errors="coerce")
    df_trips["date_only"] = df_trips["created_at"].dt.date

st.markdown("## 📊 Key KPIs")

col1, col2, col3, col4 = st.columns(4)

n_drivers = len(drivers)
n_trips = len(df_trips) if not df_trips.empty else 0
total_gmv = float(df_trips.get("price_xof", pd.Series([0]*len(df_trips))).sum()) if not df_trips.empty else 0.0
total_platform = float(df_trips.get("platform_commission_xof", pd.Series([0]*len(df_trips))).sum()) if not df_trips.empty else 0.0

with col1:
    st.metric("Active drivers (registered)", n_drivers)
with col2:
    st.metric("Total trips (lifetime)", n_trips)
with col3:
    st.metric("Gross fares (XOF)", f"{total_gmv:,.0f}")
with col4:
    st.metric("Platform revenue (XOF)", f"{total_platform:,.0f}")

st.markdown("---")

tab_overview, tab_drivers, tab_trips, tab_promos, tab_mobile = st.tabs(
    ["Overview", "Drivers", "Trips & cancellations", "Promos & referrals", "Mobile usage"]
)

# ----------------------------
# OVERVIEW TAB
# ----------------------------
with tab_overview:
    st.markdown("### 📅 Volume over time")

    if not df_trips.empty and "date_only" in df_trips.columns:
        daily = df_trips.groupby("date_only").agg(
            trips_count=("price_xof", "count"),
            revenue_xof=("price_xof", "sum"),
            platform_xof=("platform_commission_xof", "sum"),
        ).reset_index()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Trips per day**")
            st.line_chart(daily.set_index("date_only")["trips_count"])
        with c2:
            st.markdown("**Gross fares per day (XOF)**")
            st.line_chart(daily.set_index("date_only")["revenue_xof"])

        st.markdown("### 🌍 City mix")
        if "city" in df_trips.columns:
            city_group = df_trips.dropna(subset=["city"]).groupby("city").size().reset_index(name="trips_count")
            st.dataframe(city_group)
            st.bar_chart(city_group.set_index("city")["trips_count"])
    else:
        st.info("No trips yet – create some in the Passenger app to populate this view.")

# ----------------------------
# DRIVERS TAB
# ----------------------------
with tab_drivers:
    st.markdown("### 🚖 Driver performance & ratings")

    if drivers:
        df_dr = pd.DataFrame(drivers)
        pref = ["username", "first_name", "last_name", "city", "transport_type", "rating", "cancel_count"]
        cols = [c for c in pref if c in df_dr.columns] + [c for c in df_dr.columns if c not in pref]
        st.dataframe(df_dr[cols])
    else:
        st.info("No drivers registered.")

    if not df_trips.empty and "driver_username" in df_trips.columns:
        df_d = df_trips.copy()
        agg = df_d.groupby("driver_username").agg(
            trips_count=("price_xof", "count"),
            total_revenue_xof=("price_xof", "sum"),
            driver_earnings_xof=("driver_earnings_xof", "sum")
            if "driver_earnings_xof" in df_d.columns
            else ("price_xof", "sum"),
        ).reset_index()

        if drivers:
            df_dr = pd.DataFrame(drivers)
            join_cols = ["username", "first_name", "last_name", "city", "transport_type", "rating", "cancel_count"]
            join_cols = [c for c in join_cols if c in df_dr.columns]
            df_info = df_dr[join_cols].copy()
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

        st.markdown("**Top drivers by earnings**")
        top_n = st.slider("Top N drivers", 3, 50, 10, key="inv_top_driver")
        top_drivers = agg.head(top_n)
        st.dataframe(top_drivers)

        st.markdown("**Revenue by driver (XOF)**")
        st.bar_chart(top_drivers.set_index("driver_name")["driver_earnings_xof"])
    else:
        st.info("No driver-level trips yet.")

# ----------------------------
# TRIPS & CANCELLATIONS TAB
# ----------------------------
with tab_trips:
    st.markdown("### 🚕 Trip mix & cancellation behavior")

    if not df_trips.empty:
        st.markdown("**Trips snapshot**")
        st.dataframe(df_trips)

        if "status" in df_trips.columns:
            cancel_stats = df_trips["status"].value_counts().reset_index()
            cancel_stats.columns = ["status", "count"]

            st.markdown("**Trips by status (including cancellations)**")
            st.dataframe(cancel_stats)
            st.bar_chart(cancel_stats.set_index("status")["count"])

        if "cancellation_fee_xof" in df_trips.columns:
            total_cancel_fees = float(df_trips["cancellation_fee_xof"].fillna(0).sum())
            st.metric("Total cancellation fees (XOF)", f"{total_cancel_fees:,.0f}")
    else:
        st.info("No trips yet.")

# ----------------------------
# PROMOS & REFERRALS TAB
# ----------------------------
with tab_promos:
    st.markdown("### 💸 Promotions & referral engine")

    if not df_trips.empty:
        if "promo_code" in df_trips.columns:
            df_promo = df_trips.copy()
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

                st.markdown("**Promo performance**")
                st.dataframe(promo_group)

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("Trips by promo code")
                    st.bar_chart(promo_group.set_index("promo_code")["trips_count"])
                with c2:
                    st.markdown("Total discount by promo code (XOF)")
                    st.bar_chart(promo_group.set_index("promo_code")["total_discount_xof"])
            else:
                st.info("No promo codes used yet.")
        else:
            st.info("Promo code field not available in trips.")

        st.markdown("---")

        if "referral_code" in df_trips.columns:
            df_ref = df_trips.copy()
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
                st.bar_chart(ref_group.set_index("referral_code")["trips_count"])
            else:
                st.info("No referral codes used yet.")
        else:
            st.info("Referral code field not available in trips.")
    else:
        st.info("No trips yet.")

# ----------------------------
# MOBILE USAGE TAB
# ----------------------------
with tab_mobile:
    st.markdown("### 📱 Mobile vs web usage")

    if not df_trips.empty and "client_app" in df_trips.columns:
        df_ch = df_trips.dropna(subset=["client_app"]).copy()
        if not df_ch.empty:
            ch_group = df_ch.groupby("client_app").size().reset_index(name="trips_count")
            st.dataframe(ch_group)
            st.bar_chart(ch_group.set_index("client_app")["trips_count"])
        else:
            st.info("No client_app data available yet.")
    else:
        st.info(
            "No client_app field found – the Passenger app saves `client_app='passenger_mobile_demo'`. "
            "You can extend this to other clients (driver mobile, web, etc.)."
        )


import streamlit as st
import pandas as pd
from datetime import date

from core.shared import (
    LANG_OPTIONS,
    labels,
    load_drivers_from_db,
    load_trips_from_db,
)

st.set_page_config(
    page_title="Mali Ride – Investor Demo Dashboard",
    layout="wide"
)

st.sidebar.markdown("### 🌍 Language / Langue / Kan")
lang = st.sidebar.selectbox("", LANG_OPTIONS, index=0)

def L(key: str) -> str:
    return labels.get(lang, labels["English"]).get(key, key)

st.title("Mali Ride – Investor Overview")
st.caption("Unified demo of drivers, passenger trips, promotions, and mobile usage for investors.")

st.markdown(
    """
    This dashboard provides a **high-level, investor-facing view** of:
    - 🚕 Driver supply & earnings  
    - 👥 Passenger demand & trips  
    - 💸 Promotions & referral performance  
    - 📱 Mobile vs. web usage (where available)
    """
)

drivers = load_drivers_from_db() or []
trips = load_trips_from_db() or []

df_drivers = pd.DataFrame(drivers) if drivers else pd.DataFrame()
df_trips = pd.DataFrame(trips) if trips else pd.DataFrame()

if not df_trips.empty and "created_at" in df_trips.columns:
    df_trips["created_at"] = pd.to_datetime(df_trips["created_at"], errors="coerce")
    df_trips["date"] = df_trips["created_at"].dt.date

# FILTERS
st.sidebar.markdown("### 🔎 Filters")

if not df_trips.empty and df_trips["date"].notna().any():
    min_date = df_trips["date"].min()
    max_date = df_trips["date"].max()
else:
    today = date.today()
    min_date = max_date = today

start_date, end_date = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
)

if "city" in df_trips.columns:
    city_options = sorted(c for c in df_trips["city"].dropna().unique())
else:
    city_options = []

city_filter = st.sidebar.multiselect(
    "City",
    options=city_options,
    default=city_options if city_options else None,
)

df_trips_f = df_trips.copy()
if not df_trips_f.empty:
    df_trips_f = df_trips_f[
        (df_trips_f["date"] >= start_date) & (df_trips_f["date"] <= end_date)
    ]
    if city_options and city_filter:
        df_trips_f = df_trips_f[df_trips_f["city"].isin(city_filter)]

# KPIs
st.markdown("## 📊 High-level KPIs")

if not df_trips_f.empty:
    total_trips = len(df_trips_f)
    total_gmv = float(df_trips_f.get("price_xof", pd.Series([0]*len(df_trips_f))).sum())
    total_platform_rev = float(df_trips_f.get("platform_commission_xof", pd.Series([0]*len(df_trips_f))).sum())
    total_driver_income = float(df_trips_f.get("driver_earnings_xof", pd.Series([0]*len(df_trips_f))).sum())
    avg_fare = total_gmv / total_trips if total_trips > 0 else 0.0

    n_drivers = df_trips_f["driver_username"].nunique() if "driver_username" in df_trips_f.columns else 0
    n_cities = df_trips_f["city"].nunique() if "city" in df_trips_f.columns else 0

    if "promo_code" in df_trips_f.columns:
        n_promo_trips = df_trips_f["promo_code"].replace("", pd.NA).dropna().shape[0]
    else:
        n_promo_trips = 0
    promo_share = 100 * n_promo_trips / total_trips if total_trips > 0 else 0

    if "referral_code" in df_trips_f.columns:
        n_ref_trips = df_trips_f["referral_code"].replace("", pd.NA).dropna().shape[0]
    else:
        n_ref_trips = 0
    referral_share = 100 * n_ref_trips / total_trips if total_trips > 0 else 0
else:
    total_trips = total_gmv = total_platform_rev = total_driver_income = avg_fare = 0.0
    n_drivers = n_cities = n_promo_trips = promo_share = n_ref_trips = referral_share = 0.0

col1, col2, col3, col4 = st.columns(4)
col5, col6, col7, col8 = st.columns(4)

col1.metric("Total trips (filtered)", total_trips)
col2.metric("GMV – Gross fares (XOF)", f"{total_gmv:,.0f}")
col3.metric("Platform revenue (XOF)", f"{total_platform_rev:,.0f}")
col4.metric("Driver income (XOF)", f"{total_driver_income:,.0f}")

col5.metric("Avg fare per trip (XOF)", f"{avg_fare:,.0f}")
col6.metric("Active drivers", n_drivers)
col7.metric("Active cities", n_cities)
col8.metric("Trips with promo / referral", f"{promo_share+referral_share:.1f}% est.")

st.markdown("---")

tab_overview, tab_drivers, tab_passengers, tab_promos, tab_mobile = st.tabs(
    ["Overview charts", "Drivers", "Passengers & trips", "Promotions & referrals", "Mobile experience"]
)

with tab_overview:
    st.subheader("📈 Growth & revenue view")
    if not df_trips_f.empty:
        trips_by_day = df_trips_f.groupby("date").agg(
            trips_count=("price_xof", "count"),
            revenue_xof=("price_xof", "sum"),
        ).reset_index()

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### Trips per day")
            st.line_chart(trips_by_day.set_index("date")["trips_count"])
        with col_b:
            st.markdown("#### Revenue per day (XOF)")
            st.line_chart(trips_by_day.set_index("date")["revenue_xof"])

        if "platform_commission_xof" in df_trips_f.columns and "driver_earnings_xof" in df_trips_f.columns:
            rev_split = pd.DataFrame(
                {
                    "Platform": [df_trips_f["platform_commission_xof"].sum()],
                    "Drivers": [df_trips_f["driver_earnings_xof"].sum()],
                }
            ).T
            rev_split.columns = ["Revenue_XOF"]
            st.markdown("#### Revenue split (platform vs drivers)")
            st.bar_chart(rev_split)
    else:
        st.info("No trips available for the selected filters.")

with tab_drivers:
    st.subheader("🚕 Driver supply & earnings")
    if not df_trips_f.empty and "driver_username" in df_trips_f.columns:
        df_d = df_trips_f.copy()
        agg = df_d.groupby("driver_username").agg(
            trips_count=("price_xof", "count"),
            total_revenue_xof=("price_xof", "sum"),
            driver_earnings_xof=("driver_earnings_xof", "sum") if "driver_earnings_xof" in df_d.columns else ("price_xof", "sum"),
        ).reset_index()

        if not df_drivers.empty and "username" in df_drivers.columns:
            join_cols = ["username", "first_name", "last_name", "city", "transport_type"]
            join_cols = [c for c in join_cols if c in df_drivers.columns]
            df_info = df_drivers[join_cols].copy()
            agg = agg.merge(df_info, how="left", left_on="driver_username", right_on="username")

            agg["driver_name"] = agg.apply(
                lambda r: f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
                if pd.notna(r.get('first_name', '')) or pd.notna(r.get('last_name', ''))
                else r["driver_username"],
                axis=1
            )
        else:
            agg["driver_name"] = agg["driver_username"]

        agg = agg.sort_values("driver_earnings_xof", ascending=False)
        top_n = st.slider("Top N drivers", 3, 50, 10)
        top_drivers = agg.head(top_n)

        st.markdown("#### Top drivers by earnings")
        st.dataframe(top_drivers)

        st.markdown("#### Earnings by driver (XOF)")
        st.bar_chart(top_drivers.set_index("driver_name")["driver_earnings_xof"])
    else:
        st.info("No driver information in current trip data.")

with tab_passengers:
    st.subheader("👥 Passenger demand & trip patterns")
    if not df_trips_f.empty:
        col_p1, col_p2 = st.columns(2)
        if "city" in df_trips_f.columns:
            df_city = df_trips_f.dropna(subset=["city"]).copy()
            city_group = df_city.groupby("city").agg(
                trips_count=("price_xof", "count"),
                avg_fare_xof=("price_xof", "mean"),
                total_revenue_xof=("price_xof", "sum"),
            ).reset_index()
            city_group["avg_fare_xof"] = city_group["avg_fare_xof"].round(0)

            with col_p1:
                st.markdown("#### Trips by city")
                st.dataframe(city_group)
                st.bar_chart(city_group.set_index("city")["trips_count"])

        if "distance_miles" in df_trips_f.columns:
            with col_p2:
                st.markdown("#### Distance vs fare")
                dist_fare = df_trips_f[["distance_miles", "price_xof"]].dropna()
                if not dist_fare.empty:
                    st.scatter_chart(dist_fare, x="distance_miles", y="price_xof")
                else:
                    st.info("No valid distance/fare data to plot.")
    else:
        st.info("No passenger trip data for selected filters.")

with tab_promos:
    st.subheader("💸 Promotions & referrals")
    if not df_trips_f.empty:
        if "promo_code" in df_trips_f.columns:
            df_promo = df_trips_f.copy()
            df_promo = df_promo[df_promo["promo_code"].notna() & (df_promo["promo_code"] != "")]
            if not df_promo.empty:
                promo_group = df_promo.groupby("promo_code").agg(
                    trips_count=("price_xof", "count"),
                    total_gross_before_xof=("price_before_discount_xof", "sum") if "price_before_discount_xof" in df_promo.columns else ("price_xof", "sum"),
                    total_discount_xof=("discount_xof", "sum") if "discount_xof" in df_promo.columns else ("price_xof", "sum"),
                    total_net_xof=("price_xof", "sum"),
                ).reset_index()
                promo_group["avg_discount_per_trip_xof"] = (
                    promo_group["total_discount_xof"] / promo_group["trips_count"]
                ).round(2)

                st.markdown("#### Promo performance")
                st.dataframe(promo_group)

                col_pr1, col_pr2 = st.columns(2)
                with col_pr1:
                    st.markdown("Trips by promo code")
                    st.bar_chart(promo_group.set_index("promo_code")["trips_count"])
                with col_pr2:
                    st.markdown("Total discount by promo code (XOF)")
                    st.bar_chart(promo_group.set_index("promo_code")["total_discount_xof"])
            else:
                st.info("No promo codes used in the filtered period.")
        else:
            st.info("Promo code information not available.")

        st.markdown("---")

        if "referral_code" in df_trips_f.columns:
            df_ref = df_trips_f.copy()
            df_ref = df_ref[df_ref["referral_code"].notna() & (df_ref["referral_code"] != "")]
            if not df_ref.empty:
                ref_group = df_ref.groupby("referral_code").agg(
                    trips_count=("price_xof", "count"),
                    total_revenue_xof=("price_xof", "sum"),
                    avg_fare_xof=("price_xof", "mean"),
                ).reset_index()
                ref_group["avg_fare_xof"] = ref_group["avg_fare_xof"].round(0)

                st.markdown("#### Referral performance")
                st.dataframe(ref_group)
                st.markdown("Trips by referral code")
                st.bar_chart(ref_group.set_index("referral_code")["trips_count"])
            else:
                st.info("No referral codes used in the filtered period.")
        else:
            st.info("Referral information not available.")
    else:
        st.info("No trips available for promo/referral analysis.")

with tab_mobile:
    st.subheader("📱 Mobile vs web experience")
    if not df_trips_f.empty and "client_app" in df_trips_f.columns:
        df_ch = df_trips_f.dropna(subset=["client_app"]).copy()
        if not df_ch.empty:
            ch_group = df_ch.groupby("client_app").size().reset_index(name="trips_count")
            st.markdown("#### Trips by platform (actual)")
            st.dataframe(ch_group)
            st.bar_chart(ch_group.set_index("client_app")["trips_count"])
        else:
            st.info("No client_app data available in filtered trips.")
    else:
        st.markdown(
            """
            _Client platform tracking not yet fully integrated in the data model._  
            For this investor demo, we show a **realistic simulated split**:
            """
        )
        if total_trips > 0:
            simulated = pd.DataFrame(
                {
                    "platform": ["Passenger mobile app", "Driver mobile app", "Web / admin"],
                    "trips_count": [
                        int(total_trips * 0.65),
                        int(total_trips * 0.25),
                        total_trips - int(total_trips * 0.65) - int(total_trips * 0.25),
                    ],
                }
            )
            st.dataframe(simulated)
            st.bar_chart(simulated.set_index("platform")["trips_count"])
        else:
            st.info("No trips to simulate platform split.")

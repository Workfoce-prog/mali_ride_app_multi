
import streamlit as st
import pandas as pd
from datetime import date

from core.shared import (
    LANG_OPTIONS,
    labels,
    load_drivers_from_db,
    load_trips_from_db,
    ADMIN_CODE,
    save_admin_login_to_db,
    load_admin_logins_from_db,
)

st.set_page_config(page_title="Mali Ride – Admin Dashboard", layout="wide")

# LANGUAGE
st.sidebar.markdown("### 🌍 Language / Langue / Kan")
lang = st.sidebar.selectbox("", LANG_OPTIONS, index=0)

def L(key):
    return labels.get(lang, labels["English"]).get(key, key)

st.title(L("title_admin"))
st.caption(L("subtitle"))

# DEMO BADGE
DEMO_END_DATE = date(2026, 12, 31)
today = date.today()
is_demo_mode = today <= DEMO_END_DATE

if is_demo_mode:
    st.markdown(f"""
    <div style="
        padding: 12px;
        background-color: #ffcc00;
        border-radius: 8px;
        border: 1px solid #e6b800;
        margin-bottom: 15px;
    ">
    <b style="color:#663300; font-size:18px;">⚠️ DEMO MODE ACTIVE</b><br>
    <span style="color:#663300;">
    This admin dashboard is <b>unlocked</b> until <b>{DEMO_END_DATE.isoformat()}</b>.
    Password protection is temporarily disabled for public demo.
    </span>
    </div>
    """, unsafe_allow_html=True)

# SIDEBAR AUTH + LOGGING
st.sidebar.markdown("### 🔑 " + L("admin_auth"))

admin_email = st.sidebar.text_input("Admin email (for audit)", placeholder="you@example.com")
admin_phone = st.sidebar.text_input("Admin phone (optional)", placeholder="+223...")

if "admin_ok" not in st.session_state:
    st.session_state["admin_ok"] = False

def _log_admin_login(mode: str):
    from datetime import datetime
    info = {
        "email": admin_email.strip(),
        "phone": admin_phone.strip(),
        "mode": mode,
        "timestamp_iso": datetime.utcnow().isoformat(),
    }
    save_admin_login_to_db(info)

if is_demo_mode:
    st.sidebar.success(
        f"✅ Demo mode active until {DEMO_END_DATE.isoformat()}. Admin dashboard is unlocked."
    )
    if st.sidebar.button("Log my admin session (demo mode)"):
        if not admin_email.strip():
            st.sidebar.warning("Please enter an email before logging your session.")
        else:
            _log_admin_login("demo")
            st.sidebar.success("Admin session logged.")
    st.session_state["admin_ok"] = True
else:
    st.sidebar.info(
        f"🔒 Demo period ended on {DEMO_END_DATE.isoformat()}. Admin code is now required."
    )
    code_input = st.sidebar.text_input(L("admin_code_label"), type="password", help=L("admin_code_hint"))
    admin_ok = st.sidebar.button("OK")
    if admin_ok:
        if code_input == ADMIN_CODE:
            if not admin_email.strip():
                st.sidebar.warning("Please enter an email before logging in.")
                st.session_state["admin_ok"] = False
            else:
                st.session_state["admin_ok"] = True
                st.sidebar.success("Admin access granted.")
                _log_admin_login("password")
        else:
            st.session_state["admin_ok"] = False
            st.sidebar.error(L("admin_code_wrong"))

if not st.session_state["admin_ok"]:
    st.warning(L("admin_locked"))
    st.stop()

# LOAD DATA
drivers = load_drivers_from_db()
trips = load_trips_from_db()
df_trips = pd.DataFrame(trips) if trips else pd.DataFrame()
if not df_trips.empty and "created_at" in df_trips.columns:
    df_trips["created_at"] = pd.to_datetime(df_trips["created_at"], errors="coerce")

# FILTERS
if not df_trips.empty:
    st.markdown("### 🔎 Filters (trips)")
    colf1, colf2, colf3 = st.columns(3)

    with colf1:
        if "city" in df_trips.columns:
            city_options = sorted([c for c in df_trips["city"].dropna().unique()])
        else:
            city_options = []
        city_filter = st.multiselect("City (from trips)", city_options, default=city_options if city_options else None)

    with colf2:
        if "created_at" in df_trips.columns and df_trips["created_at"].notna().any():
            dates = df_trips["created_at"].dropna()
            min_date = dates.min().date()
            max_date = dates.max().date()
        else:
            today = date.today()
            min_date = max_date = today
        start_date, end_date = st.date_input("Date range (created_at)", value=(min_date, max_date))

    with colf3:
        if "routing_provider" in df_trips.columns:
            provider_options = sorted([p for p in df_trips["routing_provider"].dropna().unique()])
        else:
            provider_options = []
        provider_filter = st.multiselect("Routing provider", provider_options, default=provider_options if provider_options else None)

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

# METRICS
st.header("Platform metrics")
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
    total_gross = float(df_trips_filtered["price_xof"].sum())
    total_platform = float(df_trips_filtered["platform_commission_xof"].sum())
    total_driver = float(df_trips_filtered["driver_earnings_xof"].sum())
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

# DRIVERS TABLE
st.markdown("---")
st.subheader(L("drivers_table_header"))
if drivers:
    df_drivers = pd.DataFrame(drivers)
    st.dataframe(df_drivers)
else:
    st.info(L("no_drivers"))

# TRIPS TABLE
st.markdown("---")
st.subheader(L("trips_table_header") + " (filtered)")
if not df_trips_filtered.empty:
    st.dataframe(df_trips_filtered)
else:
    st.info("No trips (for current filters).")

# ADMIN LOGIN ANALYTICS
st.markdown("---")
st.subheader("👤 Admin login analytics")

logins = load_admin_logins_from_db(limit=300)
df_logins = pd.DataFrame(logins) if logins else pd.DataFrame()
if not df_logins.empty:
    if "timestamp_iso" in df_logins.columns:
        df_logins["timestamp_iso"] = pd.to_datetime(df_logins["timestamp_iso"], errors="coerce")
        df_logins["date"] = df_logins["timestamp_iso"].dt.date
        df_logins = df_logins.sort_values("timestamp_iso", ascending=False)

    st.markdown("#### Recent admin logins")
    st.dataframe(df_logins)

    st.markdown("#### Login count by email")
    if "email" in df_logins.columns:
        by_email = df_logins.groupby("email").size().reset_index(name="login_count")
        st.dataframe(by_email)
        st.bar_chart(by_email.set_index("email")["login_count"])

    st.markdown("#### Login count by mode (demo vs password)")
    if "mode" in df_logins.columns:
        by_mode = df_logins.groupby("mode").size().reset_index(name="login_count")
        st.dataframe(by_mode)
        st.bar_chart(by_mode.set_index("mode")["login_count"])
else:
    st.info("No admin login events recorded yet.")

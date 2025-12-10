
# Mali Ride – Full Demo (Passenger, Driver, Admin, Investor)

This repository is a **Streamlit-based ride hailing demo** for Mali, inspired by apps like Heetch and Uber, with:

- **Passenger app** – request & schedule trips, apply promo codes, see cancellation policy.
- **Driver app** – register drivers, see earnings & dynamic commissions, cancel trips with penalties & rating impact.
- **Admin dashboard** – always-open control center for drivers, trips, promotions, cancellations, and mobile usage.
- **Investor dashboard** – high-level KPIs and charts across the platform.

## Apps

All app entrypoints live in `apps/`:

- `apps/passenger_app.py`
- `apps/driver_app.py`
- `apps/admin_app.py`
- `apps/investor_dashboard.py`

Shared logic (data, pricing, geo, cancellations, ratings) is in:

- `core/shared.py`

All data is stored as local JSON files in:

- `data/drivers.json`
- `data/trips.json`
- `data/admin_logins.json`

These are created at runtime if they don't exist.

## Features

### Passenger app

- Choose pickup/dropoff inside Mali (Bamako and other cities).
- Pricing based on distance (haversine miles) + base fare.
- Promo code engine (`WELCOME50`, `MALI10`, etc.).
- Trip scheduling (date + time).
- **Cancellation policy:**
  - Free cancellation only if **4+ hours** before scheduled trip time.
  - If cancelled within 4h, passenger pays **75% of fare** as cancellation fee (goes to the platform).
- Stored trips appear in the **Admin** and **Investor** dashboards.

### Driver app

- Register new drivers with name, city, transport type.
- Launch driver with **initial rating 5.0** and `cancel_count = 0`.
- See weekly trips and earnings (last 7 days).
- **Dynamic commission tiers (Heetch-beating):**

  - 60+ trips / week → 8% platform commission  
  - 40–59 trips / week → 10%  
  - 20–39 trips / week → 12%  
  - 0–19 trips / week → 14%  

- **Driver cancellations:**
  - If a driver cancels a scheduled trip, the trip is marked `cancelled_by_driver`.
  - A penalty of **35% of the scheduled fare** is taken as platform revenue.
  - Driver earnings on that trip become 0.
  - The driver's rating is reduced by a small step each time (minimum rating 1.0).

### Admin dashboard

- **Always unlocked** in this demo – no password gate.
- Filters by city, date range, and routing provider.
- Top-level metrics:
  - Number of drivers
  - Available / busy / offline
  - Total trips (filtered)
  - Gross fares, platform revenue, and driver earnings
- Tabs:
  - **Driver** – supply, earnings, ratings, top drivers.
  - **Passenger** – trip volume by day, city mix, distance vs fare.
  - **Promotions** – promo & referral performance.
  - **Mobile** – trips by `client_app` (e.g. passenger mobile).
- Raw tables for:
  - Drivers
  - Trips (filtered)

### Investor dashboard

- High-level KPIs:
  - Drivers
  - Trips
  - Gross fares
  - Platform revenue
- Daily time-series charts.
- City mix, driver ranking by earnings, promo/referral performance.
- Cancellation analytics (status breakdown + total cancellation fees).
- Mobile vs web usage by `client_app`.

## Running locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run any app:

```bash
streamlit run apps/passenger_app.py
# or
streamlit run apps/driver_app.py
# or
streamlit run apps/admin_app.py
# or
streamlit run apps/investor_dashboard.py
```

## Deploying on Streamlit Cloud

1. Push this entire folder as a GitHub repo.
2. On Streamlit Cloud:
   - Create a new app.
   - Point it to this repo.
   - Set the **main file** to one of:
     - `apps/passenger_app.py`
     - `apps/driver_app.py`
     - `apps/admin_app.py`
     - `apps/investor_dashboard.py`
3. Deploy.

You can create **multiple deployed apps** using the same repo but different entrypoints (one for each app), or one "main hub" app that links to the others.

## Cancellation & rating logic (business rules)

- **Passenger cancellation:**
  - Free only if 4h+ before the scheduled time.
  - If <4h: 75% of fare is charged as a platform fee, driver earns 0.

- **Driver cancellation:**
  - 35% of the scheduled fare is taken as penalty fee by the platform.
  - Driver earns 0 on that trip.
  - Driver rating is reduced; repeated cancellations push rating down.

These rules are implemented in `core/shared.py` and enforced via the Passenger and Driver apps.

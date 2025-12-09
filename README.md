
# Mali Ride – Multi-App Demo (Driver, Passenger, Admin, Investor)

This repo contains a simplified **Uber-style demo for Mali** with:

- `apps/passenger_app.py` – passenger-facing app (distance pricing, promo codes, referrals)
- `apps/driver_app.py` – driver-facing app (registration + weekly earnings with tiered commissions)
- `apps/admin_app.py` – admin dashboard (demo-unlocked until 2026-12-31 with login analytics)
- `apps/investor_dashboard.py` – investor overview (drivers, passengers, promos, mobile usage)
- `core/shared.py` – shared logic (JSON persistence, pricing, commission tiers, promos)

## Run locally

```bash
pip install -r requirements.txt

# Passenger
streamlit run apps/passenger_app.py

# Driver
streamlit run apps/driver_app.py

# Admin
streamlit run apps/admin_app.py

# Investor overview
streamlit run apps/investor_dashboard.py
```

Data is stored as local JSON files under `data/` (auto-created).

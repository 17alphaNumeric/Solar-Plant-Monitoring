# ☀️ Solar Plant Performance Monitoring & Alert System

Automated Python pipeline that ingests sensor data from a 500-panel solar plant, detects underperforming panels, generates a daily performance report, emails the maintenance team, and refreshes a BI-ready dashboard — on a schedule, with no manual steps.

## Why this exists

Utility-scale and commercial solar plants log voltage, current, power, irradiance, and temperature from every panel every few minutes. Left unmonitored, a shaded, soiled, or wiring-faulted panel can silently underperform for weeks. This project automates the detection loop: **data arrives → gets cleaned → gets scored against a physics-based expected-output model → faults get flagged → maintenance gets alerted → everything lands in SQL and a dashboard.**

## Pipeline

```
CSV arrives in data/incoming/
        │
        ▼
Ingestion (src/data_ingestion.py) ── reads new files only, archives after processing
        │
        ▼
Cleaning (src/data_cleaning.py) ── dedupes, repairs sensor glitches, interpolates gaps
        │
        ▼
Analysis (src/performance_analysis.py) ── models expected power (irradiance + temp
        │                                  derating), computes efficiency, flags panels
        │                                  producing ≥20% below expected
        ▼
Persistence (src/database.py) ── stores every reading + alert in SQL (SQLAlchemy)
        │
        ▼
Reporting (src/report_generator.py) ── Excel + HTML daily report with charts
        │
        ▼
Alerting (src/email_alert.py) ── emails maintenance team (dry-run mode if no SMTP set)
        │
        ▼
Dashboard (src/dashboard.py) ── interactive Plotly HTML + CSV export for Power BI
```

## Features

- **Physics-based fault detection** — expected power is modeled from irradiance and cell temperature using the standard linear temperature-derating formula, not a naive threshold.
- **Self-healing data cleaning** — recomputes power from V×I when sensors disagree, clips impossible readings, interpolates gaps per panel.
- **Zero-config demo mode** — runs fully end-to-end out of the box: no real SMTP credentials or BI license required (email falls back to a saved `.eml` file; dashboard is a standalone HTML file).
- **SQL-backed** — every reading and alert is persisted via SQLAlchemy (SQLite by default; swap in Postgres/MySQL by changing one env var).
- **BI-ready** — exports a clean CSV plus a queryable SQL database for Power BI (or Tableau/Looker) to connect to directly.
- **Scheduled automation** — `schedule` library runs the whole pipeline every 5 minutes unattended.
- **Tested** — unit tests for the expected-power model, fault detection, and data cleaning; CI runs them (and a full pipeline smoke test) on every push.

## Quickstart

```bash
git clone https://github.com/<your-username>/solar-plant-monitoring.git
cd solar-plant-monitoring
pip install -r requirements.txt

# 1. Simulate the data logger: drops 12 synthetic 5-minute CSV batches
#    for 500 panels (with ~5% of panels injected as faulty) into data/incoming/
python main.py --generate-sample --batches 12

# 2. Run the pipeline once (processes everything currently in data/incoming/)
python main.py --once

# 3. Or run it continuously, matching the logger's real cadence
python main.py --run
```

After step 2, check:
- `reports/daily_report_*.xlsx` and `.html` — the daily report
- `reports/email_dry_run_*.eml` — the alert email (open in any text editor / mail client) if SMTP isn't configured
- `dashboard_output/dashboard.html` — open directly in a browser
- `dashboard_output/power_bi_export.csv` — import into Power BI (`Get Data → Text/CSV`)
- `data/solar_monitoring.db` — SQLite database; connect Power BI, DBeaver, or `sqlite3` directly

## Enabling real email alerts

Copy `.env.example` to `.env` and set `SMTP_USERNAME` / `SMTP_PASSWORD` (an app password works for Gmail). Without these set, the system automatically runs in **dry-run mode** and writes the composed email to disk instead — so the project is runnable by anyone who clones it.

## Connecting Power BI

Two options, both live off the same pipeline:
1. **CSV import**: point Power BI at `dashboard_output/power_bi_export.csv`, refresh on a schedule.
2. **Direct SQL connection**: point Power BI's SQLite/ODBC connector (or switch `DATABASE_URL` to Postgres for production) at `data/solar_monitoring.db` and query the `readings` / `alerts` tables directly for a live-refreshing report.

## Project structure

```
solar-plant-monitoring/
├── main.py                    # CLI entry point
├── config.py                  # all thresholds/paths/credentials (env-driven)
├── generate_sample_data.py    # synthetic data logger simulator
├── src/
│   ├── data_ingestion.py      # watches data/incoming/, archives processed files
│   ├── data_cleaning.py       # dedupe, repair, interpolate
│   ├── performance_analysis.py# expected-power model + fault detection
│   ├── database.py            # SQLAlchemy models + read/write helpers
│   ├── report_generator.py    # Excel + HTML report builder
│   ├── email_alert.py         # SMTP alerting (with dry-run fallback)
│   ├── dashboard.py            # Plotly dashboard + Power BI CSV export
│   └── scheduler.py            # orchestrates the full pipeline on a timer
├── tests/                      # pytest unit tests
└── .github/workflows/tests.yml # CI: tests + full pipeline smoke test
```

## Tech stack

Python, Pandas, NumPy, Matplotlib, Plotly, SQLAlchemy, `schedule`, `smtplib`, OpenPyXL, pytest, GitHub Actions.

## Possible extensions

- Swap the polling-based ingestion watcher for `watchdog` filesystem events or an MQTT feed from real inverters.
- Add a per-panel historical trend model (e.g. rolling z-score) to catch gradual degradation, not just point-in-time faults.
- Containerize with Docker and deploy the scheduler as a long-running service (systemd/Kubernetes CronJob).

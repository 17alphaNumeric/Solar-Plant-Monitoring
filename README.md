# ☀️ Solar Plant Performance Monitoring & Alert System

Automated Python pipeline that ingests sensor data from a 500-panel solar plant, detects underperforming panels, generates a daily performance report, emails the maintenance team, and refreshes a BI-ready dashboard — on a schedule, with no manual steps.

## Why this exists

Utility-scale and commercial solar plants log voltage, current, power, irradiance, and temperature from every panel every few minutes. Left unmonitored, a shaded, soiled, or wiring-faulted panel can silently underperform for weeks. This project automates the detection loop: **data arrives → gets cleaned → gets scored against a physics-based expected-output model → faults get flagged → maintenance gets alerted → everything lands in SQL and a dashboard.**


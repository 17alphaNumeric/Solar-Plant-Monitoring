"""
Central configuration for the Solar Plant Performance Monitoring & Alert System.
All values can be overridden with environment variables (see .env.example).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Plant / panel parameters
# ---------------------------------------------------------------------------
PANEL_COUNT = int(os.getenv("PANEL_COUNT", 500))
RATED_POWER_W = float(os.getenv("RATED_POWER_W", 400))      # W per panel at STC
STC_IRRADIANCE = 1000.0                                      # W/m^2 at Standard Test Conditions
STC_TEMP_C = 25.0                                            # deg C at STC
TEMP_COEFF_PER_C = float(os.getenv("TEMP_COEFF_PER_C", -0.004))  # power loss per degree above 25C

# Efficiency below which a panel is flagged as underperforming (0.80 = 20% below expected)
UNDERPERFORMANCE_THRESHOLD = float(os.getenv("UNDERPERFORMANCE_THRESHOLD", 0.80))
# Ignore low-light readings (dawn/dusk/night) below this irradiance when flagging faults
MIN_IRRADIANCE_FOR_CHECK = float(os.getenv("MIN_IRRADIANCE_FOR_CHECK", 100))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
INCOMING_DIR = BASE_DIR / "data" / "incoming"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "reports"
DASHBOARD_DIR = BASE_DIR / "dashboard_output"
DB_PATH = BASE_DIR / "data" / "solar_monitoring.db"
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

for d in (INCOMING_DIR, PROCESSED_DIR, REPORT_DIR, DASHBOARD_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
PIPELINE_INTERVAL_MINUTES = int(os.getenv("PIPELINE_INTERVAL_MINUTES", 5))

# ---------------------------------------------------------------------------
# Email alerts (SMTP). If SMTP_USERNAME/PASSWORD are not set, the system runs
# in DRY-RUN mode: it writes the alert email to disk instead of sending it,
# so the project is fully runnable out of the box without real credentials.
# ---------------------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", SMTP_USERNAME or "alerts@solarplant.local")
ALERT_EMAIL_TO = [e.strip() for e in os.getenv("ALERT_EMAIL_TO", "maintenance@solarplant.local").split(",") if e.strip()]
EMAIL_DRY_RUN = not (SMTP_USERNAME and SMTP_PASSWORD)

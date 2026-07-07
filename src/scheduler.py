"""
Orchestrates the full pipeline described in the project spec:

    CSV arrives -> Python starts -> reads data -> cleans data
    -> finds underperforming panels -> creates report -> sends email
    -> stores data in SQL -> refreshes dashboard/Power BI export

`run_pipeline_once()` processes every CSV currently sitting in data/incoming.
`start_scheduler()` runs that same function on a fixed interval (default:
every 5 minutes, matching the data logger's reporting cadence) using the
`schedule` library, so the whole thing can run unattended as a background job.
"""
import logging
import time
from pathlib import Path

import pandas as pd
import schedule

import config
from src import data_cleaning, data_ingestion, database, dashboard, email_alert, report_generator
from src.performance_analysis import calculate_efficiency, detect_underperforming, summarize_by_panel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def run_pipeline_once() -> dict:
    """Process every CSV waiting in data/incoming. Returns a summary dict."""
    database.init_db()

    files = data_ingestion.list_new_files()
    if not files:
        logger.info("scheduler: no new CSVs in %s", config.INCOMING_DIR)
        return {"processed_files": 0}

    frames = []
    for path in files:
        try:
            frames.append(data_ingestion.load_csv(path))
        except Exception:
            logger.exception("scheduler: failed to load %s", path)

    if not frames:
        return {"processed_files": 0}

    raw = pd.concat(frames, ignore_index=True)
    cleaned = data_cleaning.clean_readings(raw)
    analyzed = calculate_efficiency(cleaned)
    underperforming = detect_underperforming(analyzed)
    panel_summary = summarize_by_panel(analyzed)

    database.insert_readings(analyzed)
    database.insert_alerts(underperforming)

    report_paths = report_generator.generate_daily_report(analyzed, panel_summary, underperforming)
    email_path = email_alert.send_alert_email(underperforming, report_paths)
    dashboard.export_power_bi_csv(analyzed)
    dashboard_path = dashboard.build_dashboard(analyzed, panel_summary)

    for path in files:
        data_ingestion.archive_file(path)

    result = {
        "processed_files": len(files),
        "rows_processed": len(analyzed),
        "panels": int(analyzed["panel_id"].nunique()),
        "underperforming_panels": int(underperforming["panel_id"].nunique()) if not underperforming.empty else 0,
        "report": report_paths,
        "email": email_path,
        "dashboard": dashboard_path,
    }
    logger.info("scheduler: pipeline run complete -> %s", {k: v for k, v in result.items() if k not in ("report",)})
    return result


def start_scheduler(interval_minutes: int = config.PIPELINE_INTERVAL_MINUTES) -> None:
    logger.info("scheduler: running pipeline every %d minute(s). Ctrl+C to stop.", interval_minutes)
    schedule.every(interval_minutes).minutes.do(run_pipeline_once)
    run_pipeline_once()  # run immediately on startup, then wait for the schedule
    while True:
        schedule.run_pending()
        time.sleep(1)

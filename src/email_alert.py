"""
Sends the daily report + underperformance summary to the maintenance team.

If SMTP credentials are not configured (config.EMAIL_DRY_RUN), the composed
email is written to reports/ instead of sent, so the whole pipeline runs
end-to-end without needing real credentials.
"""
import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd

import config

logger = logging.getLogger(__name__)


def _build_message(underperforming: pd.DataFrame, report_paths: dict) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = config.ALERT_EMAIL_FROM
    msg["To"] = ", ".join(config.ALERT_EMAIL_TO)
    n = underperforming["panel_id"].nunique() if not underperforming.empty else 0
    msg["Subject"] = f"[Solar Plant Alert] {n} panel(s) underperforming - Daily Report"

    if n:
        worst = underperforming.sort_values("shortfall_pct", ascending=False).head(10)
        rows = "\n".join(
            f"  - Panel {r.panel_id}: producing {r.shortfall_pct:.1f}% below expected "
            f"({r.power_w:.0f}W vs {r.expected_power_w:.0f}W expected)"
            for r in worst.itertuples()
        )
        body = (
            f"{n} panel(s) are producing at least "
            f"{(1-config.UNDERPERFORMANCE_THRESHOLD)*100:.0f}% below expected output.\n\n"
            f"Top offenders:\n{rows}\n\n"
            "Full details are attached in the daily report.\n"
        )
    else:
        body = "All panels are performing within expected efficiency range. Daily report attached.\n"

    msg.attach(MIMEText(body, "plain"))

    xlsx_path: Path = report_paths.get("xlsx")
    if xlsx_path and xlsx_path.exists():
        with open(xlsx_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=xlsx_path.name)
        part["Content-Disposition"] = f'attachment; filename="{xlsx_path.name}"'
        msg.attach(part)

    return msg


def send_alert_email(underperforming: pd.DataFrame, report_paths: dict) -> Path | None:
    msg = _build_message(underperforming, report_paths)

    if config.EMAIL_DRY_RUN:
        dry_run_path = config.REPORT_DIR / f"email_dry_run_{report_paths['xlsx'].stem}.eml"
        dry_run_path.write_text(msg.as_string(), encoding="utf-8")
        logger.warning(
            "email_alert: SMTP not configured -- DRY RUN. Email content saved to %s",
            dry_run_path,
        )
        return dry_run_path

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.sendmail(config.ALERT_EMAIL_FROM, config.ALERT_EMAIL_TO, msg.as_string())
        logger.info("email_alert: alert email sent to %s", config.ALERT_EMAIL_TO)
        return None
    except Exception:
        logger.exception("email_alert: failed to send email, falling back to dry run")
        fallback_path = config.REPORT_DIR / f"email_send_failed_{report_paths['xlsx'].stem}.eml"
        fallback_path.write_text(msg.as_string(), encoding="utf-8")
        return fallback_path

"""
Produces the visual layer on top of the SQL data:

1. A self-contained interactive Plotly HTML dashboard (dashboard_output/dashboard.html)
   -- open it directly in a browser, no server needed.
2. A flat CSV export (dashboard_output/power_bi_export.csv) formatted for
   Power BI: point Power BI's "Get Data -> Text/CSV" (or a scheduled refresh
   against the SQLite/Postgres database directly) at this file/table to get
   a live-refreshing report on top of the same pipeline.
"""
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config

logger = logging.getLogger(__name__)


def export_power_bi_csv(readings: pd.DataFrame, out_dir: Path = config.DASHBOARD_DIR) -> Path:
    out_path = out_dir / "power_bi_export.csv"
    cols = ["timestamp", "panel_id", "voltage_v", "current_a", "power_w",
            "irradiance_wm2", "temperature_c", "expected_power_w", "efficiency"]
    readings[cols].to_csv(out_path, index=False)
    logger.info("dashboard: exported %d rows to %s for Power BI", len(readings), out_path)
    return out_path


def build_dashboard(readings: pd.DataFrame, panel_summary: pd.DataFrame,
                     out_dir: Path = config.DASHBOARD_DIR) -> Path:
    out_path = out_dir / "dashboard.html"

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Plant Output Over Time (kW)",
            "Efficiency Distribution Across Panels",
            "20 Lowest-Efficiency Panels",
            "Temperature vs. Efficiency",
        ),
        specs=[[{"type": "scatter"}, {"type": "histogram"}],
               [{"type": "bar"}, {"type": "scatter"}]],
    )

    plant_over_time = (
        readings.groupby("timestamp")["power_w"].sum().div(1000).reset_index(name="plant_kw")
    )
    fig.add_trace(
        go.Scatter(x=plant_over_time["timestamp"], y=plant_over_time["plant_kw"],
                   mode="lines", name="Plant output (kW)"),
        row=1, col=1,
    )

    fig.add_trace(
        go.Histogram(x=readings["efficiency"].dropna() * 100, nbinsx=30, name="Efficiency %"),
        row=1, col=2,
    )

    worst = panel_summary.sort_values("avg_efficiency").head(20)
    fig.add_trace(
        go.Bar(x=worst["panel_id"].astype(str), y=worst["avg_efficiency"] * 100,
               marker_color="crimson", name="Lowest efficiency panels"),
        row=2, col=1,
    )

    fig.add_trace(
        go.Scatter(x=readings["temperature_c"], y=readings["efficiency"] * 100,
                   mode="markers", marker=dict(size=4, opacity=0.4), name="Panels"),
        row=2, col=2,
    )

    fig.update_layout(
        title="Solar Plant Performance Dashboard",
        height=800, showlegend=False, template="plotly_white",
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn")
    logger.info("dashboard: wrote %s", out_path)
    return out_path

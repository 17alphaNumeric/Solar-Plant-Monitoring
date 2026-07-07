"""
Persistence layer. Stores every cleaned reading and every underperformance
alert in SQL (SQLite by default; point DATABASE_URL at Postgres/MySQL/etc for
production) via SQLAlchemy Core. Power BI (or any BI tool) can connect
directly to this database, or import the CSV export produced by
src/dashboard.py, to build a live dashboard on top of the same data.
"""
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
)

import config

logger = logging.getLogger(__name__)

engine = create_engine(config.DB_URL, future=True)
metadata = MetaData()

readings_table = Table(
    "readings",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", DateTime, nullable=False, index=True),
    Column("panel_id", String, nullable=False, index=True),
    Column("voltage_v", Float),
    Column("current_a", Float),
    Column("power_w", Float),
    Column("irradiance_wm2", Float),
    Column("temperature_c", Float),
    Column("expected_power_w", Float),
    Column("efficiency", Float),
)

alerts_table = Table(
    "alerts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime, nullable=False, index=True),
    Column("panel_id", String, nullable=False, index=True),
    Column("timestamp", DateTime, nullable=False),
    Column("efficiency", Float),
    Column("shortfall_pct", Float),
    Column("power_w", Float),
    Column("expected_power_w", Float),
)


def init_db() -> None:
    metadata.create_all(engine)
    logger.info("database: schema ready at %s", config.DB_URL)


def insert_readings(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    cols = [c.name for c in readings_table.columns if c.name != "id"]
    records = df[[c for c in cols if c in df.columns]].to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(readings_table.insert(), records)
    logger.info("database: inserted %d readings", len(records))
    return len(records)


def insert_alerts(alerts_df: pd.DataFrame) -> int:
    if alerts_df.empty:
        return 0
    now = datetime.now(timezone.utc)
    records = []
    for _, row in alerts_df.iterrows():
        records.append(
            {
                "created_at": now,
                "panel_id": row["panel_id"],
                "timestamp": row["timestamp"],
                "efficiency": float(row["efficiency"]),
                "shortfall_pct": float(row["shortfall_pct"]),
                "power_w": float(row["power_w"]),
                "expected_power_w": float(row["expected_power_w"]),
            }
        )
    with engine.begin() as conn:
        conn.execute(alerts_table.insert(), records)
    logger.info("database: inserted %d alerts", len(records))
    return len(records)


def fetch_recent_readings(limit: int = 5000) -> pd.DataFrame:
    with engine.connect() as conn:
        stmt = select(readings_table).order_by(readings_table.c.timestamp.desc()).limit(limit)
        return pd.read_sql(stmt, conn)


def fetch_recent_alerts(limit: int = 500) -> pd.DataFrame:
    with engine.connect() as conn:
        stmt = select(alerts_table).order_by(alerts_table.c.created_at.desc()).limit(limit)
        return pd.read_sql(stmt, conn)

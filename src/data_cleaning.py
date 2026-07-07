"""
Data cleaning utilities for raw solar panel sensor readings.

Raw CSVs coming off the data logger can contain: duplicate rows (logger
retries), missing sensor values (dropped packets), and physically impossible
readings (sensor glitches -- e.g. negative irradiance, voltage spikes).
"""
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Plausible physical bounds for a typical 400W residential/commercial panel.
PLAUSIBLE_RANGES = {
    "voltage_v": (0, 60),
    "current_a": (0, 12),
    "power_w": (0, 500),
    "irradiance_wm2": (0, 1200),
    "temperature_c": (-10, 85),
}

REQUIRED_COLUMNS = [
    "timestamp",
    "panel_id",
    "voltage_v",
    "current_a",
    "power_w",
    "irradiance_wm2",
    "temperature_c",
]


def clean_readings(df: pd.DataFrame) -> pd.DataFrame:
    """Validate schema, drop duplicates, clip/flag out-of-range values,
    and interpolate missing readings on a per-panel basis.
    """
    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Input CSV is missing required columns: {missing_cols}")

    df = df.copy()
    before = len(df)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates(subset=["timestamp", "panel_id"])

    # Recompute power from V*I when the reported power disagrees wildly with
    # V*I (a common sensor fault) -- keeps the "power" column trustworthy.
    computed_power = df["voltage_v"] * df["current_a"]
    disagreement = (df["power_w"] - computed_power).abs() > (0.25 * computed_power.clip(lower=1))
    df.loc[disagreement, "power_w"] = computed_power[disagreement]

    # Clip physically impossible values, then null out extreme sensor glitches
    # so they get interpolated rather than silently clipped to a boundary.
    for col, (low, high) in PLAUSIBLE_RANGES.items():
        out_of_range = (df[col] < low) | (df[col] > high)
        df.loc[out_of_range, col] = np.nan

    # Interpolate missing values per panel along the time axis. Sort + reset
    # the index first so that groupby().transform() output aligns back onto
    # the correct rows (using .apply(...).reset_index(drop=True) here would
    # silently scramble values across panels -- caught via testing).
    df = df.sort_values(["panel_id", "timestamp"]).reset_index(drop=True)
    numeric_cols = list(PLAUSIBLE_RANGES.keys())
    df[numeric_cols] = df.groupby("panel_id")[numeric_cols].transform(
        lambda g: g.interpolate(limit_direction="both")
    )

    # Any panel where a whole column is NaN (interpolation impossible) -> drop.
    df = df.dropna(subset=numeric_cols)

    removed = before - len(df)
    if removed:
        logger.info("data_cleaning: removed/repaired %d of %d rows", removed, before)

    return df.reset_index(drop=True)

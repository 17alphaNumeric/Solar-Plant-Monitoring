import numpy as np
import pandas as pd
import pytest

from src.data_cleaning import clean_readings


def _base_df(n=5):
    ts = pd.date_range("2026-07-07 12:00:00", periods=n, freq="5min")
    return pd.DataFrame({
        "timestamp": ts,
        "panel_id": ["PNL-0001"] * n,
        "voltage_v": [36.0] * n,
        "current_a": [10.0] * n,
        "power_w": [360.0] * n,
        "irradiance_wm2": [900.0] * n,
        "temperature_c": [25.0] * n,
    })


def test_missing_required_column_raises():
    df = _base_df().drop(columns=["irradiance_wm2"])
    with pytest.raises(ValueError):
        clean_readings(df)


def test_duplicates_are_removed():
    df = pd.concat([_base_df(1), _base_df(1)], ignore_index=True)
    cleaned = clean_readings(df)
    assert len(cleaned) == 1


def test_out_of_range_irradiance_is_interpolated():
    df = _base_df(5)
    df.loc[2, "irradiance_wm2"] = 5000  # impossible sensor spike
    cleaned = clean_readings(df)
    assert cleaned["irradiance_wm2"].max() < 5000
    assert len(cleaned) == 5


def test_negative_values_are_repaired():
    df = _base_df(3)
    df.loc[1, "power_w"] = -50
    cleaned = clean_readings(df)
    assert (cleaned["power_w"] >= 0).all()

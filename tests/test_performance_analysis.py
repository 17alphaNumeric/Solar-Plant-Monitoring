import pandas as pd
import pytest

import config
from src.performance_analysis import (
    calculate_efficiency,
    detect_underperforming,
    expected_power_w,
    summarize_by_panel,
)


def make_reading(panel_id="PNL-0001", power_w=350, irradiance_wm2=900, temperature_c=25):
    return pd.DataFrame([{
        "timestamp": pd.Timestamp("2026-07-07 12:00:00"),
        "panel_id": panel_id,
        "voltage_v": 36.0,
        "current_a": power_w / 36.0,
        "power_w": power_w,
        "irradiance_wm2": irradiance_wm2,
        "temperature_c": temperature_c,
    }])


def test_expected_power_at_stc_equals_rated_power():
    result = expected_power_w(pd.Series([1000.0]), pd.Series([25.0]), rated_power_w=400)
    assert result.iloc[0] == pytest.approx(400, rel=1e-6)


def test_expected_power_scales_with_irradiance():
    half_sun = expected_power_w(pd.Series([500.0]), pd.Series([25.0]), rated_power_w=400)
    assert half_sun.iloc[0] == pytest.approx(200, rel=1e-6)


def test_expected_power_derates_with_temperature():
    hot = expected_power_w(pd.Series([1000.0]), pd.Series([45.0]), rated_power_w=400)
    assert hot.iloc[0] < 400


def test_healthy_panel_not_flagged():
    df = make_reading(power_w=360, irradiance_wm2=900, temperature_c=25)
    analyzed = calculate_efficiency(df)
    flagged = detect_underperforming(analyzed)
    assert flagged.empty


def test_faulty_panel_is_flagged():
    # Expected power at 900 W/m2, 25C, 400W rated ~= 360W. 200W is ~44% below.
    df = make_reading(panel_id="PNL-0002", power_w=200, irradiance_wm2=900, temperature_c=25)
    analyzed = calculate_efficiency(df)
    flagged = detect_underperforming(analyzed)
    assert len(flagged) == 1
    assert flagged.iloc[0]["panel_id"] == "PNL-0002"
    assert flagged.iloc[0]["shortfall_pct"] > 20


def test_night_readings_not_flagged_even_if_zero_power():
    df = make_reading(power_w=0, irradiance_wm2=0, temperature_c=18)
    analyzed = calculate_efficiency(df)
    flagged = detect_underperforming(analyzed)
    assert flagged.empty


def test_summarize_by_panel_returns_one_row_per_panel():
    df = pd.concat([
        make_reading(panel_id="PNL-0001", power_w=360),
        make_reading(panel_id="PNL-0002", power_w=200),
    ], ignore_index=True)
    analyzed = calculate_efficiency(df)
    summary = summarize_by_panel(analyzed)
    assert set(summary["panel_id"]) == {"PNL-0001", "PNL-0002"}
    assert summary.iloc[0]["avg_efficiency"] <= summary.iloc[1]["avg_efficiency"]

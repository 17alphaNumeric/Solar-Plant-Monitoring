"""
Core performance-analysis logic: expected power modelling, efficiency
calculation, and underperforming-panel detection.

Model
-----
Expected power output of a panel is estimated from irradiance and cell
temperature using the standard linear temperature-derating model:

    P_expected = P_rated * (G / G_stc) * (1 + gamma * (T_cell - T_stc))

where G is measured irradiance (W/m^2), G_stc = 1000 W/m^2, gamma is the
panel's temperature coefficient of power (~ -0.4%/degC for crystalline
silicon), and T_stc = 25 degC.
"""
import pandas as pd

import config


def expected_power_w(irradiance_wm2: pd.Series, temperature_c: pd.Series,
                      rated_power_w: float = config.RATED_POWER_W) -> pd.Series:
    temp_factor = 1 + config.TEMP_COEFF_PER_C * (temperature_c - config.STC_TEMP_C)
    expected = rated_power_w * (irradiance_wm2 / config.STC_IRRADIANCE) * temp_factor
    return expected.clip(lower=0)


def calculate_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    """Add `expected_power_w` and `efficiency` columns to a readings dataframe."""
    df = df.copy()
    df["expected_power_w"] = expected_power_w(df["irradiance_wm2"], df["temperature_c"])

    # Efficiency is only meaningful in daylight; avoid divide-by-zero at night.
    daylight = df["irradiance_wm2"] >= config.MIN_IRRADIANCE_FOR_CHECK
    df["efficiency"] = pd.NA
    df.loc[daylight, "efficiency"] = (
        df.loc[daylight, "power_w"] / df.loc[daylight, "expected_power_w"].clip(lower=1e-6)
    )
    df["efficiency"] = pd.to_numeric(df["efficiency"], errors="coerce")
    return df


def detect_underperforming(df: pd.DataFrame,
                            threshold: float = config.UNDERPERFORMANCE_THRESHOLD) -> pd.DataFrame:
    """Return rows for panels producing less than `threshold` of expected
    power during daylight hours (default: flag panels >=20% below expected).
    """
    daylight = df["irradiance_wm2"] >= config.MIN_IRRADIANCE_FOR_CHECK
    underperforming = df[daylight & (df["efficiency"] < threshold)].copy()
    underperforming["shortfall_pct"] = (1 - underperforming["efficiency"]) * 100
    return underperforming.sort_values("shortfall_pct", ascending=False)


def summarize_by_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the latest batch into one row per panel for reporting."""
    agg = (
        df.groupby("panel_id")
        .agg(
            avg_power_w=("power_w", "mean"),
            avg_expected_power_w=("expected_power_w", "mean"),
            avg_efficiency=("efficiency", "mean"),
            avg_temperature_c=("temperature_c", "mean"),
            avg_irradiance_wm2=("irradiance_wm2", "mean"),
            readings=("power_w", "count"),
        )
        .reset_index()
    )
    return agg.sort_values("avg_efficiency")

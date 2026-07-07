"""
Simulates the data logger: generates realistic per-panel sensor readings for
a 500-panel plant and drops them into data/incoming/ as CSV files, one file
per 5-minute batch -- exactly how the real logger would deliver data.

Run standalone: `python generate_sample_data.py --batches 12`
"""
import argparse
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config

RNG = np.random.default_rng(42)


def _irradiance_curve(minute_of_day: float) -> float:
    """Rough bell curve peaking at solar noon (12:00), zero before 6:00/after 18:00."""
    sunrise, sunset, peak = 6 * 60, 18 * 60, 12 * 60
    if minute_of_day <= sunrise or minute_of_day >= sunset:
        return 0.0
    x = (minute_of_day - sunrise) / (sunset - sunrise) * np.pi
    return max(0.0, 950 * np.sin(x))


def _ambient_temp(minute_of_day: float) -> float:
    """Daily temperature swing between ~18C (dawn) and ~33C (mid-afternoon)."""
    return 25 + 8 * np.sin((minute_of_day - 6 * 60) / (16 * 60) * np.pi)


def generate_batch(timestamp: datetime, panel_count: int = config.PANEL_COUNT,
                    faulty_panel_ids: set = frozenset()) -> pd.DataFrame:
    minute_of_day = timestamp.hour * 60 + timestamp.minute
    base_irradiance = _irradiance_curve(minute_of_day)
    ambient_temp = _ambient_temp(minute_of_day)

    rows = []
    for i in range(1, panel_count + 1):
        panel_id = f"PNL-{i:04d}"
        irradiance = max(0.0, RNG.normal(base_irradiance, 25))
        cell_temp = ambient_temp + irradiance * 0.03 + RNG.normal(0, 1.0)

        temp_factor = 1 + config.TEMP_COEFF_PER_C * (cell_temp - config.STC_TEMP_C)
        expected = max(0.0, config.RATED_POWER_W * (irradiance / config.STC_IRRADIANCE) * temp_factor)

        degradation = RNG.normal(1.0, 0.02)  # small healthy-panel noise
        if panel_id in faulty_panel_ids:
            degradation *= RNG.uniform(0.55, 0.78)  # simulate soiling/shading/wiring fault

        power = max(0.0, expected * degradation)
        voltage = round(RNG.normal(36 if power > 5 else 20, 1.5), 2)
        current = round(power / voltage, 3) if voltage > 0 else 0.0

        rows.append(
            {
                "timestamp": timestamp.isoformat(),
                "panel_id": panel_id,
                "voltage_v": voltage,
                "current_a": current,
                "power_w": round(power, 2),
                "irradiance_wm2": round(irradiance, 1),
                "temperature_c": round(cell_temp, 2),
            }
        )
    return pd.DataFrame(rows)


def main(batches: int = 12, interval_minutes: int = 5, start: datetime = None,
         fault_rate: float = 0.05):
    start = start or datetime.now().replace(second=0, microsecond=0)
    n_faulty = max(1, int(config.PANEL_COUNT * fault_rate))
    faulty_ids = {f"PNL-{i:04d}" for i in RNG.choice(range(1, config.PANEL_COUNT + 1), n_faulty, replace=False)}

    print(f"Simulating {batches} batch(es) of {config.PANEL_COUNT} panels "
          f"({interval_minutes}-min intervals), {len(faulty_ids)} faulty panels injected.")

    for b in range(batches):
        ts = start + timedelta(minutes=interval_minutes * b)
        df = generate_batch(ts, faulty_panel_ids=faulty_ids)
        out_path = config.INCOMING_DIR / f"solar_readings_{ts.strftime('%Y%m%d_%H%M')}.csv"
        df.to_csv(out_path, index=False)
        print(f"  wrote {out_path.name} ({len(df)} rows)")

    print(f"Done. Faulty panels this run: {sorted(faulty_ids)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic solar plant sensor data.")
    parser.add_argument("--batches", type=int, default=12, help="Number of 5-min CSV batches to generate")
    parser.add_argument("--interval-minutes", type=int, default=5)
    parser.add_argument("--fault-rate", type=float, default=0.05, help="Fraction of panels simulated as faulty")
    args = parser.parse_args()
    main(batches=args.batches, interval_minutes=args.interval_minutes, fault_rate=args.fault_rate)

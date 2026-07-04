#!/usr/bin/env python3
"""
Generate synthetic sensor CSV data with realistic patterns and labeled anomalies.

Columns:
  timestamp, temperature_C, humidity_pct, people_count, time_spent_sec,
  alarm_status, is_anomaly, anomaly_type

Usage:
    python -m src.data_processing.sensor_generator \
        --output data/sensor_data.csv \
        --hours 24 \
        --seed 42
"""

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


BASE_TEMP = 25.0
TEMP_AMPLITUDE = 6.0
BASE_HUMIDITY = 55.0
HUMIDITY_AMPLITUDE = 15.0
ANOMALY_PROBABILITY = 0.005  # ~0.5 % of readings are anomalous


def _diurnal_offset(seconds: int) -> float:
    """Return a temperature offset based on time of day (0–86400 s).
    Peak at 14:00, trough at 04:00.
    """
    return -2.0 + 4.0 * ((seconds / 86400.0 - 0.25) * 2 * 3.14159) ** 2 / 40.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def generate_sensor_data(
    hours: float = 24.0,
    interval_s: int = 1,
    seed: Optional[int] = None,
    anomaly_prob: float = ANOMALY_PROBABILITY,
) -> list[dict]:
    """Generate a list of sensor reading dicts."""
    if seed is not None:
        random.seed(seed)

    rng = random.Random(seed)
    total = int(hours * 3600 / interval_s)
    base_time = datetime(2026, 7, 2, 0, 0, 0)
    rows: list[dict] = []

    temp_noise = 0.0
    people = 0
    anomaly_active = False
    anomaly_type = ""

    for i in range(total):
        ts = base_time + timedelta(seconds=i * interval_s)
        seconds = (ts.hour * 3600 + ts.minute * 60 + ts.second)

        # --- Temperature with diurnal cycle + noise ---
        temp = (
            BASE_TEMP
            + TEMP_AMPLITUDE * _diurnal_offset(seconds)
            + rng.gauss(0, 0.5)
            + temp_noise
        )

        # --- Humidity (inverse correlation with temp) ---
        humidity = (
            BASE_HUMIDITY
            - HUMIDITY_AMPLITUDE * _diurnal_offset(seconds) * 0.6
            + rng.gauss(0, 2.0)
        )

        # --- People count (work hours pattern) ---
        hour = ts.hour
        if 8 <= hour <= 18:
            target_people = rng.randint(1, 5)
        else:
            target_people = rng.randint(0, 2)
        people += (target_people - people) * 0.2
        people = max(0, int(round(people)))

        # --- Time spent ---
        time_spent = rng.randint(10, 600) if people > 0 else 0

        # --- Anomaly injection ---
        is_anomaly = False
        anomaly_label = ""

        if anomaly_active:
            is_anomaly = True
            if anomaly_type == "temp_spike":
                temp += rng.uniform(10, 20)
            elif anomaly_type == "humidity_spike":
                humidity += rng.uniform(20, 35)
            elif anomaly_type == "people_surge":
                people = rng.randint(10, 30)
            elif anomaly_type == "sensor_fault":
                temp = -99.9
                humidity = -99.9
            anomaly_label = anomaly_type
            anomaly_active = rng.random() > 0.3  # decay
        else:
            if rng.random() < anomaly_prob:
                anomaly_active = True
                anomaly_type = rng.choice([
                    "temp_spike", "humidity_spike", "people_surge", "sensor_fault"
                ])
                is_anomaly = True
                anomaly_label = anomaly_type
                if anomaly_type == "temp_spike":
                    temp += rng.uniform(10, 20)
                elif anomaly_type == "humidity_spike":
                    humidity += rng.uniform(20, 35)
                elif anomaly_type == "people_surge":
                    people = rng.randint(10, 30)
                elif anomaly_type == "sensor_fault":
                    temp = -99.9
                    humidity = -99.9

        alarm_status = 1 if anomaly_active else 0

        rows.append({
            "timestamp": ts.isoformat(),
            "temperature_C": round(_clamp(temp, -100, 100), 2),
            "humidity_pct": round(_clamp(humidity, 0, 100), 2),
            "people_count": int(people),
            "time_spent_sec": time_spent,
            "alarm_status": alarm_status,
            "is_anomaly": int(is_anomaly),
            "anomaly_type": anomaly_label,
        })

    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    """Write sensor data to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "timestamp", "temperature_C", "humidity_pct", "people_count",
        "time_spent_sec", "alarm_status", "is_anomaly", "anomaly_type",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic sensor CSV data")
    parser.add_argument("--output", default="data/sensor_data.csv", help="Output CSV path")
    parser.add_argument("--hours", type=float, default=24.0, help="Hours of data (default: 24)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--interval", type=int, default=1, help="Reading interval in seconds (default: 1)")
    args = parser.parse_args()

    output_path = Path(args.output)
    rows = generate_sensor_data(
        hours=args.hours,
        interval_s=args.interval,
        seed=args.seed,
    )
    write_csv(rows, output_path)


if __name__ == "__main__":
    main()

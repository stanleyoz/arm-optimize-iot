"""Shared fixtures for tests."""

import pytest

from src.data_processing.sensor_generator import generate_sensor_data
from src.data_processing.sensor_reader import SensorReader, SensorWindow
from src.alerting.threshold_rules import ThresholdConfig


@pytest.fixture
def sample_csv(tmp_path):
    """Generate a 10-minute sensor CSV file and return its path."""
    rows = generate_sensor_data(hours=10 / 60, interval_s=1, seed=42)
    path = tmp_path / "sensor_data.csv"
    import csv
    fieldnames = [
        "timestamp", "temperature_C", "humidity_pct", "people_count",
        "time_spent_sec", "alarm_status", "is_anomaly", "anomaly_type",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.fixture
def reader(sample_csv):
    """Return a SensorReader for the sample data."""
    return SensorReader(str(sample_csv))


@pytest.fixture
def last_window(reader):
    """Return the last 30-second window from sample data."""
    return reader.window(seconds=30)


@pytest.fixture
def default_thresholds():
    return ThresholdConfig()

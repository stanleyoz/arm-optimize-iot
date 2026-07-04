"""Tests for the sensor data generator."""

from src.data_processing.sensor_generator import generate_sensor_data


def test_generates_correct_row_count():
    rows = generate_sensor_data(hours=1, interval_s=1, seed=42)
    assert len(rows) == 3600


def test_generates_correct_columns():
    rows = generate_sensor_data(hours=0.1, seed=42)
    row = rows[0]
    expected_keys = {
        "timestamp", "temperature_C", "humidity_pct", "people_count",
        "time_spent_sec", "alarm_status", "is_anomaly", "anomaly_type",
    }
    assert set(row.keys()) == expected_keys


def test_reproducible_with_seed():
    a = generate_sensor_data(hours=0.1, seed=42)
    b = generate_sensor_data(hours=0.1, seed=42)
    assert a == b


def test_different_seeds_different():
    a = generate_sensor_data(hours=0.1, seed=42)
    b = generate_sensor_data(hours=0.1, seed=99)
    assert a != b


def test_temperature_range():
    rows = generate_sensor_data(hours=24, seed=42)
    temps = [r["temperature_C"] for r in rows]
    assert all(-100 <= t <= 100 for t in temps)
    # Normal readings without anomalies should be within reasonable bounds
    normal_temps = [r["temperature_C"] for r in rows if not r["is_anomaly"]]
    assert all(0 <= t <= 50 for t in normal_temps)


def test_humidity_range():
    rows = generate_sensor_data(hours=24, seed=42)
    hums = [r["humidity_pct"] for r in rows]
    assert all(0 <= h <= 100 for h in hums)


def test_people_count_non_negative():
    rows = generate_sensor_data(hours=24, seed=42)
    assert all(r["people_count"] >= 0 for r in rows)


def test_anomalies_injected():
    rows = generate_sensor_data(hours=24, seed=42)
    anomalies = [r for r in rows if r["is_anomaly"]]
    assert len(anomalies) > 0
    anomaly_types = {r["anomaly_type"] for r in anomalies}
    assert "temp_spike" in anomaly_types or "humidity_spike" in anomaly_types


def test_alarm_active_during_anomaly_burst():
    rows = generate_sensor_data(hours=24, seed=42)
    # Anomaly rows should sometimes have alarm_status=1
    anomaly_rows = [r for r in rows if r["is_anomaly"]]
    assert any(r["alarm_status"] == 1 for r in anomaly_rows)
    # Rows with no anomaly flag and no type label should never alarm
    clean = [r for r in rows if not r["is_anomaly"] and not r["anomaly_type"]]
    assert all(r["alarm_status"] == 0 for r in clean)


def test_timestamp_format():
    rows = generate_sensor_data(hours=0.1, seed=42)
    for r in rows:
        assert "T" in r["timestamp"]  # ISO format

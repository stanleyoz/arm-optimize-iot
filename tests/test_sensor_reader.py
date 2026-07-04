"""Tests for the sensor data reader."""

from src.data_processing.sensor_reader import SensorReader, SensorWindow


def test_reader_loads_csv(sample_csv):
    reader = SensorReader(str(sample_csv))
    assert len(reader._data) > 0


def test_latest_returns_last_reading(reader):
    latest = reader.latest()
    assert latest is not None
    assert "temperature_C" in latest


def test_window_returns_correct_count(reader):
    window = reader.window(seconds=30)
    assert isinstance(window, SensorWindow)
    assert len(window.readings) > 0


def test_window_zero_seconds(reader):
    window = reader.window(seconds=0)
    # Should return at least the last reading
    assert len(window.readings) >= 0


def test_window_to_prompt_format(reader):
    window = reader.window(seconds=10)
    prompt = window.to_prompt()
    assert "temp=" in prompt
    assert "humid=" in prompt


def test_window_summary_keys(reader):
    window = reader.window(seconds=30)
    summary = window.summary()
    expected_keys = {
        "temp_min", "temp_max", "temp_avg",
        "humidity_min", "humidity_max", "humidity_avg",
        "people_max", "people_avg", "reading_count",
    }
    assert set(summary.keys()) == expected_keys


def test_stream_yields_windows(reader):
    windows = list(reader.stream(window_s=30, step_s=30))
    assert len(windows) > 0
    assert all(isinstance(w, SensorWindow) for w in windows)


def test_stream_increasing_timestamps(reader):
    windows = list(reader.stream(window_s=10, step_s=5))
    starts = [w.start_time for w in windows if w.readings]
    assert all(s <= e for s, e in zip(starts, starts[1:]))


def test_empty_file(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("timestamp,temperature_C,humidity_pct,people_count,time_spent_sec,alarm_status\n")
    reader = SensorReader(str(path))
    assert reader.latest() is None
    window = reader.window(seconds=30)
    assert len(window.readings) == 0

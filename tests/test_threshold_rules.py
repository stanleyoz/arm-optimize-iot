"""Tests for threshold rules."""

from src.alerting.threshold_rules import ThresholdConfig, evaluate, TriggeredRule


def test_no_triggers_normal_readings(default_thresholds):
    summary = {
        "temp_min": 22.0,
        "temp_max": 26.0,
        "humidity_min": 40.0,
        "humidity_max": 60.0,
        "people_max": 3,
    }
    result = evaluate(summary, default_thresholds)
    assert result == []


def test_temp_high_triggers(default_thresholds):
    summary = {"temp_min": 25.0, "temp_max": 42.0, "humidity_min": 50.0,
               "humidity_max": 60.0, "people_max": 1}
    result = evaluate(summary, default_thresholds)
    names = [r.name for r in result]
    assert "temp_high" in names


def test_temp_low_triggers(default_thresholds):
    summary = {"temp_min": -5.0, "temp_max": 10.0, "humidity_min": 50.0,
               "humidity_max": 60.0, "people_max": 1}
    result = evaluate(summary, default_thresholds)
    names = [r.name for r in result]
    assert "temp_low" in names


def test_humidity_high_triggers(default_thresholds):
    summary = {"temp_min": 20.0, "temp_max": 25.0, "humidity_min": 50.0,
               "humidity_max": 95.0, "people_max": 1}
    result = evaluate(summary, default_thresholds)
    names = [r.name for r in result]
    assert "humidity_high" in names


def test_humidity_low_triggers(default_thresholds):
    summary = {"temp_min": 20.0, "temp_max": 25.0, "humidity_min": 5.0,
               "humidity_max": 30.0, "people_max": 1}
    result = evaluate(summary, default_thresholds)
    names = [r.name for r in result]
    assert "humidity_low" in names


def test_people_high_triggers(default_thresholds):
    summary = {"temp_min": 20.0, "temp_max": 25.0, "humidity_min": 50.0,
               "humidity_max": 60.0, "people_max": 15}
    result = evaluate(summary, default_thresholds)
    names = [r.name for r in result]
    assert "people_high" in names


def test_multiple_triggers_simultaneously(default_thresholds):
    summary = {"temp_min": -10.0, "temp_max": 50.0, "humidity_min": 5.0,
               "humidity_max": 95.0, "people_max": 20}
    result = evaluate(summary, default_thresholds)
    assert len(result) >= 3


def test_triggered_rule_dataclass():
    rule = TriggeredRule(name="test", value=42.0, threshold=40.0,
                         severity="high", message="Test alert")
    assert rule.name == "test"
    assert rule.severity == "high"


def test_custom_threshold():
    config = ThresholdConfig(temp_max=30.0)
    summary = {"temp_min": 20.0, "temp_max": 35.0, "humidity_min": 50.0,
               "humidity_max": 60.0, "people_max": 1}
    result = evaluate(summary, config)
    assert len(result) == 1
    assert result[0].name == "temp_high"

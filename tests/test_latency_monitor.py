"""Tests for latency monitor."""

from src.alerting.latency_monitor import LatencyMonitor


def test_under_budget():
    monitor = LatencyMonitor(budget_ms=2000.0)
    assert monitor.check(100.0) is False
    assert monitor.check(500.0) is False


def test_over_budget():
    monitor = LatencyMonitor(budget_ms=1000.0)
    assert monitor.check(1500.0) is True


def test_stats_recorded():
    monitor = LatencyMonitor(budget_ms=2000.0, window_size=10)
    for i in range(5):
        monitor.check(float(i * 100))
    s = monitor.stats()
    assert "p50_ms" in s
    assert s["total_calls"] == 5
    assert s["exceeded_count"] == 0


def test_exceeded_count():
    monitor = LatencyMonitor(budget_ms=500.0, window_size=10)
    monitor.check(100.0)
    monitor.check(600.0)  # exceeded
    monitor.check(700.0)  # exceeded
    s = monitor.stats()
    assert s["exceeded_count"] == 2


def test_empty_stats():
    monitor = LatencyMonitor()
    s = monitor.stats()
    assert "error" in s


def test_window_size():
    monitor = LatencyMonitor(budget_ms=2000.0, window_size=3)
    for i in range(10):
        monitor.check(float(i))
    s = monitor.stats()
    assert s["total_calls"] == 10
    # Window should only hold the last 3
    assert s["min_ms"] >= 7.0

#!/usr/bin/env python3
"""
Latency monitoring and budget enforcement for the alert pipeline.

Tracks p50/p95/p99 latency and raises an alert if any single
call exceeds the budget (default 2000ms).

Usage:
    from src.alerting.latency_monitor import LatencyMonitor
    monitor = LatencyMonitor(budget_ms=2000.0)
    if monitor.check(elapsed_ms):
        print("Budget exceeded!")
    print(monitor.stats())
"""

import time
import statistics
from typing import Optional


class LatencyMonitor:
    """Tracks alert pipeline latency and enforces budget."""

    def __init__(self, budget_ms: float = 2000.0, window_size: int = 100):
        self.budget_ms = budget_ms
        self.window_size = window_size
        self._latencies: list[float] = []
        self._exceeded_count = 0
        self._total_calls = 0

    def check(self, elapsed_ms: float) -> bool:
        """Record a latency measurement and return True if budget exceeded."""
        self._latencies.append(elapsed_ms)
        self._total_calls += 1

        if len(self._latencies) > self.window_size:
            self._latencies.pop(0)

        if elapsed_ms > self.budget_ms:
            self._exceeded_count += 1
            return True
        return False

    def stats(self) -> dict:
        """Return latency statistics for the current window."""
        if not self._latencies:
            return {"error": "no data"}

        sorted_lat = sorted(self._latencies)
        n = len(sorted_lat)
        return {
            "p50_ms": round(sorted_lat[int(n * 0.50)], 1),
            "p95_ms": round(sorted_lat[int(n * 0.95)], 1),
            "p99_ms": round(sorted_lat[int(n * 0.99)], 1),
            "mean_ms": round(statistics.mean(sorted_lat), 1),
            "max_ms": round(max(sorted_lat), 1),
            "min_ms": round(min(sorted_lat), 1),
            "budget_ms": self.budget_ms,
            "exceeded_count": self._exceeded_count,
            "total_calls": self._total_calls,
        }

    def report(self) -> None:
        """Print latency report to stdout."""
        s = self.stats()
        if "error" in s:
            print(f"[LatencyMonitor] {s['error']}")
            return
        print(f"[LatencyMonitor] p50={s['p50_ms']}ms  "
              f"p95={s['p95_ms']}ms  p99={s['p99_ms']}ms  "
              f"max={s['max_ms']}ms  "
              f"exceeded={s['exceeded_count']}/{s['total_calls']}  "
              f"budget={s['budget_ms']}ms")

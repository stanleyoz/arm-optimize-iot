#!/usr/bin/env python3
"""
Hybrid alert engine orchestrator.

Pipeline:
  1. Receive SensorWindow
  2. Run threshold rules (fast path, <10ms)
  3. If threshold triggered, run LLM triage (slow path)
  4. Dispatch alert action
  5. Return AlertResult with timing breakdown

Usage:
    from src.alerting.alert_engine import AlertEngine
    engine = AlertEngine()
    result = engine.process(window)
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from src.data_processing.sensor_reader import SensorWindow

from .threshold_rules import ThresholdConfig, TriggeredRule, evaluate
from .llm_triage import LlmTriage
from .alert_actions import AlertLogger
from .latency_monitor import LatencyMonitor


@dataclass
class AlertResult:
    """Result from a single alert pipeline run."""
    alert: bool
    reason: str
    severity: str  # "low" | "medium" | "high"
    threshold_time_ms: float
    llm_time_ms: float
    total_time_ms: float
    triggered_rules: list[TriggeredRule] = field(default_factory=list)
    llm_raw: Optional[dict[str, Any]] = None
    latency_budget_exceeded: bool = False


class AlertEngine:
    """Orchestrates the hybrid threshold + LLM alert pipeline."""

    def __init__(
        self,
        model_path: str | Path = "models/qwen2-0.5b-q4_k_m.gguf",
        n_ctx: int = 1024,
        threshold_config: Optional[ThresholdConfig] = None,
        latency_budget_ms: float = 2000.0,
        log_file: str | Path = "alerts.log",
        verbose: bool = False,
    ):
        self.threshold_config = threshold_config or ThresholdConfig()
        self.latency_monitor = LatencyMonitor(budget_ms=latency_budget_ms)
        self.logger = AlertLogger(log_file)
        self.verbose = verbose

        self._n_ctx = n_ctx
        self._model_path = Path(model_path)

        # Eager-load LLM model at startup to avoid cold-start latency
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {self._model_path}. "
                "Run download_model.py and quantize_model.py first."
            )
        self._llm: LlmTriage = LlmTriage(self._model_path, n_ctx=self._n_ctx, verbose=self.verbose)

    def _get_llm(self) -> LlmTriage:
        return self._llm

    def process(self, window: SensorWindow) -> AlertResult:
        """Run the full alert pipeline on a sensor window."""
        start = time.perf_counter()

        # Step 1: Threshold rules (fast path)
        t0 = time.perf_counter()
        summary = window.summary()
        triggered = evaluate(summary, self.threshold_config)
        threshold_time = (time.perf_counter() - t0) * 1000

        if not triggered:
            elapsed = (time.perf_counter() - start) * 1000
            return AlertResult(
                alert=False,
                reason="No thresholds triggered",
                severity="low",
                threshold_time_ms=threshold_time,
                llm_time_ms=0.0,
                total_time_ms=elapsed,
                triggered_rules=[],
            )

        # Step 1.5: Skip LLM for low-severity-only triggers
        max_severity = max((r.severity for r in triggered), default="low")
        if max_severity == "low":
            elapsed = (time.perf_counter() - start) * 1000
            result = AlertResult(
                alert=True,
                reason=f"Low-severity threshold: {triggered[0].message}",
                severity="low",
                threshold_time_ms=threshold_time,
                llm_time_ms=0.0,
                total_time_ms=elapsed,
                triggered_rules=triggered,
            )
            result.latency_budget_exceeded = self.latency_monitor.check(elapsed)
            if result.alert:
                self.logger.log_alert(result)
            return result

        # Step 2: LLM triage (slow path, medium/high triggers only)
        t1 = time.perf_counter()
        try:
            llm = self._get_llm()
            llm_result = llm.analyze(window, triggered, max_tokens=25)
        except Exception as exc:
            llm_result = {
                "alert": True,
                "reason": f"LLM error: {exc}",
                "severity": "high",
            }
        llm_time = (time.perf_counter() - t1) * 1000

        alert = llm_result.get("alert", True)
        reason = llm_result.get("reason", "LLM triggered alert")
        severity = llm_result.get("severity", "medium")

        elapsed = (time.perf_counter() - start) * 1000

        result = AlertResult(
            alert=alert,
            reason=reason,
            severity=severity,
            threshold_time_ms=threshold_time,
            llm_time_ms=llm_time,
            total_time_ms=elapsed,
            triggered_rules=triggered,
            llm_raw=llm_result,
        )

        # Step 3: Latency monitoring
        result.latency_budget_exceeded = self.latency_monitor.check(elapsed)

        # Step 4: Dispatch alert action
        if alert:
            self.logger.log_alert(result)

        return result

    def close(self) -> None:
        if self._llm is not None:
            self._llm.close()
        self.latency_monitor.report()


def main() -> None:
    """Run a quick demo of the alert engine on sample data."""
    import sys
    from src.data_processing.sensor_generator import generate_sensor_data
    from src.data_processing.sensor_reader import SensorReader

    # Generate sample data
    print("Generating sample sensor data (1 hour, 1s interval)...")
    rows = generate_sensor_data(hours=1, seed=99)
    csv_path = Path("data/demo_data.csv")
    csv_path.parent.mkdir(exist_ok=True)
    import csv as csv_module
    fieldnames = [
        "timestamp", "temperature_C", "humidity_pct", "people_count",
        "time_spent_sec", "alarm_status", "is_anomaly", "anomaly_type",
    ]
    with open(csv_path, "w", newline="") as f:
        writer = csv_module.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {csv_path}")

    reader = SensorReader(str(csv_path))
    engine = AlertEngine(verbose=False)

    print("\nProcessing windows (every 30s)...")
    thresholds_triggered = 0
    alerts_issued = 0
    total_windows = 0

    for window in reader.stream(window_s=30, step_s=30):
        result = engine.process(window)
        total_windows += 1
        if result.triggered_rules:
            thresholds_triggered += 1
        if result.alert:
            alerts_issued += 1
            print(f"\n  ALERT at {window.end_time.isoformat()}")
            print(f"    Reason: {result.reason}")
            print(f"    Severity: {result.severity}")
            print(f"    Threshold: {result.threshold_time_ms:.1f}ms, "
                  f"LLM: {result.llm_time_ms:.1f}ms, "
                  f"Total: {result.total_time_ms:.1f}ms")

    print(f"\nSummary: {total_windows} windows, "
          f"{thresholds_triggered} threshold triggers, "
          f"{alerts_issued} alerts")
    print(f"Latency stats: {engine.latency_monitor.stats()}")
    engine.close()


if __name__ == "__main__":
    main()

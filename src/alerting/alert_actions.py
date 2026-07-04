#!/usr/bin/env python3
"""
Alert action dispatchers.

Currently supports:
  - AlertLogger: writes alerts to log file (JSONL format)
  - GPIO stub: ready for future hardware integration

Usage:
    from src.alerting.alert_actions import AlertLogger
    logger = AlertLogger("alerts.log")
    logger.log_alert(result)
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class AlertLogger:
    """Write alerts to a JSONL log file."""

    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None

    def _open(self):
        if self._file is None:
            self._file = open(self.log_path, "a")

    def log_alert(self, result) -> None:
        """Log an alert result to file."""
        self._open()
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "alert": result.alert,
            "reason": result.reason,
            "severity": result.severity,
            "threshold_time_ms": round(result.threshold_time_ms, 1),
            "llm_time_ms": round(result.llm_time_ms, 1),
            "total_time_ms": round(result.total_time_ms, 1),
            "triggered_rules": [r.name for r in result.triggered_rules],
        }
        print(f"[ALERT] {result.severity.upper()}: {result.reason}")
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

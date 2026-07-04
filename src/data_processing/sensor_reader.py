#!/usr/bin/env python3
"""
Unified sensor data reader supporting CSV, JSON, and SQLite3 formats.

Produces SensorWindow dataclasses representing rolling windows of sensor data.

Usage:
    from src.data_processing.sensor_reader import SensorReader, SensorWindow

    reader = SensorReader("data/sensor_data.csv")
    window = reader.window(seconds=30)   # last 30 seconds
    for w in reader.stream(window_s=30, step_s=1):
        process(w)
"""

import csv
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator, Iterator, Optional


@dataclass
class SensorWindow:
    """A sliding window of sensor readings."""
    start_time: datetime
    end_time: datetime
    readings: list[dict] = field(default_factory=list)

    def to_prompt(self) -> str:
        """Format window as a compact text block for LLM prompts."""
        if not self.readings:
            return "No sensor data available."

        lines = []
        for r in self.readings[-5:]:  # last 5 readings
            lines.append(
                f"{r['timestamp']}  "
                f"temp={r['temperature_C']}C  "
                f"humid={r['humidity_pct']}%  "
                f"people={r['people_count']}  "
                f"spent={r['time_spent_sec']}s  "
                f"alarm={r['alarm_status']}"
            )
        return "\n".join(lines)

    def summary(self) -> dict:
        """Aggregate statistics over the window."""
        if not self.readings:
            return {}
        temps = [r["temperature_C"] for r in self.readings]
        hums = [r["humidity_pct"] for r in self.readings]
        people = [r["people_count"] for r in self.readings]
        return {
            "temp_min": round(min(temps), 1),
            "temp_max": round(max(temps), 1),
            "temp_avg": round(sum(temps) / len(temps), 1),
            "humidity_min": round(min(hums), 1),
            "humidity_max": round(max(hums), 1),
            "humidity_avg": round(sum(hums) / len(hums), 1),
            "people_max": max(people),
            "people_avg": round(sum(people) / len(people), 1),
            "reading_count": len(self.readings),
        }


class SensorReader:
    """Read sensor data from various formats."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: list[dict] = []
        self._load()

    def _load(self) -> None:
        suffix = self.path.suffix.lower()
        if suffix == ".csv":
            self._load_csv()
        elif suffix == ".json":
            self._load_json()
        elif suffix in (".sqlite", ".sqlite3", ".db"):
            self._load_sqlite()
        else:
            raise ValueError(f"Unsupported format: {suffix}")

    def _load_csv(self) -> None:
        with open(self.path, newline="") as f:
            reader = csv.DictReader(f)
            self._data = [self._normalize(row) for row in reader]

    def _load_json(self) -> None:
        with open(self.path) as f:
            raw = json.load(f)
            self._data = [self._normalize(r) for r in raw]

    def _load_sqlite(self) -> None:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM sensor_data ORDER BY timestamp ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self._data = [self._normalize(r) for r in rows]

    def _normalize(self, row: dict) -> dict:
        """Ensure all sensor reading dicts have consistent types and keys."""
        return {
            "timestamp": str(row.get("timestamp", "")),
            "temperature_C": float(row.get("temperature_C", row.get("temperature", 0))),
            "humidity_pct": float(row.get("humidity_pct", row.get("humidity", 0))),
            "people_count": int(row.get("people_count", row.get("people", 0))),
            "time_spent_sec": int(row.get("time_spent_sec", row.get("time_spent", 0))),
            "alarm_status": int(row.get("alarm_status", row.get("alarm", 0))),
        }

    def _parse_ts(self, row: dict) -> datetime:
        """Parse the timestamp field, which may be ISO format or Unix epoch."""
        ts = row["timestamp"]
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            pass
        try:
            return datetime.fromtimestamp(float(ts))
        except (ValueError, TypeError):
            pass
        raise ValueError(f"Cannot parse timestamp: {ts}")

    def latest(self) -> Optional[dict]:
        """Return the most recent reading."""
        return self._data[-1] if self._data else None

    def window(self, seconds: int = 30) -> SensorWindow:
        """Return a SensorWindow covering the last N seconds."""
        if not self._data:
            return SensorWindow(datetime.min, datetime.min)

        end = self._parse_ts(self._data[-1])
        start = end - timedelta(seconds=seconds)
        readings = [
            r for r in self._data
            if self._parse_ts(r) >= start
        ]
        return SensorWindow(start_time=start, end_time=end, readings=readings)

    def stream(
        self,
        window_s: int = 30,
        step_s: int = 1,
    ) -> Generator[SensorWindow, None, None]:
        """Yield a sliding window over the data, stepping by step_s seconds."""
        if not self._data:
            return

        times = [self._parse_ts(r) for r in self._data]
        t_start = times[0]
        t_end = times[-1]

        cursor = 0
        current = t_start
        while current <= t_end:
            window_end = current + timedelta(seconds=window_s)
            window_start = current

            # Advance cursor to include new readings
            readings = []
            for i in range(cursor, len(self._data)):
                if times[i] >= window_end:
                    break
                if times[i] >= window_start:
                    readings.append(self._data[i])
                    cursor = i

            yield SensorWindow(
                start_time=window_start,
                end_time=window_end,
                readings=readings,
            )
            current += timedelta(seconds=step_s)

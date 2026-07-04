#!/usr/bin/env python3
"""
Fast rule-based threshold checks for sensor data.

Runs in <10ms — serves as the first-pass filter before LLM triage.

Usage:
    from src.alerting.threshold_rules import ThresholdConfig, evaluate
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ThresholdConfig:
    """Configurable sensor thresholds."""
    temp_min: float = 0.0
    temp_max: float = 40.0
    humidity_min: float = 10.0
    humidity_max: float = 90.0
    people_max: int = 10
    temp_rise_rate: float = 5.0       # max C per 60s before alert
    humidity_rise_rate: float = 15.0  # max % per 60s before alert


@dataclass
class TriggeredRule:
    """A rule that was triggered by a sensor reading."""
    name: str
    value: float
    threshold: float
    severity: str  # "low" | "medium" | "high"
    message: str


def evaluate(window_summary: dict, config: Optional[ThresholdConfig] = None) -> list[TriggeredRule]:
    """Evaluate threshold rules against a sensor window summary.

    Returns a list of triggered rules (empty list = no alert).
    """
    if config is None:
        config = ThresholdConfig()

    triggered: list[TriggeredRule] = []

    temp_max = window_summary.get("temp_max", 0)
    temp_min = window_summary.get("temp_min", 0)
    humid_max = window_summary.get("humidity_max", 0)
    humid_min = window_summary.get("humidity_min", 0)
    people_max = window_summary.get("people_max", 0)

    if temp_max > config.temp_max:
        triggered.append(TriggeredRule(
            name="temp_high",
            value=temp_max,
            threshold=config.temp_max,
            severity="high" if temp_max > config.temp_max + 10 else "medium",
            message=f"Temperature {temp_max}C exceeds {config.temp_max}C",
        ))

    if temp_min < config.temp_min:
        triggered.append(TriggeredRule(
            name="temp_low",
            value=temp_min,
            threshold=config.temp_min,
            severity="medium",
            message=f"Temperature {temp_min}C below {config.temp_min}C",
        ))

    if humid_max > config.humidity_max:
        triggered.append(TriggeredRule(
            name="humidity_high",
            value=humid_max,
            threshold=config.humidity_max,
            severity="medium",
            message=f"Humidity {humid_max}% exceeds {config.humidity_max}%",
        ))

    if humid_min < config.humidity_min:
        triggered.append(TriggeredRule(
            name="humidity_low",
            value=humid_min,
            threshold=config.humidity_min,
            severity="low",
            message=f"Humidity {humid_min}% below {config.humidity_min}%",
        ))

    if people_max > config.people_max:
        triggered.append(TriggeredRule(
            name="people_high",
            value=people_max,
            threshold=config.people_max,
            severity="low",
            message=f"People count {people_max} exceeds {config.people_max}",
        ))

    return triggered

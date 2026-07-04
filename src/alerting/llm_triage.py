#!/usr/bin/env python3
"""
LLM-based triage for sensor windows using llama-cpp-python (1 thread).

Uses 1 thread to avoid Python GIL contention that makes multi-thread
inference slower. Model stays loaded in process memory between calls
(no cold-start overhead).

Usage:
    from src.alerting.llm_triage import LlmTriage
    triage = LlmTriage(model_path="models/qwen2-0.5b-q4_k_m.gguf")
    result = triage.analyze(window, triggered_rules)
"""

import json
from pathlib import Path
from typing import Any, Optional

from llama_cpp import Llama

from src.data_processing.sensor_reader import SensorWindow
from .threshold_rules import TriggeredRule


FEW_SHOT_EXAMPLES = """temp=45C,humid=30%,people=3
{"alert": true, "reason": "Temperature 45C is very high and room is occupied", "severity": "high"}

temp=22C,humid=50%,people=0
{"alert": false, "reason": "All readings normal, room empty", "severity": "low"}

temp=28C,humid=85%,people=2
{"alert": true, "reason": "Humidity 85% is very high, comfort risk", "severity": "medium"}

temp=10C,humid=40%,people=1
{"alert": false, "reason": "Temperature 10C is cool but within acceptable range", "severity": "low"}

temp=38C,humid=55%,people=5
{"alert": true, "reason": "Temperature 38C is high and room has 5 people, overheating risk", "severity": "high"}

temp=30C,humid=65%,people=1
{"alert": false, "reason": "Temperature 30C is warm but acceptable with low occupancy", "severity": "low"}
"""


class LlmTriage:
    """LLM triage engine using llama-cpp-python (1 thread for optimal perf)."""

    def __init__(
        self,
        model_path: str | Path,
        n_ctx: int = 512,
        verbose: bool = False,
    ):
        self.model_path = Path(model_path)
        self.llm = Llama(
            model_path=str(self.model_path),
            n_ctx=n_ctx,
            n_threads=1,  # 1 thread avoids GIL contention on ARM
            verbose=verbose,
        )
        self._warmup()

    def _warmup(self) -> None:
        self.llm(
            f"{FEW_SHOT_EXAMPLES}temp=25C,humid=50%,people=1\n{{\"alert\":",
            max_tokens=5,
            temperature=0.0,
            echo=False,
        )

    def _build_prompt(
        self,
        window: SensorWindow,
        triggered_rules: list[TriggeredRule],
    ) -> str:
        summary = window.summary()
        sensor_str = (
            f"temp={summary['temp_max']}C,humid={summary['humidity_max']}%,"
            f"people={summary['people_max']}"
        )
        return (
            f"{FEW_SHOT_EXAMPLES}"
            f"{sensor_str}\n"
            f"{{\"alert\":"
        )

    def analyze(
        self,
        window: SensorWindow,
        triggered_rules: list[TriggeredRule],
        temperature: float = 0.0,
        max_tokens: int = 20,
    ) -> dict[str, Any]:
        """Run LLM triage on a sensor window.

        Returns parsed JSON with keys: alert, reason, severity.
        Falls back to a safe default if JSON parsing fails.
        """
        prompt = self._build_prompt(window, triggered_rules)
        output = self.llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            echo=False,
        )

        text = output.get("choices", [{}])[0].get("text", "").strip()
        full_json = '{"alert":' + text
        brace_depth = 0
        json_end = -1
        for i, ch in enumerate(full_json):
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
                if brace_depth == 0:
                    json_end = i + 1
                    break
        if json_end > 0:
            try:
                result = json.loads(full_json[:json_end])
                result.setdefault("alert", False)
                result.setdefault("reason", "No reason provided")
                result.setdefault("severity", "low")
                return result
            except json.JSONDecodeError:
                pass

        # Attempt partial JSON extraction before falling back
        partial = self._extract_partial_json(text)
        if partial:
            return partial

        if len(triggered_rules) >= 2:
            return {
                "alert": True,
                "reason": f"Multiple thresholds triggered ({len(triggered_rules)} rules). LLM output: {text[:100]}",
                "severity": "medium",
            }
        return {
            "alert": False,
            "reason": f"Threshold triggered ({triggered_rules[0].name}) but LLM output malformed. Conservative no-alert.",
            "severity": "low",
        }

    def _extract_partial_json(self, text: str) -> dict | None:
        """Try to extract alert/reason/severity from a truncated JSON fragment."""
        import re
        alert_m = re.search(r'"alert"\s*:\s*(true|false)', text, re.IGNORECASE)
        reason_m = re.search(r'"reason"\s*:\s*"([^"]*)"', text, re.IGNORECASE)
        severity_m = re.search(r'"severity"\s*:\s*"(low|medium|high)"', text, re.IGNORECASE)
        if alert_m:
            return {
                "alert": alert_m.group(1).lower() == "true",
                "reason": reason_m.group(1) if reason_m else "No reason provided",
                "severity": severity_m.group(1) if severity_m else "medium",
            }
        return None

    def close(self) -> None:
        pass

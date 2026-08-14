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


# Reasons are deliberately terse. A complete verdict has to fit inside the token
# budget that keeps us under 2s on a Cortex-A76 — verbose examples teach the model
# to write long reasons, which then get truncated mid-object and never parse.
# Examples are calibrated to the deployment envelope, not to room temperature.
# This is a chilled retail space: ~13C and ~70% RH are NORMAL here. Office-calibrated
# examples (45C critical, 22C normal) make the model read every window as alarming.
#
# Readings are passed as min/max pairs. Maxima alone are not sufficient: the -99.9C
# sensor-fault sentinel lands in the MINIMUM, so a max-only prompt cannot see a fault
# at all. Each example below corresponds to one anomaly type the generator produces
# (temp_spike, humidity_spike, people_surge, sensor_fault) plus normal baselines.
FEW_SHOT_EXAMPLES = """temp=12.8/13.4C,humid=68/72%,people=2
{"alert":false,"reason":"normal cold room","severity":"low"}

temp=-99.9/13.2C,humid=0/70%,people=1
{"alert":true,"reason":"sensor fault, invalid reading","severity":"high"}

temp=13.0/34.4C,humid=65/71%,people=3
{"alert":true,"reason":"temp spike 34C, cold chain risk","severity":"high"}

temp=13.1/13.9C,humid=70/100%,people=2
{"alert":true,"reason":"humidity spike 100%","severity":"high"}

temp=13.2/15.1C,humid=69/75%,people=28
{"alert":true,"reason":"28 people, crowding","severity":"medium"}

temp=12.9/13.6C,humid=66/70%,people=0
{"alert":false,"reason":"normal, empty","severity":"low"}
"""

# The completion is primed with this, so the model only ever emits the remainder.
# Both the prompt suffix and the parser need it, so it lives in one place.
JSON_PREFIX = '{"alert":'


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
        # Uses the full few-shot prompt on purpose: llama.cpp defers some internal
        # allocations until it sees a realistic workload, so a trivial warmup string
        # leaves that cost sitting in the first real request.
        self.llm(
            f"{FEW_SHOT_EXAMPLES}temp=25C,humid=50%,people=1\n{JSON_PREFIX}",
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
        # min/max pairs, matching FEW_SHOT_EXAMPLES. The minima matter: sensor faults
        # only ever show up there.
        sensor_str = (
            f"temp={summary['temp_min']}/{summary['temp_max']}C,"
            f"humid={summary['humidity_min']}/{summary['humidity_max']}%,"
            f"people={summary['people_max']}"
        )
        return (
            f"{FEW_SHOT_EXAMPLES}"
            f"{sensor_str}\n"
            f"{JSON_PREFIX}"
        )

    def analyze(
        self,
        window: SensorWindow,
        triggered_rules: list[TriggeredRule],
        temperature: float = 0.0,
        max_tokens: int = 25,
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
            stop=["}"],  # verdict is complete at the closing brace; stop early
        )

        text = output.get("choices", [{}])[0].get("text", "").strip()
        # `stop` consumes the brace that terminated generation, so put it back.
        if not text.endswith("}"):
            text += "}"
        full_json = JSON_PREFIX + text
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

        # Attempt partial JSON extraction before falling back. This must be given
        # the prefixed string: the `"alert"` key lives in the prompt, not the
        # completion, so matching against the raw completion can never succeed.
        partial = self._extract_partial_json(full_json)
        if partial:
            return partial

        if len(triggered_rules) >= 2:
            rules = ", ".join(r.name for r in triggered_rules)
            return {
                "alert": True,
                "reason": f"{len(triggered_rules)} thresholds triggered ({rules}); LLM verdict unparseable",
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

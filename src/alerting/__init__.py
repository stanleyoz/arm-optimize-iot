# Hybrid alert engine for real-time sensor triage.
# - threshold_rules.py: Fast rule-based checks (<10ms)
# - llm_triage.py: Qwen2-0.5B inference via native llama-cli subprocess
# - alert_engine.py: Orchestrates threshold + LLM pipeline
# - alert_actions.py: Alert dispatch (log, notify, GPIO)
# - latency_monitor.py: Sub-2s p99 latency enforcement

#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

source venv/bin/activate

echo "========================================"
echo "  ARM AI Optimization — Benchmark Suite"
echo "========================================"
echo ""

# ------------------------------------------------------------------
# 1. Generate sensor data
# ------------------------------------------------------------------
echo "[1/5] Generating sensor data (24h @ 1s interval) ..."
python -m src.data_processing.sensor_generator \
    --hours 24 \
    --output data/benchmark_data.csv \
    --seed 42
echo ""

# ------------------------------------------------------------------
# 2. Check for model
# ------------------------------------------------------------------
echo "[2/5] Checking model ..."
MODEL_Q4="models/qwen2-0.5b-q4_k_m.gguf"
MODEL_FP16="models/qwen2-0.5b-fp16.gguf"

if [ ! -f "$MODEL_Q4" ] && [ ! -f "$MODEL_FP16" ]; then
    echo "  No model found. Run the pipeline:"
    echo "    python -m src.model_optimization.optimize_model"
    echo "  or download + quantize manually."
    echo "  Skipping model benchmarks."
    HAS_MODEL=false
else
    HAS_MODEL=true
fi
echo ""

# ------------------------------------------------------------------
# 3. Model benchmarks (if model available)
# ------------------------------------------------------------------
if [ "$HAS_MODEL" = true ]; then
    echo "[3/5] Running model benchmarks ..."
    python -m src.model_optimization.benchmark
    echo ""
fi

# ------------------------------------------------------------------
# 4. Unit tests
# ------------------------------------------------------------------
echo "[4/5] Running unit tests ..."
python -m pytest tests/ -v --tb=short
echo ""

# ------------------------------------------------------------------
# 5. Alert pipeline demo (data only, no LLM unless model exists)
# ------------------------------------------------------------------
echo "[5/5] Running alert pipeline demo ..."
if [ "$HAS_MODEL" = true ]; then
    python -m src.alerting.alert_engine
else
    echo "  Skipping LLM demo (model not found)."
    echo "  Running data-only validation ..."
    python -c "
from src.data_processing.sensor_reader import SensorReader
from src.alerting.threshold_rules import evaluate
from src.alerting.latency_monitor import LatencyMonitor

reader = SensorReader('data/benchmark_data.csv')
monitor = LatencyMonitor(budget_ms=2000.0)
triggered = 0
total = 0

for w in reader.stream(window_s=30, step_s=30):
    total += 1
    rules = evaluate(w.summary())
    if rules:
        triggered += 1

print(f'  Windows processed: {total}')
print(f'  Threshold triggers: {triggered} ({100*triggered/total:.1f}%)')
"
fi

echo ""
echo "========================================"
echo "  Benchmark complete"
echo "========================================"

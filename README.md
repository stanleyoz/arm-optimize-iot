# ARM AI Optimization Challenge — Hybrid Edge LLM for Sensor Triage

**Track:** Track 1 — Physical AI (On-Device Edge AI)

**Base Model:** Qwen2-0.5B → GGUF Q4_K_M (380 MB)  
**Inference Engine:** llama.cpp built from source with NEON for Cortex-A76  
**Target Device:** Raspberry Pi 5 (4× Cortex-A76 @ 2.4 GHz, 8 GB RAM)  
**Pipeline:** Threshold rules (<0.1ms) → LLM triage (Qwen2-0.5B, ~1.1s) → JSON alert

**Key Result:** p99 LLM triage latency **1,359 ms** — 41/41 LLM calls under the 2-second budget, 0 exceeded, 41/41 producing valid JSON.

**Measured on the target device**, not estimated: every number below comes from a run on a
Raspberry Pi 5 over 4 hours of sensor data. See [`capture/`](capture/) for the raw logs.

---

## Architecture

```
[Sensor CSV stream] → [30s sliding window] → [Threshold rules: <0.1ms]
                                                    │
                                          425/480 pass → No alert
                                                    │
                                            55/480 trigger
                                                    │
                                         ┌──────────┴──────────┐
                                         │ severity = "low"    │
                                         │ (people count only) │
                                         │ → Alert directly    │  14 windows
                                         └─────────────────────┘
                                                    │
                                         medium/high severity      41 windows
                                                    │
                                         [LLM Triage: ~1.1s]
                                                    │
                                    grades severity + writes reason
                                    (does NOT veto — see accuracy)
                                                    │
                                         [JSON verdict: 41/41 valid]
                                                    │
                                         [AlertLogger: log/GPIO]
```

## Quick Start

```bash
git clone <repo> && cd arm-optimize-iot
./setup.sh                                    # Build env + llama.cpp
source venv/bin/activate
python -m src.model_optimization.download_model  # Get Qwen2-0.5B Q4_K_M
python -m src.data_processing.sensor_generator   # Generate test data
python -m src.alerting.alert_engine              # Run pipeline
./benchmark.sh                                   # Full benchmark suite
```

## Optimization Summary

| Optimization | Before | After | Gain |
|---|---|---|---|
| FP16 → Q4_K_M quantization | 949 MB / 949 MB RAM | 380 MB / 297 MB RAM | 2.5× memory reduction |
| GIL-aware `n_threads=1` | 4.0 tok/s (4 threads) | 15.1 tok/s (1 thread) | 3.8× generation speed |
| `max_tokens=128` → 25 | ~8.5s per call | ~1.6s per call | 5.3× per-call reduction |
| Lazy load → eager + warmup | 5,833 ms p99 | 1,825 ms p99 | 3.2× cold-start elimination |
| Terse few-shot + `}` stop token | 1,825 ms p99 | 1,359 ms p99 | 1.3× — and fixed truncated JSON |
| Hybrid pipeline gate | 1,127 ms avg per window | 96 ms effective avg | 11.7× system-level |
| Generic pip → native NEON build | 4.0 tok/s | 28.4 tok/s (4T native) | 7× prompt processing |

## Benchmark Results (Raspberry Pi 5)

Run: 4 hours of synthetic sensor data (seed 99), 30 s windows / 30 s step → 480 windows,
of which **55 crossed a threshold** and **41 escalated to the LLM** (the other 14 were
low-severity and took the sub-0.1 ms fast path).

| Metric | Threshold Check | LLM Triage | Total per Alert |
|---|---|---|---|
| p50 | <0.1 ms | 1,107 ms | 1,107 ms |
| p95 | <0.1 ms | 1,215 ms | 1,215 ms |
| **p99** | **<0.1 ms** | **1,359 ms** | **1,359 ms** |
| Max | 0.05 ms | 1,359 ms | 1,359 ms |
| Calls | 55 triggered windows | 41 LLM calls | 55 alerts |
| Budget exceeded (2,000 ms) | 0/55 | 0/41 | **0/41** |
| Valid JSON | — | **41/41** | — |

Because the threshold gate absorbs 88% of windows, the **effective average cost is 96 ms
per window** across the whole run.

## Detection Accuracy — and an honest negative result

Scored against the generator's ground-truth anomaly labels over the same 480 windows:

| Layer | Precision | Recall | F1 |
|---|---|---|---|
| Threshold rules only | 0.982 | 0.692 | 0.812 |
| Hybrid (thresholds + LLM) | 0.982 | 0.692 | 0.812 |

**The LLM does not improve detection accuracy, and we measured rather than assumed that.**
When we let the model veto a threshold hit, recall fell from 0.692 to 0.500 (F1 0.812 →
0.661): a 0.5B model at 4-bit is a worse detector than six tuned rules. So the model is
not wired as a filter. The threshold layer owns the alert decision; the LLM grades
severity and writes the human-readable reason, which it does within budget and with 100%
JSON validity. Wiring it the flattering way would have cost 28% of recall.

## Project Structure

```
src/
  alerting/          # Core pipeline: threshold_rules, llm_triage, alert_engine
  data_processing/   # sensor_generator, sensor_reader (CSV/JSON/SQLite)
  model_optimization/# download, export, quantize, benchmark
tests/               # 34 unit tests, all passing
docs/                # benchmark_results, process_report, rpi5_deployment
submission/          # Devpost submission write-up
setup.sh             # One-command environment + llama.cpp build
benchmark.sh         # Automated benchmark suite
LICENSE              # Apache 2.0
```

## Key Technical Decisions

1. **Qwen2-0.5B** at Q4_K_M — smallest size with reliable JSON output; 380 MB fits Pi 5 RAM
2. **Few-shot completion** instead of instruction prompting — 100% JSON compliance at 4-bit (instruction mode fails at this quantization level)
3. **Terse few-shot reasons** — the token budget that keeps us under 2 s only fits a short
   verdict. Verbose examples teach the model to write long reasons that get truncated
   mid-object and never parse, so example length is a latency parameter, not a style choice.
4. **`n_threads=1`** in llama-cpp-python — Python GIL makes multi-thread 3.8× slower than single-thread on ARM small cores
5. **Eager load + model warmup** — eliminates 5.8s cold-start outlier; warmup uses full few-shot prompt to trigger llama.cpp's internal allocations
6. **Hybrid architecture** — threshold rules filter 88% of windows in <0.1ms; low-severity bypass skips another 14 of 55 potential LLM calls
7. **Prompt carries min *and* max** — the `-99.9` sensor-fault sentinel lands in the
   minimum, so a max-only prompt is structurally blind to faults. Fixing this took
   sensor-fault detection from 2/26 to 24/26.
8. **Rules own the decision, the model explains it** — see the accuracy section; letting
   the model veto a threshold hit costs 28% of recall.

## Documentation

- [`submission/SUBMISSION.md`](submission/SUBMISSION.md) — Full Devpost submission write-up with setup instructions
- [`docs/benchmark_results.md`](docs/benchmark_results.md) — Detailed benchmark data and methodology
- [`docs/process_report.md`](docs/process_report.md) — Decision log and implementation notes
- [`docs/rpi5_deployment.md`](docs/rpi5_deployment.md) — RPi 5 deployment guide with systemd service

## License

Apache 2.0 — see [`LICENSE`](LICENSE).

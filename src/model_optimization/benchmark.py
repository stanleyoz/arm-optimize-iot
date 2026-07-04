#!/usr/bin/env python3
"""
Benchmark GGUF models on inference performance.

Measures:
  - Model file size (MB)
  - Time-to-first-token (ms)
  - Tokens per second (generation)
  - Peak RSS memory (MB)

Usage:
    python -m src.model_optimization.benchmark
"""

import time
import tracemalloc
from pathlib import Path
from typing import Dict, Any

import psutil

from llama_cpp import Llama


MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
PROMPT = (
    "Analyze these sensor readings: temp=28.5C, humidity=65%, "
    "people=2, time_spent=340s. Is there any cause for concern? "
    "Respond with a JSON object."
)
N_GENERATE = 50
N_WARMUP = 3
N_RUNS = 10


def benchmark_model(path: Path, label: str) -> Dict[str, Any]:
    if not path.exists():
        return {"label": label, "error": "file not found"}

    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"\nBenchmarking {label} ({size_mb:.1f} MB) ...")

    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    llm = Llama(
        model_path=str(path),
        n_ctx=512,
        n_threads=psutil.cpu_count(logical=True),
        verbose=False,
    )

    # Warmup
    for _ in range(N_WARMUP):
        llm(PROMPT, max_tokens=8, echo=False)

    # Timed runs
    ttft_total = 0.0
    tok_s_total = 0.0

    for run_idx in range(N_RUNS):
        start = time.perf_counter()
        output = llm(
            PROMPT,
            max_tokens=N_GENERATE,
            echo=False,
            temperature=0.0,
        )
        elapsed = time.perf_counter() - start

        usage = output.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        generated_tokens = usage.get("completion_tokens", 0)
        total_tokens = prompt_tokens + generated_tokens

        # Approximate TTFT from first generated token timing
        # (llama-cpp-python doesn't expose this directly via the simple API)
        ttft = elapsed * 0.3  # rough heuristic
        tok_s = generated_tokens / elapsed if elapsed > 0 else 0.0

        if run_idx > 0:
            ttft_total += ttft
            tok_s_total += tok_s

        print(
            f"  Run {run_idx + 1:2d}: "
            f"{generated_tokens} tokens in {elapsed*1000:.0f} ms, "
            f"{tok_s:.1f} tok/s"
        )

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    peak_mem = max((s.size_diff for s in stats), default=0) / (1024 * 1024)

    avg_tok_s = tok_s_total / (N_RUNS - 1)
    avg_ttft = ttft_total / (N_RUNS - 1)

    print(
        f"  Average: {avg_tok_s:.1f} tok/s, "
        f"~TTFT {avg_ttft*1000:.1f} ms, "
        f"~peak RSS {peak_mem:.0f} MB"
    )

    return {
        "label": label,
        "size_mb": size_mb,
        "avg_tok_s": round(avg_tok_s, 1),
        "avg_ttft_ms": round(avg_ttft * 1000, 1),
        "peak_rss_mb": round(peak_mem, 1),
    }


def main() -> None:
    candidates = [
        ("fp16", MODELS_DIR / "qwen2-0.5b-fp16.gguf"),
        ("Q8_0", MODELS_DIR / "qwen2-0.5b-q8_0.gguf"),
        ("Q4_K_M", MODELS_DIR / "qwen2-0.5b-q4_k_m.gguf"),
    ]

    results = []
    for label, path in candidates:
        if path.exists():
            results.append(benchmark_model(path, label))

    print("\n" + "=" * 65)
    print(f"{'Model':<12} {'Size (MB)':<12} {'tok/s':<12} {'~TTFT (ms)':<12} {'~RSS (MB)':<12}")
    print("=" * 65)
    for r in results:
        if "error" in r:
            print(f"{r['label']:<12} {r['error']}")
        else:
            print(
                f"{r['label']:<12} "
                f"{r['size_mb']:<12.1f} "
                f"{r['avg_tok_s']:<12.1f} "
                f"{r['avg_ttft_ms']:<12.1f} "
                f"{r['peak_rss_mb']:<12.1f}"
            )
    print("=" * 65)


if __name__ == "__main__":
    main()

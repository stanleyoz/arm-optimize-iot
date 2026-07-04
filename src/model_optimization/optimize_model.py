#!/usr/bin/env python3
"""
Orchestrate the full model optimization pipeline:

    download --> convert to GGUF --> quantize --> benchmark

Usage:
    python -m src.model_optimization.optimize_model [--steps DOWNLOAD,CONVERT,QUANTIZE,BENCHMARK]
"""

import argparse
import sys
import subprocess
from pathlib import Path


MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "Qwen/Qwen2-0.5B"
GGUF_FP16 = MODELS_DIR / "qwen2-0.5b-fp16.gguf"
GGUF_Q4 = MODELS_DIR / "qwen2-0.5b-q4_k_m.gguf"


def run_step(script: str, step_name: str) -> None:
    print(f"\n{'='*60}")
    print(f"  Step: {step_name}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, "-m", f"src.model_optimization.{script}"],
        cwd=Path(__file__).resolve().parents[2],
    )
    if result.returncode != 0:
        print(f"  FAILED: {step_name}")
        sys.exit(result.returncode)
    print(f"  OK: {step_name}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Full model optimization pipeline")
    parser.add_argument(
        "--steps",
        default="DOWNLOAD,CONVERT,QUANTIZE,BENCHMARK",
        help="Comma-separated steps to run (default: all)",
    )
    args = parser.parse_args()

    steps = [s.strip().upper() for s in args.steps.split(",")]

    pipeline = {
        "DOWNLOAD": ("download_model", "Download model from Hugging Face"),
        "CONVERT": ("export_to_gguf", "Convert HF model to GGUF fp16"),
        "QUANTIZE": ("quantize_model", "Quantize GGUF to Q4_K_M"),
        "BENCHMARK": ("benchmark", "Run inference benchmarks"),
    }

    for key in steps:
        if key not in pipeline:
            print(f"Unknown step: {key}. Valid: {', '.join(pipeline)}")
            sys.exit(1)
        script, name = pipeline[key]
        run_step(script, name)

    print("Pipeline complete.")
    print(f"  FP16  model: {GGUF_FP16}")
    print(f"  Q4_K_M model: {GGUF_Q4}")


if __name__ == "__main__":
    main()

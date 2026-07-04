#!/usr/bin/env python3
"""
Quantize a GGUF fp16 model to Q4_K_M (and optionally Q8_0) using llama-quantize.

Usage:
    python -m src.model_optimization.quantize_model
"""

import subprocess
import sys
from pathlib import Path


MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
GGUF_FP16 = MODELS_DIR / "qwen2-0.5b-fp16.gguf"
LLAMA_QUANTIZE = (
    Path(__file__).resolve().parents[2] / "bin" / "llama-quantize"
)

QUANT_TYPES = [
    ("Q4_K_M", MODELS_DIR / "qwen2-0.5b-q4_k_m.gguf"),
    ("Q8_0", MODELS_DIR / "qwen2-0.5b-q8_0.gguf"),
]


def main() -> None:
    if not GGUF_FP16.exists():
        print(f"FP16 model not found at {GGUF_FP16}. Run export_to_gguf.py first.")
        sys.exit(1)

    if not LLAMA_QUANTIZE.exists():
        print(f"llama-quantize not found at {LLAMA_QUANTIZE}. Build llama.cpp first.")
        sys.exit(1)

    for qtype, out_path in QUANT_TYPES:
        if out_path.exists():
            print(f"{qtype} already exists at {out_path}, skipping.")
            continue

        print(f"Quantizing to {qtype} --> {out_path} ...")
        subprocess.check_call(
            [str(LLAMA_QUANTIZE), str(GGUF_FP16), str(out_path), qtype]
        )
        size_mb = out_path.stat().st_size / (1024 * 1024)
        fp16_mb = GGUF_FP16.stat().st_size / (1024 * 1024)
        ratio = size_mb / fp16_mb
        print(f"  Done — {size_mb:.1f} MB ({ratio:.1%} of fp16)")

    print("\nSummary:")
    for qtype, out_path in QUANT_TYPES:
        if out_path.exists():
            print(f"  {qtype:8s}  {out_path.stat().st_size / (1024*1024):.1f} MB")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Convert a Hugging Face model to GGUF fp16 format using llama.cpp's convert_hf_to_gguf.py.

Usage:
    python -m src.model_optimization.export_to_gguf
"""

import subprocess
import sys
from pathlib import Path


MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
HF_DIR = MODELS_DIR / "qwen2-0.5b-hf"
GGUF_FP16 = MODELS_DIR / "qwen2-0.5b-fp16.gguf"
CONVERT_PY = (
    Path(__file__).resolve().parents[2] / "llama.cpp" / "convert_hf_to_gguf.py"
)


def main() -> None:
    if GGUF_FP16.exists():
        print(f"GGUF fp16 model already exists at {GGUF_FP16}")
        return

    if not HF_DIR.exists():
        print(f"HF model not found at {HF_DIR}. Run download_model.py first.")
        sys.exit(1)

    if not CONVERT_PY.exists():
        print(f"convert_hf_to_gguf.py not found at {CONVERT_PY}. Is llama.cpp cloned?")
        sys.exit(1)

    print(f"Converting {HF_DIR} --> {GGUF_FP16} ...")
    subprocess.check_call(
        [
            sys.executable,
            str(CONVERT_PY),
            str(HF_DIR),
            "--outfile",
            str(GGUF_FP16),
            "--outtype",
            "f16",
        ]
    )
    size_mb = GGUF_FP16.stat().st_size / (1024 * 1024)
    print(f"Done — {size_mb:.1f} MB")


if __name__ == "__main__":
    main()

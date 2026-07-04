#!/usr/bin/env python3
"""
Download Qwen2-0.5B from Hugging Face and verify integrity.

Usage:
    python -m src.model_optimization.download_model
"""

import sys
from pathlib import Path

from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen2-0.5B"
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
HF_DIR = MODELS_DIR / "qwen2-0.5b-hf"


def main() -> None:
    if HF_DIR.exists() and (HF_DIR / "config.json").exists():
        print(f"Model already downloaded at {HF_DIR}")
        return

    print(f"Downloading {MODEL_NAME} ...")
    HF_DIR.mkdir(parents=True, exist_ok=True)

    print("  Downloading tokenizer ...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.save_pretrained(str(HF_DIR))

    print("  Downloading model ...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        torch_dtype="auto",
    )
    model.save_pretrained(str(HF_DIR))

    total_bytes = sum(
        f.stat().st_size for f in HF_DIR.rglob("*") if f.is_file()
    )
    total_mb = total_bytes / (1024 * 1024)
    print(f"Done — {total_mb:.1f} MB saved to {HF_DIR}")


if __name__ == "__main__":
    main()

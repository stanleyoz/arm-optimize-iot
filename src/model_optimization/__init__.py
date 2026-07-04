# Model optimization pipeline for ARM mobile deployment.
# - download_model.py: Fetch Qwen2-0.5B from Hugging Face
# - export_to_gguf.py: Convert HF model to GGUF format
# - quantize_model.py: Apply Q4_K_M quantization
# - benchmark.py: Measure inference performance

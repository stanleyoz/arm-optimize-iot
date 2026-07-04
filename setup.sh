#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
MODELS_DIR="$PROJECT_DIR/models"
LLAMACP_DIR="$PROJECT_DIR/llama.cpp"

echo "=== ARM AI Optimization Challenge — Setup ==="

# ------------------------------------------------------------------
# Python virtual environment
# ------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/4] Creating Python virtual environment ..."
    python3 -m venv "$VENV_DIR"
else
    echo "[1/4] Virtual environment already exists, skipping."
fi

source "$VENV_DIR/bin/activate"

echo "[2/4] Installing Python dependencies ..."
pip install --upgrade pip setuptools wheel --quiet
pip install -r "$PROJECT_DIR/requirements.txt" --quiet

# ------------------------------------------------------------------
# llama.cpp (build from source)
# ------------------------------------------------------------------
if [ ! -d "$LLAMACP_DIR" ]; then
    echo "[3/4] Cloning llama.cpp ..."
    git clone --depth=1 https://github.com/ggerganov/llama.cpp.git "$LLAMACP_DIR"
else
    echo "[3/4] llama.cpp already cloned, updating ..."
    git -C "$LLAMACP_DIR" pull --ff-only --quiet
fi

echo "Building llama.cpp ..."
mkdir -p "$LLAMACP_DIR/build"
cmake -S "$LLAMACP_DIR" -B "$LLAMACP_DIR/build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLAMA_CUDA=OFF \
    -DLLAMA_NATIVE=ON

cmake --build "$LLAMACP_DIR/build" --config Release --parallel "$(nproc)"

# Symlink tools into the project bin directory
mkdir -p "$PROJECT_DIR/bin"
for tool in llama-cli llama-quantize llama-perplexity llama-bench; do
    if [ -f "$LLAMACP_DIR/build/bin/$tool" ]; then
        ln -sf "$LLAMACP_DIR/build/bin/$tool" "$PROJECT_DIR/bin/$tool"
        echo "  Linked $tool"
    fi
done

# Symlink convert.py
if [ -f "$LLAMACP_DIR/convert.py" ]; then
    ln -sf "$LLAMACP_DIR/convert.py" "$PROJECT_DIR/bin/convert.py"
    echo "  Linked convert.py"
fi

# ------------------------------------------------------------------
# Create empty directories for data and models
# ------------------------------------------------------------------
echo "[4/4] Creating data and model directories ..."
mkdir -p "$MODELS_DIR"
mkdir -p "$PROJECT_DIR/data"

echo ""
echo "=== Setup complete ==="
echo "Activate the environment with:  source venv/bin/activate"
echo "Download the model with:        python -m src.model_optimization.download_model"

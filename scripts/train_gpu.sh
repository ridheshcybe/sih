#!/usr/bin/env bash
# Train all SIH26054 models on the GPU (or CPU/MPS with --device).
# Usage:
#   bash scripts/train_gpu.sh                      # auto device, all models
#   bash scripts/train_gpu.sh --device cuda:0 --epochs 30
#   bash scripts/train_gpu.sh --task fault --device cuda
set -e
cd "$(dirname "$0")/.."

if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
else
  PYTHON=".venv/bin/python"
fi

exec "$PYTHON" -m ml.train_gpu "$@"
#!/usr/bin/env bash
# One-time setup: create the Python venv, install pip deps, install npm deps.
# Works in bash and zsh. Windows PowerShell users: run scripts/setup.ps1 instead.
#
# Usage:
#   scripts/setup.sh              # CPU setup
#   scripts/setup.sh --with-gpu   # also install CUDA PyTorch + GPU requirements
set -e
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
fi

GPU=0
for arg in "$@"; do
  case "$arg" in
    --with-gpu) GPU=1 ;;
    *) echo "Unknown option: $arg (supported: --with-gpu, --help)"; exit 2 ;;
  esac
done

if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"   # Windows venv layout
elif [ -f ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"           # macOS / Linux venv layout
else
  echo "==> Creating Python virtual environment (.venv)"
  python3 -m venv .venv 2>/dev/null || python -m venv .venv
  if [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
  else
    PYTHON=".venv/bin/python"
  fi
fi

echo "==> Installing Python dependencies"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt

if [ "$GPU" -eq 1 ]; then
  echo "==> Installing GPU (CUDA) build of PyTorch"
  "$PYTHON" -m pip install torch --index-url https://download.pytorch.org/whl/cu124
  "$PYTHON" -m pip install -r requirements-gpu.txt
  echo "    (match the cu124 tag to your driver - see docs/gpu_training.md)"
fi

echo "==> Installing frontend dependencies"
(cd frontend && npm install)

echo ""
echo "Setup complete. Next:"
echo "  scripts/start_demo.sh      # full stack (works with or without trained models)"
echo "  scripts/train_models.sh    # optional: train ML models (CPU or --gpu)"

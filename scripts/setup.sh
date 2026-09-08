#!/usr/bin/env bash
# One-time setup: create the Python venv, install pip deps, install npm deps.
set -e
cd "$(dirname "$0")/.."

echo "==> Creating Python virtual environment (.venv)"
python -m venv .venv

if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
else
  PYTHON=".venv/bin/python"
fi

echo "==> Installing Python dependencies"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt

echo "==> Installing frontend dependencies"
(cd frontend && npm install)

echo ""
echo "Setup complete. Next: bash scripts/train_all.sh"
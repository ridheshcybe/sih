#!/usr/bin/env bash
# SIH26054 inference CLI wrapper — works in bash and zsh.
#
# Examples:
#   scripts/predict.sh --status
#   scripts/predict.sh --csv data/test.csv --out data/predictions.csv
#   scripts/predict.sh --simulate --profile hot_weather --fault-type overheating \
#       --severity 0.7 --fault-start 60 --duration 300
#   scripts/predict.sh --live --interval 1
#
# All flags are forwarded to python -m ml.predict (see ml/predict.py).
# Windows PowerShell users: run scripts/predict.ps1 instead.
set -e
cd "$(dirname "$0")/.."

if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"   # Windows venv layout
else
  PYTHON=".venv/bin/python"           # macOS / Linux venv layout
fi

exec "$PYTHON" -m ml.predict "$@"

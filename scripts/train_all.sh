#!/usr/bin/env bash
# Generate the synthetic dataset (if missing) and train all ML models.
set -e
cd "$(dirname "$0")/.."

if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"
else
  PYTHON=".venv/bin/python"
fi

if [ ! -f "data/train.csv" ]; then
  echo "==> Generating synthetic dataset (~40 missions)"
  "$PYTHON" -m simulator.generate_dataset --missions 40 --rows-per-mission 4000
else
  echo "==> Dataset already present (data/train.csv); skipping generation"
fi

echo "==> Training anomaly detection model"
"$PYTHON" -m ml.train_anomaly

echo "==> Training fault classifier model"
"$PYTHON" -m ml.train_fault_classifier

echo "==> Training degradation + RUL models"
"$PYTHON" -m ml.train_degradation_rul

echo ""
echo "All models trained and saved to models/."
echo "Start the full stack with: bash scripts/start_demo.sh"
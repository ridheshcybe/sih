#!/usr/bin/env bash
# SIH26054 training script — works in bash and zsh. (Run only when you want to
# (re)train; the demo also works without trained models.)
#
# Usage:
#   scripts/train_models.sh                  # CPU baselines (scikit-learn)
#   scripts/train_models.sh --gpu            # GPU/PyTorch models (auto device)
#   scripts/train_models.sh --gpu --epochs 30 --device cuda:0
#   scripts/train_models.sh --missions 60    # bigger dataset
#
# Options:
#   --gpu              train the PyTorch models instead of scikit-learn baselines
#   --missions N       number of dataset missions to generate (default 40)
#   (other flags are forwarded to ml.train_gpu, e.g. --epochs, --device)
set -e
cd "$(dirname "$0")/.."

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
fi

if [ -f ".venv/Scripts/python.exe" ]; then
  PYTHON=".venv/Scripts/python.exe"   # Windows venv layout
else
  PYTHON=".venv/bin/python"           # macOS / Linux venv layout
fi

GPU=0
MISSIONS=40
REST=()
while [ $# -gt 0 ]; do
  case "$1" in
    --gpu|-g) GPU=1 ;;
    --missions) MISSIONS="$2"; shift ;;
    *) REST+=("$1") ;;
  esac
  shift
done

# 1. Dataset ---------------------------------------------------------------
if [ ! -f "data/train.csv" ]; then
  echo "==> Generating synthetic dataset (fixed seed, identical everywhere)"
  "$PYTHON" -m simulator.generate_dataset --missions "$MISSIONS" --rows-per-mission 4000
else
  echo "==> Dataset already present (data/train.csv); skipping generation"
fi

# 2. Models ----------------------------------------------------------------
if [ "$GPU" -eq 1 ]; then
  echo "==> Training PyTorch models (anomaly AE, fault MLP, degradation + RUL)"
  "$PYTHON" -m ml.train_gpu --task all --device auto "${REST[@]+"${REST[@]}"}"
else
  echo "==> Training anomaly detection model (scikit-learn)"
  "$PYTHON" -m ml.train_anomaly
  echo "==> Training fault classifier model (scikit-learn)"
  "$PYTHON" -m ml.train_fault_classifier
  echo "==> Training degradation + RUL models (scikit-learn)"
  "$PYTHON" -m ml.train_degradation_rul
fi

echo ""
echo "All models saved to models/. Verify with:"
echo "  scripts/predict.sh --status"

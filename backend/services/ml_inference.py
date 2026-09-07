"""
backend/services/ml_inference.py -- Backend-facing ML inference layer (Task 4.4).

Thin adapter over ml/inference.py. Adds the project root to sys.path so the
backend can import the ML package from anywhere (uvicorn, scripts, tests),
then re-exports the unified prediction API:

    predict_all(features)          -> full payload dict (never raises)
    predict_all_from_window(window)-> payload from raw telemetry dicts
    predict_anomaly / predict_fault / predict_degradation / predict_rul

Every function falls back to safe defaults (anomaly=0.0, uniform fault_probs,
degradation=0.0, rul=120.0/low) and logs a warning if a model file is missing
or corrupt -- the backend must never crash because of the ML layer.
"""

import os
import sys

# Project root (two levels above backend/services/)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ml.inference import (  # noqa: E402,F401
    predict_all,
    predict_all_from_window,
    predict_anomaly,
    predict_fault,
    predict_degradation,
    predict_rul,
    reset_model_cache,
    FAULT_CLASSES,
    RUL_FULL_LIFE,
)

__all__ = [
    "predict_all",
    "predict_all_from_window",
    "predict_anomaly",
    "predict_fault",
    "predict_degradation",
    "predict_rul",
    "reset_model_cache",
    "FAULT_CLASSES",
    "RUL_FULL_LIFE",
]

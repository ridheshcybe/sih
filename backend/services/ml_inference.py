"""ML inference glue for the backend.

Loads the Predictor once at startup; predict() never raises - the ML layer
degrades to safe defaults if models are missing.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

import numpy as np

from backend.config import MODEL_PATH
from ml.inference import Predictor

logger = logging.getLogger("sih26054.ml")

_predictor: Predictor | None = None


def get_ml_predictor() -> Predictor:
    global _predictor
    if _predictor is None:
        _predictor = Predictor(Path(MODEL_PATH))
        logger.info("ML predictor status: %s", _predictor.status)
    return _predictor


def predict(features: np.ndarray, twin_state: Dict | None = None) -> Dict:
    try:
        return get_ml_predictor().predict_all(features, twin_state)
    except Exception as exc:  # noqa: BLE001 - never let ML break the data pipeline
        logger.error("ML inference failed (%s) - using fallback defaults", exc)
        return {
            "anomaly_score": 0.0,
            "fault_probs": {c: (1.0 if c == "none" else 0.0) for c in
                            ["none", "misfire", "injector_degradation", "lubrication_issue",
                             "overheating", "sensor_drift", "abnormal_vibration",
                             "battery_alternator_degradation"]},
            "degradation_level": 0.0,
            "rul_estimate": 500.0,
            "rul_confidence": "low",
            "model_status": {"anomaly": False, "fault_classifier": False,
                              "degradation": False, "rul": False},
        }
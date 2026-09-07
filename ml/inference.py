"""
ml/inference.py -- Unified model loading, predictions and fallbacks (SIH26054).

Used directly by backend/services/ml_inference.py. Every public function
tolerates missing/corrupt model files by returning safe defaults and logging
warnings, so the backend never crashes because of the ML layer.

Score convention: anomaly_score in [0, 1], higher = more anomalous.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np

from ml.features import extract_features

logger = logging.getLogger("ml_inference")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "models")

FAULT_CLASSES = [
    "none", "injector_degradation", "overheating",
    "lubrication_issue", "sensor_drift", "abnormal_vibration",
]
RUL_FULL_LIFE = 120.0  # missions

_paths = {
    "anomaly": os.path.join(MODEL_DIR, "anomaly_model.joblib"),
    "fault": os.path.join(MODEL_DIR, "fault_classifier.joblib"),
    "degradation": os.path.join(MODEL_DIR, "degradation_model.joblib"),
    "rul": os.path.join(MODEL_DIR, "rul_model.joblib"),
}

_models: Dict[str, Optional[object]] = {}
_load_attempted: set = set()


def _get(name: str):
    """Lazily load a model once; returns None if missing/corrupt (with warning)."""
    if name not in _load_attempted:
        _load_attempted.add(name)
        path = _paths[name]
        try:
            _models[name] = joblib.load(path)
            logger.info("ML model loaded: %s (%s)", name, path)
        except FileNotFoundError:
            logger.warning("ML model file missing: %s -- fallbacks in use", path)
        except Exception as exc:  # corrupt / incompatible pickle
            logger.warning("ML model failed to load (%s): %s -- fallbacks in use", path, exc)
    return _models.get(name)


def reset_model_cache() -> None:
    """Force reload on next call (used by tests for the missing-file scenario)."""
    _models.clear()
    _load_attempted.clear()


def predict_anomaly(features: np.ndarray) -> float:
    """Anomaly score in [0, 1]; higher = more anomalous. Fallback: 0.0."""
    try:
        model = _get("anomaly")
        if model is None:
            return 0.0
        return float(-model.score_samples(np.asarray(features, dtype=np.float64).reshape(1, -1))[0])
    except Exception as exc:
        logger.warning("predict_anomaly failed: %s -- returning 0.0", exc)
        return 0.0


def predict_fault(features: np.ndarray) -> Dict[str, float]:
    """{fault_type: probability} summing to 1.0. Fallback: uniform."""
    try:
        model = _get("fault")
        if model is None:
            return {c: round(1.0 / len(FAULT_CLASSES), 4) for c in FAULT_CLASSES}
        proba = model.predict_proba(np.asarray(features, dtype=np.float64).reshape(1, -1))[0]
        return {str(c): float(p) for c, p in zip(model.classes_, proba)}
    except Exception as exc:
        logger.warning("predict_fault failed: %s -- uniform fallback", exc)
        return {c: round(1.0 / len(FAULT_CLASSES), 4) for c in FAULT_CLASSES}


def predict_degradation(features: np.ndarray) -> float:
    """Degradation level in [0, 1]. Fallback: 0.0."""
    try:
        model = _get("degradation")
        if model is None:
            return 0.0
        d = float(model.predict(np.asarray(features, dtype=np.float64).reshape(1, -1))[0])
        return float(min(max(d, 0.0), 1.0))
    except Exception as exc:
        logger.warning("predict_degradation failed: %s -- returning 0.0", exc)
        return 0.0


def predict_rul(features: np.ndarray, degradation: Optional[float] = None) -> Tuple[float, str]:
    """
    (rul_estimate in missions, confidence in {low, medium, high}).

    Blends the trained regressor with the interpretable time-to-threshold rule
    rul = (1 - degradation) * FULL_LIFE (per docs/fault_and_degradation_model.md).
    Degrades to the pure rule when the regressor is missing. Confidence follows
    the degradation level: early-stage = high, late-stage = medium/low.
    Fallback: (RUL_FULL_LIFE, "low").
    """
    try:
        deg_model = _get("degradation")
        d = predict_degradation(features) if degradation is None else degradation
        d = float(min(max(d, 0.0), 1.0))
        rule_rul = (1.0 - d) * RUL_FULL_LIFE

        model = _get("rul")
        if model is not None:
            x = np.concatenate([
                np.asarray(features, dtype=np.float64).reshape(1, -1),
                np.array([[d]]),
            ], axis=1)
            model_rul = float(model.predict(x)[0])
            rul = 0.5 * model_rul + 0.5 * rule_rul
        else:
            rul = rule_rul

        confidence = "high" if d < 0.4 else ("medium" if d < 0.75 else "low")
        if deg_model is None:
            # Degradation estimate itself is a fallback (0.0) -- never claim
            # high confidence in a prediction built on fallback inputs.
            confidence = "low"
        return round(max(rul, 0.0), 2), confidence
    except Exception as exc:
        logger.warning("predict_rul failed: %s -- static fallback", exc)
        return RUL_FULL_LIFE, "low"


def predict_all(features) -> Dict:
    """
    Run the full ML stack on one feature vector. Never raises.

    Returns: {anomaly_score, fault_probs, degradation_level,
              rul_estimate, rul_confidence}
    """
    f = np.asarray(features, dtype=np.float64).reshape(1, -1)
    fault_probs = predict_fault(f)
    degradation = predict_degradation(f)
    rul, confidence = predict_rul(f, degradation)
    return {
        "anomaly_score": round(predict_anomaly(f), 4),
        "fault_probs": {k: round(v, 4) for k, v in fault_probs.items()},
        "degradation_level": round(degradation, 4),
        "rul_estimate": rul,
        "rul_confidence": confidence,
    }


def predict_all_from_window(window: List[dict]) -> Dict:
    """Convenience: raw telemetry dicts -> extract_features -> predict_all."""
    return predict_all(extract_features(window))

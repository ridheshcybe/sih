"""
ml/features.py -- Single source of truth for the ML feature vector (SIH26054).

Both training (ml/train_all_models.py) and backend inference
(backend/services/ml_inference.py) import FEATURE_NAMES from here, so the
feature order can never drift between training and serving.

A "window" is a list of consecutive raw telemetry dicts (1 Hz), e.g.:
    [{"rpm": 2450.0, "cht": 180.2, ...}, ...]   # 60 rows = 60 s window
"""

import numpy as np

WINDOW_SIZE = 60  # 60 samples @ 1 Hz

# Canonical sensor list (matches backend/simulator/EngineSimulator.py columns).
SENSORS = [
    "rpm", "cht", "egt", "oil_pressure", "oil_temperature",
    "fuel_flow", "vibration_rms", "battery_voltage", "alternator_current",
]

# The exact, frozen feature order. Every model is trained on vectors in this
# order and every inference call must build vectors in this order.
FEATURE_NAMES = []
for _s in SENSORS:
    FEATURE_NAMES += [
        f"{_s}_mean", f"{_s}_std", f"{_s}_min", f"{_s}_max",
        f"{_s}_last", f"{_s}_delta",
    ]
FEATURE_NAMES = tuple(FEATURE_NAMES)  # 9 sensors x 6 stats = 54 features
N_FEATURES = len(FEATURE_NAMES)


def extract_features(window) -> np.ndarray:
    """
    Extract the fixed-length feature vector from one telemetry window.

    :param window: list of telemetry dicts (len >= 1; last WINDOW_SIZE are used).
    :return: np.ndarray of shape (N_FEATURES,) in FEATURE_NAMES order.
    """
    if not window:
        raise ValueError("extract_features: empty window")
    tail = list(window)[-WINDOW_SIZE:]
    n = len(tail)
    vec = np.empty(N_FEATURES, dtype=np.float64)
    k = 0
    for s in SENSORS:
        vals = np.array(
            [float(w.get(s, np.nan) or 0.0) for w in tail], dtype=np.float64
        )
        vals = np.nan_to_num(vals, nan=0.0, posinf=0.0, neginf=0.0)
        vec[k:k + 6] = (
            vals.mean(), vals.std(), vals.min(), vals.max(),
            vals[-1], (vals[-1] - vals[0]) / max(n - 1, 1),
        )
        k += 6
    return vec

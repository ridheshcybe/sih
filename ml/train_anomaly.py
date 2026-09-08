#!/usr/bin/env python3
"""Train the anomaly detection model (Isolation Forest) on healthy windows.

Usage:
  python -m ml.train_anomaly
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from ml.data_utils import MODELS_DIR, build_features, healthy_only, load_splits, save_meta

ANOMALY_MODEL_PATH = MODELS_DIR / "anomaly_model.joblib"
ANOMALY_META_PATH = MODELS_DIR / "anomaly_meta.json"


def score(iso: IsolationForest, x: np.ndarray) -> np.ndarray:
    """Map raw decision_function output to a 0..1 anomaly score."""
    raw = -iso.decision_function(x)          # higher = more anomalous
    return 1.0 - np.exp(-np.clip(raw, 0.0, None))


def main() -> int:
    train, val, test = load_splits()
    print(f"Rows: train={len(train)}, val={len(val)}, test={len(test)}")

    healthy = healthy_only(train)
    X_healthy, _, _, _, feature_names = build_features(healthy)
    print(f"Healthy windows for training: {X_healthy.shape}")

    iso = IsolationForest(contamination=0.05, n_estimators=120, random_state=0, n_jobs=-1)
    iso.fit(X_healthy)

    # Residual statistics over healthy data: used at inference to compute a
    # residual z-score anomaly signal in addition to the Isolation Forest score.
    res_idx = [i for i, n in enumerate(feature_names) if n.endswith("_residual")]
    res_means = np.zeros(len(feature_names))
    res_stds = np.zeros(len(feature_names))
    for i in res_idx:
        res_means[i] = float(X_healthy[:, i].mean())
        res_stds[i] = float(X_healthy[:, i].std()) or 1e-6

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(iso, ANOMALY_MODEL_PATH)
    save_meta(ANOMALY_META_PATH, {
        "feature_names": feature_names,
        "model": "IsolationForest + residual z-score",
        "residual_means": res_means.tolist(),
        "residual_stds": res_stds.tolist(),
    })
    print(f"Saved model -> {ANOMALY_MODEL_PATH}")

    # Report separation on the test split using the same hybrid score the
    # backend applies: max(isolation-forest score, residual z-score).
    X_test, y_fault, _, _, _ = build_features(test)
    healthy_mask = y_fault == "none"
    if healthy_mask.any() and (~healthy_mask).any():
        def hybrid(x):
            if_score = score(iso, x.reshape(1, -1))[0]
            z = np.abs((x[res_idx] - res_means[res_idx]) / np.maximum(res_stds[res_idx], 1e-6))
            residual_score = float(np.clip((z - 1.0) / 4.0, 0.0, 1.0).max()) if z.size else 0.0
            return max(if_score, residual_score)

        s_healthy = np.array([hybrid(x) for x in X_test[healthy_mask][:500]])
        s_faulty = np.array([hybrid(x) for x in X_test[~healthy_mask][:500]])
        print(f"\nAnomaly score on test split (hybrid, as used by the backend):")
        print(f"  healthy segments: mean={s_healthy.mean():.3f} p95={np.percentile(s_healthy, 95):.3f}")
        print(f"  faulty segments:  mean={s_faulty.mean():.3f} p95={np.percentile(s_faulty, 95):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""Train the degradation regressor and RUL estimator.

Usage:
  python -m ml.train_degradation_rul
"""

from __future__ import annotations

import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from ml.data_utils import MODELS_DIR, build_features, load_splits, save_meta

DEGRADATION_MODEL_PATH = MODELS_DIR / "degradation_model.joblib"
RUL_MODEL_PATH = MODELS_DIR / "rul_model.joblib"
RUL_META_PATH = MODELS_DIR / "rul_meta.json"


def main() -> int:
    train, val, test = load_splits()

    X_train, _, y_deg_train, y_rul_train, feature_names = build_features(train)
    X_test, _, y_deg_test, y_rul_test, _ = build_features(test)
    print(f"Train windows: {X_train.shape}, Test windows: {X_test.shape}")

    # --- Degradation regressor ---
    deg_model = RandomForestRegressor(n_estimators=150, min_samples_leaf=2, random_state=0, n_jobs=-1)
    deg_model.fit(X_train, y_deg_train)
    pred_deg = deg_model.predict(X_test)
    print(f"\nDegradation model  -> MAE={mean_absolute_error(y_deg_test, pred_deg):.4f} "
          f"R2={r2_score(y_deg_test, pred_deg):.3f}")

    # --- RUL regressor (features + degradation as extra input) ---
    X_rul_train = np.hstack([X_train, y_deg_train.reshape(-1, 1)])
    X_rul_test = np.hstack([X_test, y_deg_test.reshape(-1, 1)])
    rul_model = RandomForestRegressor(n_estimators=150, min_samples_leaf=2, random_state=0, n_jobs=-1)
    rul_model.fit(X_rul_train, y_rul_train)
    pred_rul = rul_model.predict(X_rul_test)
    print(f"RUL model          -> MAE={mean_absolute_error(y_rul_test, pred_rul):.2f} h "
          f"R2={r2_score(y_rul_test, pred_rul):.3f}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(deg_model, DEGRADATION_MODEL_PATH)
    joblib.dump(rul_model, RUL_MODEL_PATH)
    save_meta(RUL_META_PATH, {
        "feature_names": feature_names,
        "degradation_model": "RandomForestRegressor",
        "rul_model": "RandomForestRegressor",
        "rul_extra_feature": "degradation_level",
    })
    print(f"Saved models -> {DEGRADATION_MODEL_PATH}, {RUL_MODEL_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
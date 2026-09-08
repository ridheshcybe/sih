#!/usr/bin/env python3
"""Train the fault classifier (Random Forest) on labeled windows.

Usage:
  python -m ml.train_fault_classifier
"""

from __future__ import annotations

import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

from ml.data_utils import MODELS_DIR, build_features, encode_faults, load_splits, save_meta

FAULT_MODEL_PATH = MODELS_DIR / "fault_classifier.joblib"
FAULT_META_PATH = MODELS_DIR / "fault_classifier_meta.json"


def main() -> int:
    train, val, test = load_splits()

    X_train, y_fault_train, _, _, feature_names = build_features(train)
    X_test, y_fault_test, _, _, _ = build_features(test)

    classes = sorted(set(y_fault_train) | set(y_fault_test))
    y_train, classes = encode_faults(y_fault_train, classes)
    y_test, _ = encode_faults(y_fault_test, classes)
    print(f"Classes ({len(classes)}): {classes}")
    print(f"Train windows: {X_train.shape}, Test windows: {X_test.shape}")

    clf = RandomForestClassifier(n_estimators=150, min_samples_leaf=2, random_state=0, n_jobs=-1)
    clf.fit(X_train, y_train)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, FAULT_MODEL_PATH)
    save_meta(FAULT_META_PATH, {
        "feature_names": feature_names,
        "classes": classes,
        "model": "RandomForestClassifier",
    })
    print(f"Saved model -> {FAULT_MODEL_PATH}")

    pred = clf.predict(X_test)
    print(f"\nTest accuracy: {accuracy_score(y_test, pred):.3f}")
    print(classification_report(y_test, pred, target_names=classes, labels=range(len(classes)), zero_division=0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
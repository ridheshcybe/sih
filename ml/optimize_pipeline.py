#!/usr/bin/env python3
"""Bounded, leakage-safe optimization loop for all SIH26054 ML tasks.

The validation split selects candidates; the test split is evaluated once for
the selected final candidates.  The loop never oversamples or fits a
transformer using validation/test data.

Usage:
    python -m ml.optimize_pipeline --max-iterations 15
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.feature_selection import SelectFromModel
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.data_utils import MODELS_DIR, build_features, load_splits, save_meta

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
ARTIFACT_DIR = MODELS_DIR / "optimized"
TARGET = 0.98
RANDOM_STATE = 0


def candidate_classifier(iteration: int, multiclass: bool) -> Any:
    """Return a deterministic sequence of scaling/selection/ensemble models."""
    choices = [
        ("rf_balanced", RandomForestClassifier(
            n_estimators=100, min_samples_leaf=1, max_features="sqrt",
            class_weight="balanced_subsample", n_jobs=-1, random_state=RANDOM_STATE,
        )),
        ("extra_trees_balanced", ExtraTreesClassifier(
            n_estimators=120, min_samples_leaf=1, max_features=1.0,
            class_weight="balanced", n_jobs=-1, random_state=RANDOM_STATE,
        )),
        ("extra_trees_selected", Pipeline([
            ("select", SelectFromModel(ExtraTreesClassifier(
                n_estimators=60, class_weight="balanced",
                n_jobs=-1, random_state=RANDOM_STATE,
            ), threshold="median")),
            ("model", ExtraTreesClassifier(
                n_estimators=120, min_samples_leaf=1, max_features=1.0,
                class_weight="balanced", n_jobs=-1, random_state=RANDOM_STATE,
            )),
        ])),
        ("hist_gradient_boosting", HistGradientBoostingClassifier(
            max_iter=220, learning_rate=0.08, max_leaf_nodes=31,
            l2_regularization=0.1, random_state=RANDOM_STATE,
        )),
        ("scaled_logistic_selected", Pipeline([
            ("scale", StandardScaler()),
            ("select", SelectFromModel(LogisticRegression(
                C=0.5, max_iter=300, class_weight="balanced",
                solver="lbfgs", random_state=RANDOM_STATE,
            ), threshold="median")),
            ("model", LogisticRegression(
                C=2.0, max_iter=400, class_weight="balanced",
                solver="lbfgs", random_state=RANDOM_STATE,
            )),
        ])),
    ]
    name, model = choices[(iteration - 1) % len(choices)]
    return name + ("_multiclass" if multiclass else "_binary"), model


def candidate_regressor(iteration: int) -> tuple[str, Any]:
    choices = [
        ("extra_trees_regressor", ExtraTreesRegressor(
            n_estimators=120, min_samples_leaf=1, max_features=1.0,
            n_jobs=-1, random_state=RANDOM_STATE,
        )),
        ("random_forest_regressor", RandomForestRegressor(
            n_estimators=120, min_samples_leaf=1, max_features=0.9,
            n_jobs=-1, random_state=RANDOM_STATE,
        )),
        ("hist_gradient_boosting_regressor", HistGradientBoostingRegressor(
            max_iter=250, learning_rate=0.06, max_leaf_nodes=31,
            l2_regularization=0.01, random_state=RANDOM_STATE,
        )),
    ]
    return choices[(iteration - 1) % len(choices)]


def classification_metrics(
    y_true: np.ndarray, model: Any, X: np.ndarray, threshold: float | None = None
) -> dict[str, float]:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)
    else:
        raise TypeError(f"{type(model).__name__} must expose predict_proba")
    if proba.shape[1] == 2:
        score = proba[:, 1]
        pred = (score >= threshold).astype(int) if threshold is not None else model.predict(X)
        auc = roc_auc_score(y_true, score)
    else:
        pred = model.predict(X)
        auc = roc_auc_score(y_true, proba, multi_class="ovr", average="macro")
    return {
        "accuracy": float(accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, average="macro", zero_division=0)),
        "recall": float(recall_score(y_true, pred, average="macro", zero_division=0)),
        "f1": float(f1_score(y_true, pred, average="macro", zero_division=0)),
        "roc_auc": float(auc),
    }


def find_binary_threshold(model: Any, X: np.ndarray, y: np.ndarray) -> float:
    """Select a threshold on validation data, optimizing the weakest metric."""
    scores = model.predict_proba(X)[:, 1]
    best_threshold, best_score = 0.5, -np.inf
    for threshold in np.linspace(0.05, 0.95, 91):
        pred = (scores >= threshold).astype(int)
        values = (
            accuracy_score(y, pred),
            precision_score(y, pred, zero_division=0),
            recall_score(y, pred, zero_division=0),
            f1_score(y, pred, zero_division=0),
        )
        score = min(values)
        if score > best_score:
            best_threshold, best_score = float(threshold), float(score)
    return best_threshold


def regression_metrics(y_true: np.ndarray, model: Any, X: np.ndarray) -> dict[str, float]:
    pred = model.predict(X)
    return {
        "r2": float(r2_score(y_true, pred)),
        "mae": float(np.mean(np.abs(y_true - pred))),
    }


def cv_classification(model: Any, X: np.ndarray, y: np.ndarray, folds: int) -> dict[str, float]:
    scoring = {
        "accuracy": "accuracy",
        "precision": "precision_macro",
        "recall": "recall_macro",
        "f1": "f1_macro",
        "roc_auc": "roc_auc" if len(np.unique(y)) == 2 else "roc_auc_ovr",
    }
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=RANDOM_STATE)
    result = cross_validate(model, X, y, scoring=scoring, cv=cv, n_jobs=1)
    return {key: float(np.mean(result[f"test_{key}"])) for key in scoring}


def cv_regression(model: Any, X: np.ndarray, y: np.ndarray, folds: int) -> dict[str, float]:
    result = cross_validate(model, X, y, scoring={"r2": "r2"}, cv=folds, n_jobs=1)
    return {"r2": float(np.mean(result["test_r2"]))}


def downsample(X: np.ndarray, y: np.ndarray, limit: int, classification: bool) -> tuple[np.ndarray, np.ndarray]:
    if len(X) <= limit:
        return X, y
    rng = np.random.default_rng(RANDOM_STATE)
    if not classification:
        idx = rng.choice(len(X), size=limit, replace=False)
    else:
        idx = np.concatenate([
            rng.choice(np.flatnonzero(y == label), size=min(limit // len(np.unique(y)), np.sum(y == label)), replace=False)
            for label in np.unique(y)
        ])
        if len(idx) < limit:
            remaining = np.setdiff1d(np.arange(len(X)), idx)
            idx = np.concatenate([idx, rng.choice(remaining, size=limit - len(idx), replace=False)])
    return X[idx], y[idx]


def meets(metrics: dict[str, float], keys: tuple[str, ...]) -> bool:
    return all(np.isfinite(metrics[key]) and metrics[key] >= TARGET for key in keys)


def fmt_metrics(metrics: dict[str, float]) -> str:
    return ", ".join(f"{key}={value:.4f}" for key, value in metrics.items())


def serializable_params(model: Any) -> dict[str, Any]:
    params = {}
    for key, value in model.get_params(deep=False).items():
        params[key] = value if isinstance(value, (str, int, float, bool, type(None))) else repr(value)
    return params


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-iterations", type=int, default=15)
    parser.add_argument("--cv-folds", type=int, default=3)
    parser.add_argument("--cv-sample", type=int, default=20000)
    args = parser.parse_args()
    if not 1 <= args.max_iterations <= 15:
        parser.error("--max-iterations must be between 1 and 15")
    if args.cv_folds < 2:
        parser.error("--cv-folds must be at least 2")

    train, val, test = load_splits()
    X_train, y_fault_train, y_deg_train, y_rul_train, feature_names = build_features(train)
    X_val, y_fault_val, y_deg_val, y_rul_val, _ = build_features(val)
    X_test, y_fault_test, y_deg_test, y_rul_test, _ = build_features(test)
    classes = sorted(set(y_fault_train) | set(y_fault_val) | set(y_fault_test))
    class_to_id = {label: i for i, label in enumerate(classes)}
    y_train = np.array([class_to_id[label] for label in y_fault_train])
    y_val = np.array([class_to_id[label] for label in y_fault_val])
    y_test = np.array([class_to_id[label] for label in y_fault_test])
    anomaly_train = (y_train != class_to_id["none"]).astype(int)
    anomaly_val = (y_val != class_to_id["none"]).astype(int)
    anomaly_test = (y_test != class_to_id["none"]).astype(int)

    X_cv_fault, y_cv_fault = downsample(X_train, y_train, args.cv_sample, True)
    X_cv_anomaly, y_cv_anomaly = downsample(X_train, anomaly_train, args.cv_sample, True)
    X_cv_deg, y_cv_deg = downsample(X_train, y_deg_train, args.cv_sample, False)
    X_cv_rul, y_cv_rul = downsample(X_train, y_rul_train, args.cv_sample, False)

    rows: list[dict[str, Any]] = []
    best: dict[str, tuple[float, Any, str, dict[str, float], float | None]] = {}
    tasks = [
        ("anomaly", "classification", X_cv_anomaly, y_cv_anomaly, X_val, anomaly_val, X_test, anomaly_test),
        ("fault", "classification", X_cv_fault, y_cv_fault, X_val, y_val, X_test, y_test),
        ("degradation", "regression", X_cv_deg, y_cv_deg, X_val, y_deg_val, X_test, y_deg_test),
        ("rul", "regression", X_cv_rul, y_cv_rul, X_val, y_rul_val, X_test, y_rul_test),
    ]
    started = time.time()
    for iteration in range(1, args.max_iterations + 1):
        print(f"\n=== optimization iteration {iteration}/{args.max_iterations} ===", flush=True)
        for task, kind, X_cv, y_cv, X_valid, y_valid, _, _ in tasks:
            required = ("accuracy", "precision", "recall", "f1", "roc_auc") if kind == "classification" else ("r2",)
            if task in best and meets(best[task][3], required):
                continue
            if kind == "classification":
                name, model = candidate_classifier(iteration, task == "fault")
                cv_metrics = cv_classification(model, X_cv, y_cv, args.cv_folds)
                model.fit(X_train, anomaly_train if task == "anomaly" else y_train)
                threshold = find_binary_threshold(model, X_valid, y_valid) if task == "anomaly" else None
                valid_metrics = classification_metrics(y_valid, model, X_valid, threshold)
                keys = ("accuracy", "precision", "recall", "f1", "roc_auc")
            else:
                name, model = candidate_regressor(iteration)
                target = y_deg_train if task == "degradation" else y_rul_train
                cv_metrics = cv_regression(model, X_cv, y_cv, args.cv_folds)
                model.fit(X_train, target)
                valid_metrics = regression_metrics(y_valid, model, X_valid)
                keys = ("r2",)
            score = min(valid_metrics[key] for key in keys)
            prior = best.get(task)
            if prior is None or score > prior[0]:
                best[task] = (score, clone(model), name, valid_metrics, threshold)
            rows.append({
                "iteration": iteration, "task": task, "change": name,
                "cv": cv_metrics, "validation": valid_metrics,
                "validation_min": score,
            })
            print(f"{task:12s} {name:30s} CV[{fmt_metrics(cv_metrics)}] "
                  f"VALID[{fmt_metrics(valid_metrics)}]", flush=True)
        if all(task in best and meets(best[task][3], ("accuracy", "precision", "recall", "f1", "roc_auc")
                                      if kind == "classification" else ("r2",))
               for task, kind, *_ in tasks):
            print("Target reached on validation metrics; stopping early.")
            break

    final_metrics: dict[str, dict[str, float]] = {}
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    for task, kind, _, _, _, _, X_eval, y_eval in tasks:
        _, model, name, valid_metrics, threshold = best[task]
        if task == "anomaly":
            model.fit(X_train, anomaly_train)
        elif task == "fault":
            model.fit(X_train, y_train)
        elif task == "degradation":
            model.fit(X_train, y_deg_train)
        else:
            model.fit(X_train, y_rul_train)
        final_metrics[task] = (
            classification_metrics(y_eval, model, X_eval, threshold)
            if kind == "classification" else regression_metrics(y_eval, model, X_eval)
        )
        print(f"FINAL {task:12s} {name:30s} {fmt_metrics(final_metrics[task])}")
        joblib.dump(model, ARTIFACT_DIR / f"{task}_model.joblib")
        save_meta(ARTIFACT_DIR / f"{task}_meta.json", {
            "task": task, "model": name, "target_threshold": TARGET,
            "classes": classes if task == "fault" else [0, 1] if task == "anomaly" else None,
            "feature_names": feature_names,
            "parameters": serializable_params(model),
            "selected_validation_metrics": valid_metrics,
            "final_test_metrics": final_metrics[task],
            "decision_threshold": threshold,
        })

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"optimization_report_{time.strftime('%Y%m%d_%H%M%S')}.md"
    with report_path.open("w", encoding="utf-8") as report:
        report.write("# Automated ML optimization report\n\n")
        report.write(f"- Target threshold: **{TARGET:.2f}**\n- Iterations run: **{max(row['iteration'] for row in rows)}**\n")
        report.write(f"- Runtime: **{time.time() - started:.1f}s**\n\n")
        report.write("## Final test metrics\n\n| task | accuracy | precision | recall | f1 | roc_auc | r2 | mae | pass |\n")
        report.write("|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
        for task, metrics in final_metrics.items():
            keys = ("accuracy", "precision", "recall", "f1", "roc_auc") if task in {"anomaly", "fault"} else ("r2", "mae")
            passed = meets(metrics, keys[:-1] if task in {"degradation", "rul"} else keys)
            values = [f"{metrics[k]:.4f}" if k in metrics else "-" for k in
                      ("accuracy", "precision", "recall", "f1", "roc_auc", "r2", "mae")]
            report.write(f"| {task} | " + " | ".join(values) + f" | {'YES' if passed else 'NO'} |\n")
        report.write("\n## Iteration log\n\n| iteration | task | change | validation metrics | CV metrics |\n|---:|---|---|---|---|\n")
        for row in rows:
            report.write(f"| {row['iteration']} | {row['task']} | `{row['change']}` | "
                         f"{fmt_metrics(row['validation'])} | {fmt_metrics(row['cv'])} |\n")
        report.write("\n## Artifacts\n\n")
        report.write(f"Models and metadata are saved in `{ARTIFACT_DIR.relative_to(ROOT)}/`.\n")
        report.write("The test set is held out from candidate selection; inspect the `pass` column before deployment.\n")
    print(f"Report saved -> {report_path}")
    print(f"Models saved -> {ARTIFACT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
ml/verify_anomaly.py -- Task 4.2 VERIFY: anomaly detection model.

Checks:
  1. Model file loads without errors.
  2. Healthy vs faulty score separation (means + AUROC on data/test.jsonl).
  3. Inference time < 50 ms per window.
  4. Score stability: near-zero variance for identical inputs, bounded drift
     for perturbed inputs, and no scores outside [0, 1].

Run:  .venv/bin/python ml/verify_anomaly.py
"""

import json
import os
import sys
import time

import joblib
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.features import extract_features, FEATURE_NAMES  # noqa: E402
from ml.generate_dataset import _base_window, apply_fault, FAULT_TYPES  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT, "models", "anomaly_model.joblib")
TEST_PATH = os.path.join(ROOT, "data", "test.jsonl")

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
results = []


def check(name, ok, detail="", level=None):
    status = PASS if ok else (level or FAIL)
    results.append((status, name, detail))
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))
    return ok


def main():
    # ---- 1. Model loads without errors ----
    try:
        model = joblib.load(MODEL_PATH)
        check("anomaly model loads without errors", True, MODEL_PATH)
    except Exception as exc:
        check("anomaly model loads without errors", False, str(exc))
        print("\nModel missing -- run: .venv/bin/python ml/train_all_models.py")
        return 1

    # ---- 2. Separation on held-out test set ----
    X, labels = [], []
    with open(TEST_PATH) as f:
        for line in f:
            s = json.loads(line)
            X.append(s["features"])
            labels.append(s["label"])
    X = np.asarray(X)
    labels = np.asarray(labels)
    scores = -model.score_samples(X)  # 0 = healthy, higher = anomalous

    healthy = scores[labels == "none"]
    faulty = scores[labels != "none"]
    mean_h, mean_f = float(healthy.mean()), float(faulty.mean())

    from sklearn.metrics import roc_auc_score
    auroc = roc_auc_score((labels != "none").astype(int), scores)

    check("healthy mean score is low (< 0.5)", mean_h < 0.5, f"mean={mean_h:.3f}")
    check("faulty mean score is higher than healthy", mean_f > mean_h,
          f"faulty={mean_f:.3f} vs healthy={mean_h:.3f} (gap={mean_f - mean_h:.3f})")
    check("AUROC >= 0.80", auroc >= 0.80, f"AUROC={auroc:.3f}")
    if auroc < 0.90:
        print(f"[{WARN}] AUROC {auroc:.3f} < 0.90 -- usable for demo; "
              f"improve by training on more fault severities")

    # ---- 3. Inference timing (< 50 ms/window) ----
    x1 = X[:1]
    model.score_samples(x1)  # warm-up (imports, allocations)
    t0 = time.perf_counter()
    n = 100
    for _ in range(n):
        model.score_samples(x1)
    dt_ms = 1e3 * (time.perf_counter() - t0) / n
    check("inference < 50 ms per window", dt_ms < 50.0, f"{dt_ms:.2f} ms avg over {n} runs")

    # ---- 4a. Determinism: identical input -> identical score ----
    s_same = [-model.score_samples(x1)[0] for _ in range(10)]
    spread = max(s_same) - min(s_same)
    check("score deterministic for identical inputs", spread < 1e-9, f"spread={spread:.2e}")

    # ---- 4b. Small perturbation -> bounded score change ----
    x_pert = x1.copy()
    x_pert[0, ::10] += 0.01  # ~1% jitter on every 10th feature
    s_orig = -model.score_samples(x1)[0]
    s_pert = -model.score_samples(x_pert)[0]
    drift = abs(s_pert - s_orig)
    check("score stability under small perturbation", drift < 0.05,
          f"|delta|={drift:.4f} (threshold 0.05)")

    # ---- 4c. All scores within [0, 1] ----
    check("all scores within [0, 1]",
          bool(np.all(scores >= 0.0) and np.all(scores <= 1.0)),
          f"min={scores.min():.3f} max={scores.max():.3f}")

    # ---- 5. Leakage guard: fresh synthetic windows must behave like test data ----
    fresh_healthy = np.vstack([extract_features(_base_window()) for _ in range(20)])
    fresh_faulty_windows = []
    for ft in FAULT_TYPES:
        for _ in range(20):
            win = _base_window()
            apply_fault(win, ft, 0.7)
            fresh_faulty_windows.append(win)
    fresh_faulty = np.vstack([extract_features(w) for w in fresh_faulty_windows])
    fresh_scores = -model.score_samples(fresh_healthy)
    f_scores = -model.score_samples(fresh_faulty)
    check("leakage guard: fresh healthy windows score low", float(np.mean(fresh_scores)) < 0.5,
          f"mean={np.mean(fresh_scores):.3f}")
    check("leakage guard: fresh faulty windows score higher", float(np.mean(f_scores)) > float(np.mean(fresh_scores)),
          f"faulty={np.mean(f_scores):.3f} vs healthy={np.mean(fresh_scores):.3f}")

    # ---- Summary ----
    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    n_warn = sum(1 for s, _, _ in results if s == WARN)
    print(f"\n=== Anomaly verification: {len(results) - n_fail - n_warn} passed, "
          f"{n_warn} warnings, {n_fail} failed ===")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())

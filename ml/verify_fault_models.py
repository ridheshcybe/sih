"""
ml/verify_fault_models.py -- Task 4.3 VERIFY: fault classifier + degradation/RUL.

Fault classifier checks:
  1. Model loads without errors.
  2. Correct fault type gets the highest probability on faulty test segments.
  3. "none" dominates on healthy test segments.
  4. Inference < 2 ms per sample.

Degradation/RUL checks:
  5. Models load without errors.
  6. Degradation is higher on faulty than healthy segments.
  7. Degradation increases with injected fault severity (sweep 0.2 -> 1.0).
  8. RUL decreases as degradation increases.
  9. Degradation + RUL inference < 5 ms combined.

Run:  .venv/bin/python ml/verify_fault_models.py
"""

import json
import os
import sys
import time
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.features import extract_features  # noqa: E402
from ml.generate_dataset import _base_window, apply_fault  # noqa: E402
from ml.inference import (  # noqa: E402
    predict_fault, predict_degradation, predict_rul, predict_all,
    _get, FAULT_CLASSES,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_PATH = os.path.join(ROOT, "data", "test.jsonl")

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
results = []


def check(name, ok, detail="", level=None):
    status = PASS if ok else (level or FAIL)
    results.append((status, name, detail))
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))
    return ok


def main():
    X, labels = [], []
    with open(TEST_PATH) as f:
        for line in f:
            s = json.loads(line)
            X.append(s["features"])
            labels.append(s["label"])
    X = np.asarray(X)
    labels = np.asarray(labels)

    # ---------- PART A: fault classifier ----------
    ok_load = all(_get(n) is not None for n in ("fault",))
    check("fault classifier loads without errors", ok_load)

    # Correct class wins on faulty segments
    correct, total = 0, 0
    per_class_correct = Counter()
    per_class_total = Counter()
    for x, lab in zip(X, labels):
        if lab == "none":
            continue
        probs = predict_fault(x)
        top = max(probs, key=probs.get)
        total += 1
        per_class_total[lab] += 1
        if top == lab:
            correct += 1
            per_class_correct[lab] += 1
    top1 = correct / max(total, 1)
    check("correct fault type has highest probability (faulty segments)",
          top1 >= 0.90, f"top-1 = {top1:.3f} over {total} faulty samples")
    weak = {c: f"{per_class_correct[c]}/{per_class_total[c]}"
            for c in per_class_total if per_class_correct[c] / per_class_total[c] < 0.8}
    if weak:
        print(f"[{WARN}] classes below 80% top-1: {weak}")

    # "none" dominates on healthy segments
    none_dom = 0
    none_total = 0
    for x, lab in zip(X, labels):
        if lab != "none":
            continue
        probs = predict_fault(x)
        none_total += 1
        if max(probs, key=probs.get) == "none":
            none_dom += 1
    none_rate = none_dom / max(none_total, 1)
    check("'none' dominates in healthy segments", none_rate >= 0.90,
          f"{none_dom}/{none_total} = {none_rate:.3f}")

    # Timing: < 2 ms per sample
    x1 = X[:1]
    predict_fault(x1)  # warm-up
    t0 = time.perf_counter()
    n = 200
    for _ in range(n):
        predict_fault(x1)
    fault_ms = 1e3 * (time.perf_counter() - t0) / n
    check("fault inference < 2 ms per sample", fault_ms < 2.0, f"{fault_ms:.2f} ms")

    # ---------- PART B: degradation + RUL ----------
    deg_ok = _get("degradation") is not None
    rul_ok = _get("rul") is not None
    check("degradation model loads without errors", deg_ok)
    check("rul model loads without errors", rul_ok)

    faulty_mask = labels != "none"
    deg_faulty = float(np.mean([predict_degradation(x) for x in X[faulty_mask]]))
    deg_healthy = float(np.mean([predict_degradation(x) for x in X[~faulty_mask]]))
    check("degradation higher on faulty than healthy segments",
          deg_faulty > deg_healthy,
          f"faulty={deg_faulty:.3f} vs healthy={deg_healthy:.3f}")

    # Severity sweep: degradation should rise with injected severity
    sweep = []
    for sev in np.linspace(0.2, 1.0, 5):
        win = _base_window()
        apply_fault(win, "injector_degradation", float(sev))
        sweep.append((sev, predict_degradation(extract_features(win))))
    monotone = all(b[1] > a[1] for a, b in zip(sweep, sweep[1:]))
    check("degradation increases with fault severity", monotone,
          " -> ".join(f"{s:.1f}:{d:.2f}" for s, d in sweep))

    # RUL must decrease as degradation increases (use swept points)
    rul_points = []
    for sev, deg in sweep:
        win = _base_window()
        apply_fault(win, "injector_degradation", float(sev))
        rul, conf = predict_rul(extract_features(win), deg)
        rul_points.append((deg, rul, conf))
    decreasing = all(b[1] < a[1] for a, b in zip(rul_points, rul_points[1:]))
    check("RUL decreases as degradation increases", decreasing,
          " -> ".join(f"deg={d:.2f}:rul={r:.0f}({c})" for d, r, c in rul_points))
    check("RUL confidence covers low/medium/high", len({c for _, _, c in rul_points}) > 1,
          f"confidences={[c for _, _, c in rul_points]}")

    # Timing: degradation + RUL combined < 5 ms
    predict_degradation(x1)
    predict_rul(x1, 0.5)
    t0 = time.perf_counter()
    for _ in range(n):
        d = predict_degradation(x1)
        predict_rul(x1, d)
    dr_ms = 1e3 * (time.perf_counter() - t0) / n
    check("degradation + RUL inference < 5 ms combined", dr_ms < 5.0, f"{dr_ms:.2f} ms")

    # End-to-end predict_all sanity
    out = predict_all(X[0])
    expected_keys = {"anomaly_score", "fault_probs", "degradation_level",
                     "rul_estimate", "rul_confidence"}
    probs_sum = sum(out["fault_probs"].values())
    check("predict_all returns complete payload", expected_keys == set(out.keys()),
          f"keys={sorted(out.keys())}")
    check("fault_probs sum to ~1.0", abs(probs_sum - 1.0) < 0.01, f"sum={probs_sum:.3f}")

    # ---------- Summary ----------
    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    n_warn = sum(1 for s, _, _ in results if s == WARN)
    print(f"\n=== Fault/degradation/RUL verification: "
          f"{len(results) - n_fail - n_warn} passed, {n_warn} warnings, {n_fail} failed ===")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())

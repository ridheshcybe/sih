#!/usr/bin/env bash
# scripts/train_verify_report.sh -- Train, verify, test and report every ML model.
#
# Pipeline for SIH26054 (aero piston engine digital twin):
#   1. preflight   check Python env + dataset
#   2. (optional)  regenerate data/train.jsonl + data/test.jsonl
#   3. train       ml/train_all_models.py   -> models/*.joblib
#   4. verify      ml/verify_anomaly.py, ml/verify_fault_models.py,
#                  ml/verify_integration.py
#   5. test        pytest suite
#   6. report      per-model statistics table -> reports/model_report_<ts>.md
#
# Usage:
#   scripts/train_verify_report.sh [options]
#
# Options:
#   --regen-data    Regenerate the synthetic dataset before training.
#   --skip-train    Reuse the existing models/ (implies no dataset regen).
#   --skip-tests    Skip the pytest suite.
#   --help          Show this help.
#
# Exit code: 0 only if every executed step passed.

set -uo pipefail

# ---------------------------------------------------------------- locations --
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT" || exit 1

MODELS_DIR="$ROOT/models"
DATA_DIR="$ROOT/data"
LOG_DIR="$ROOT/reports/logs"
STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_PATH="$ROOT/reports/model_report_${STAMP}.md"

# ------------------------------------------------------------------- options --
REGEN_DATA=0
SKIP_TRAIN=0
SKIP_TESTS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --regen-data) REGEN_DATA=1; shift ;;
    --skip-train) SKIP_TRAIN=1; shift ;;
    --skip-tests) SKIP_TESTS=1; shift ;;
    -h|--help)
      sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Unknown option: $1 (use --help)" >&2; exit 2 ;;
  esac
done

# ------------------------------------------------------------------- colors --
if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'
  C_GREEN=$'\033[32m'; C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'
else
  C_RESET=""; C_BOLD=""; C_GREEN=""; C_RED=""; C_YELLOW=""; C_BLUE=""
fi

section() { printf '\n%s%s==> %s%s\n' "$C_BOLD" "$C_BLUE" "$1" "$C_RESET"; }
ok()      { printf '%s[PASS]%s %s\n' "$C_GREEN" "$C_RESET" "$1"; }
bad()     { printf '%s[FAIL]%s %s\n' "$C_RED" "$C_RESET" "$1"; }
warn()    { printf '%s[WARN]%s %s\n' "$C_YELLOW" "$C_RESET" "$1"; }

STEP_NAMES=(); STEP_STATUS=()
OVERALL=0

record() { STEP_NAMES+=("$1"); STEP_STATUS+=("$2"); }

# run_step <label> <logfile> <cmd...>
run_step() {
  local label="$1" log="$2"; shift 2
  section "$label"
  if "$@" 2>&1 | tee "$log"; then
    ok "$label"
    record "$label" "PASS"
  else
    bad "$label (exit $?) -- see $log"
    record "$label" "FAIL"
    OVERALL=1
  fi
}

# ---------------------------------------------------------------- preflight --
find_python() {
  local candidates=(".venv/bin/python" "venv/bin/python" "myenv/bin/python" "python3" "python")
  local p
  for p in "${candidates[@]}"; do
    if [[ -x "$ROOT/$p" ]]; then echo "$ROOT/$p"; return 0; fi
    if command -v "$p" >/dev/null 2>&1; then command -v "$p"; return 0; fi
  done
  return 1
}

section "Preflight"
mkdir -p "$LOG_DIR"
PY="$(find_python)" || { bad "no Python interpreter found"; exit 1; }
printf 'root   : %s\npython : %s\n' "$ROOT" "$PY"
"$PY" --version || true

if ! "$PY" -c "import sklearn, joblib, numpy" >/dev/null 2>&1; then
  bad "missing Python deps (scikit-learn / joblib / numpy)."
  echo "      install with: $PY -m pip install -r requirements.txt"
  exit 1
fi
ok "Python dependencies present"

if [[ "$REGEN_DATA" -eq 0 && ! -f "$DATA_DIR/train.jsonl" ]]; then
  warn "data/train.jsonl missing -- enabling --regen-data"
  REGEN_DATA=1
fi

# ------------------------------------------------------------- 1. dataset --
if [[ "$REGEN_DATA" -eq 1 ]]; then
  run_step "Regenerate synthetic dataset" "$LOG_DIR/generate_dataset_${STAMP}.log" \
    "$PY" ml/generate_dataset.py
else
  section "Dataset"
  printf 'reusing existing dataset:\n'
  wc -l "$DATA_DIR/train.jsonl" "$DATA_DIR/test.jsonl" 2>/dev/null || true
fi

# --------------------------------------------------------------- 2. train --
if [[ "$SKIP_TRAIN" -eq 1 ]]; then
  section "Train models"
  warn "skipped (--skip-train); using existing models in $MODELS_DIR"
else
  run_step "Train all models" "$LOG_DIR/train_all_models_${STAMP}.log" \
    "$PY" ml/train_all_models.py
fi

# -------------------------------------------------------------- 3. verify --
run_step "Verify anomaly model"        "$LOG_DIR/verify_anomaly_${STAMP}.log" \
  "$PY" ml/verify_anomaly.py
run_step "Verify fault/degradation/RUL" "$LOG_DIR/verify_fault_models_${STAMP}.log" \
  "$PY" ml/verify_fault_models.py
run_step "Verify backend integration"  "$LOG_DIR/verify_integration_${STAMP}.log" \
  "$PY" ml/verify_integration.py

# ---------------------------------------------------------------- 4. test --
if [[ "$SKIP_TESTS" -eq 1 ]]; then
  section "Tests"
  warn "skipped (--skip-tests)"
else
  run_step "Pytest suite" "$LOG_DIR/pytest_${STAMP}.log" \
    "$PY" -m pytest -q
fi

# -------------------------------------------------------------- 5. report --
section "Per-model statistics report"
if "$PY" - "$REPORT_PATH" <<'PYEOF' 2>&1 | tee "$LOG_DIR/report_${STAMP}.log"
import datetime
import json
import os
import sys
import time

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score, f1_score, mean_absolute_error, mean_squared_error,
    precision_recall_fscore_support, r2_score, roc_auc_score,
)

report_path = sys.argv[1]

# --------------------------------------------------------------- load data --
def load_jsonl(path):
    X, labels, deg, rul = [], [], [], []
    with open(path) as fh:
        for line in fh:
            s = json.loads(line)
            X.append(s["features"])
            labels.append(s.get("label", "none"))
            deg.append(float(s.get("degradation", 0.0)))
            rul.append(float(s.get("rul", 120.0)))
    return (np.asarray(X, dtype=float), np.asarray(labels),
            np.asarray(deg, dtype=float), np.asarray(rul, dtype=float))


X_tr, y_tr, deg_tr, rul_tr = load_jsonl("data/train.jsonl")
X_te, y_te, deg_te, rul_te = load_jsonl("data/test.jsonl")

MODELS = {
    "anomaly":     "models/anomaly_model.joblib",
    "fault":       "models/fault_classifier.joblib",
    "degradation": "models/degradation_model.joblib",
    "rul":         "models/rul_model.joblib",
}


def load(name):
    path = MODELS[name]
    if not os.path.exists(path):
        return None, path
    try:
        return joblib.load(path), path
    except Exception as exc:  # corrupt / incompatible pickle
        print(f"  ! failed to load {path}: {exc}")
        return None, path


def model_type(model):
    return type(model).__name__


def size_kb(path):
    return os.path.getsize(path) / 1024 if os.path.exists(path) else 0.0


def mtime(path):
    if not os.path.exists(path):
        return "n/a"
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")


def latency_ms(fn, n=100):
    fn()
    t0 = time.perf_counter()
    for _ in range(n):
        fn()
    return 1e3 * (time.perf_counter() - t0) / n


def fmt(v, nd=4):
    if isinstance(v, str):
        return v
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    return f"{float(v):.{nd}f}"


# --------------------------------------------------------- registry output --
summary_rows = []      # (model, metric, value)
detail_blocks = []     # markdown sections


def add(model, metric, value):
    summary_rows.append((model, metric, value))


anom, path = load("anomaly")
if anom is not None:
    scores = -anom.score_samples(X_te)
    y_bin = (y_te != "none").astype(int)
    hs, fs = scores[y_bin == 0], scores[y_bin == 1]
    auroc = roc_auc_score(y_bin, scores)
    p = anom.get_params()
    lat = latency_ms(lambda: -anom.score_samples(X_te[:1]))
    add("anomaly", "test AUROC", auroc)
    add("anomaly", "healthy mean score", float(hs.mean()))
    add("anomaly", "faulty mean score", float(fs.mean()))
    add("anomaly", "separation (faulty-healthy)", float(fs.mean() - hs.mean()))
    add("anomaly", "latency / window (ms)", lat)
    detail_blocks.append(f"""### 1. Anomaly detection -- `{model_type(anom)}`
| property | value |
|---|---|
| file | `{path}` ({size_kb(path):.1f} KB, {mtime(path)}) |
| estimators | {p.get('n_estimators')} |
| contamination | {p.get('contamination')} |
| trained on | healthy-only, unsupervised |
| **test AUROC** | **{auroc:.4f}** |
| healthy mean score | {float(hs.mean()):.4f} |
| faulty mean score | {float(fs.mean()):.4f} |
| separation | {float(fs.mean() - hs.mean()):.4f} |
| inference latency | {lat:.2f} ms / window (single sample) |
""")

clf, path = load("fault")
if clf is not None:
    pred = clf.predict(X_te)
    acc = accuracy_score(y_te, pred)
    f1m = f1_score(y_te, pred, average="macro")
    f1w = f1_score(y_te, pred, average="weighted")
    prec, rec, f1, sup = precision_recall_fscore_support(y_te, pred, zero_division=0)
    classes = list(clf.classes_)
    faulty = y_te != "none"
    top1 = float(np.mean(pred[faulty] == y_te[faulty])) if faulty.any() else 0.0
    none_rate = float(np.mean(pred[y_te == "none"] == "none"))
    p = clf.get_params()
    lat = latency_ms(lambda: clf.predict_proba(X_te[:1]))
    add("fault", "test accuracy", acc)
    add("fault", "macro F1", f1m)
    add("fault", "weighted F1", f1w)
    add("fault", "top-1 (faulty only)", top1)
    add("fault", "'none' recall (healthy)", none_rate)
    add("fault", "latency / sample (ms)", lat)
    per_class = "\n".join(
        f"| `{c}` | {pr:.4f} | {rc:.4f} | {fb:.4f} | {int(n)} |"
        for c, pr, rc, fb, n in zip(classes, prec, rec, f1, sup)
    )
    detail_blocks.append(f"""### 2. Fault classifier -- `{model_type(clf)}`
| property | value |
|---|---|
| file | `{path}` ({size_kb(path):.1f} KB, {mtime(path)}) |
| estimators | {p.get('n_estimators')} |
| max depth | {p.get('max_depth')} |
| classes | {[str(c) for c in classes]} |
| **test accuracy** | **{acc:.4f}** |
| macro F1 | {f1m:.4f} |
| weighted F1 | {f1w:.4f} |
| top-1 on faulty segments | {top1:.4f} |
| 'none' recall on healthy | {none_rate:.4f} |
| inference latency | {lat:.2f} ms / sample |

| class | precision | recall | F1 | support |
|---|---|---|---|---|
{per_class}
""")

deg, path = load("degradation")
deg_pred_te = None
if deg is not None:
    deg_pred_te = np.clip(deg.predict(X_te), 0.0, 1.0)
    mae = mean_absolute_error(deg_te, deg_pred_te)
    rmse = float(np.sqrt(mean_squared_error(deg_te, deg_pred_te)))
    r2 = r2_score(deg_te, deg_pred_te)
    faulty = y_te != "none"
    d_f = float(deg_pred_te[faulty].mean())
    d_h = float(deg_pred_te[~faulty].mean())
    p = deg.get_params()
    lat = latency_ms(lambda: deg.predict(X_te[:1]))
    add("degradation", "test MAE", mae)
    add("degradation", "test RMSE", rmse)
    add("degradation", "test R2", r2)
    add("degradation", "faulty mean", d_f)
    add("degradation", "healthy mean", d_h)
    add("degradation", "latency / sample (ms)", lat)
    detail_blocks.append(f"""### 3. Degradation regressor -- `{model_type(deg)}`
| property | value |
|---|---|
| file | `{path}` ({size_kb(path):.1f} KB, {mtime(path)}) |
| estimators | {p.get('n_estimators')} |
| max depth | {p.get('max_depth')} |
| learning rate | {p.get('learning_rate')} |
| target | degradation level in [0, 1] |
| **test MAE** | **{mae:.4f}** |
| test RMSE | {rmse:.4f} |
| test R2 | {r2:.4f} |
| faulty mean prediction | {d_f:.4f} |
| healthy mean prediction | {d_h:.4f} |
| inference latency | {lat:.2f} ms / sample |
""")

rul, path = load("rul")
if rul is not None and deg_pred_te is not None:
    Xr_te = np.hstack([X_te, deg_pred_te.reshape(-1, 1)])
    rul_pred = rul.predict(Xr_te)
    mae = mean_absolute_error(rul_te, rul_pred)
    rmse = float(np.sqrt(mean_squared_error(rul_te, rul_pred)))
    r2 = r2_score(rul_te, rul_pred)
    corr = float(np.corrcoef(deg_pred_te, rul_pred)[0, 1])
    p = rul.get_params()
    lat = latency_ms(lambda: rul.predict(Xr_te[:1]))
    add("rul", "test MAE (missions)", mae)
    add("rul", "test RMSE (missions)", rmse)
    add("rul", "test R2", r2)
    add("rul", "corr(degradation, RUL)", corr)
    add("rul", "latency / sample (ms)", lat)
    detail_blocks.append(f"""### 4. RUL regressor -- `{model_type(rul)}`
| property | value |
|---|---|
| file | `{path}` ({size_kb(path):.1f} KB, {mtime(path)}) |
| inputs | 54 features + predicted degradation |
| fit intercept | {p.get('fit_intercept')} |
| target | remaining useful life (missions) |
| **test MAE** | **{mae:.2f} missions** |
| test RMSE | {rmse:.2f} missions |
| test R2 | {r2:.4f} |
| corr(degradation, RUL) | {corr:.4f} (expect strongly negative) |
| inference latency | {lat:.2f} ms / sample |
""")

# ------------------------------------------------------------ console view --
print(f"\nmodel        metric                        value")
print("-" * 58)
for model, metric, value in summary_rows:
    print(f"{model:<12} {metric:<29} {fmt(value)}")

print(f"\nmodels loaded: "
      f"{[n for n, p in MODELS.items() if os.path.exists(p)]}")
missing = [n for n, p in MODELS.items() if not os.path.exists(p)]
if missing:
    print(f"models MISSING: {missing} -- run without --skip-train")

# ------------------------------------------------------------- markdown ----
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
table = "\n".join(
    f"| {m} | {metric} | {fmt(v)} |" for m, metric, v in summary_rows
)
md = f"""# ML Model Report -- SIH26054

Generated: {now}
Dataset: `data/train.jsonl` ({len(X_tr)} samples), `data/test.jsonl` ({len(X_te)} samples)

## Summary

| model | metric | value |
|---|---|---|
{table}

## Per-model detail

{os.linesep.join(detail_blocks)}

---
*Synthetic data only; not flight-certified.*
"""

os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, "w") as fh:
    fh.write(md)
print(f"\nMarkdown report written to: {report_path}")
PYEOF
then
  ok "Per-model statistics report"
  record "Report model statistics" "PASS"
else
  bad "Per-model statistics report"
  record "Report model statistics" "FAIL"
  OVERALL=1
fi

# -------------------------------------------------------------- summary ----
section "Pipeline summary"
i=0
while [[ $i -lt ${#STEP_NAMES[@]} ]]; do
  if [[ "${STEP_STATUS[$i]}" == "PASS" ]]; then ok "${STEP_NAMES[$i]}"; else bad "${STEP_NAMES[$i]}"; fi
  i=$((i + 1))
done
printf '\nreport : %s\nlogs   : %s\n' "$REPORT_PATH" "$LOG_DIR"

if [[ "$OVERALL" -eq 0 ]]; then
  printf '%sAll steps passed.%s\n' "$C_GREEN$C_BOLD" "$C_RESET"
else
  printf '%sOne or more steps failed.%s\n' "$C_RED$C_BOLD" "$C_RESET"
fi
exit "$OVERALL"

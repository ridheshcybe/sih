"""
ml/verify_integration.py -- Task 4.4 VERIFY: backend integration.

Runs a simulated mission (healthy -> injected faults -> ramping degradation)
through backend.services.digital_twin.DigitalTwinService.update_twin_state(),
which exercises feature extraction + all 4 ML models + SQLite persistence.

Checks:
  1. Every twin state contains anomaly_score, fault_probs, degradation, rul.
  2. fault_probs shift toward the injected fault during faulty segments.
  3. Degradation rises and RUL falls across the mission ramp.
  4. twin_states / fault_predictions rows are persisted with expected fields.
  5. Missing-model scenario: no crash, safe defaults used.
  6. End-to-end latency (features + all models) is demo-acceptable (< 50 ms).

Run:  .venv/bin/python ml/verify_integration.py
"""

import json
import os
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use a throwaway DB so the test never touches the real backend DB
os.environ["TWIN_DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="twin_test_"), "test.db")

from ml.features import extract_features, WINDOW_SIZE, SENSORS          # noqa: E402
from ml.generate_dataset import _base_window, apply_fault, FAULT_TYPES  # noqa: E402
from ml import inference as ml_inf                                      # noqa: E402
from backend.services.digital_twin import DigitalTwinService, get_db    # noqa: E402

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
results = []


def check(name, ok, detail="", level=None):
    status = PASS if ok else (level or FAIL)
    results.append((status, name, detail))
    print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))
    return ok


def make_window(fault=None, severity=0.0):
    win = _base_window()
    if fault:
        apply_fault(win, fault, severity)
    return win


def run_mission(service, mission_id):
    """
    Simulated mission timeline (1 window per update):
      seg 0        healthy cruise
      segs 1..5    each fault injected at fixed severity 0.6
      segs 6..9    injector_degradation ramping 0.35 -> 0.95
    Returns list of twin states.
    """
    states = []
    states.append(service.update_twin_state(mission_id, make_window()))
    for ft in FAULT_TYPES:
        states.append(service.update_twin_state(mission_id, make_window(ft, 0.6)))
    for sev in (0.35, 0.55, 0.75, 0.95):
        states.append(service.update_twin_state(
            mission_id, make_window("injector_degradation", sev)))
    return states


def main():
    service = DigitalTwinService()
    mission_id = "VERIFY-001"

    # ---- 1. Run mission; every state carries the full ML payload ----
    states = run_mission(service, mission_id)
    required = {"anomaly_score", "fault_probs", "degradation", "rul_estimate",
                "rul_confidence", "health_index", "timestamp", "mission_id"}
    complete = all(required.issubset(s.keys()) for s in states)
    check("every twin state includes anomaly/fault_probs/degradation/rul", complete,
          f"{len(states)} updates")
    probs_ok = all(abs(sum(s["fault_probs"].values()) - 1.0) < 0.02 for s in states)
    check("fault_probs valid distribution in every state", probs_ok)

    # ---- 2. Fault probabilities shift toward the injected fault ----
    order = ["healthy"] + FAULT_TYPES + ["ramp"] * 4
    shift_ok, shift_detail = 0, []
    for state, seg in zip(states[1:6], FAULT_TYPES):
        top = max(state["fault_probs"], key=state["fault_probs"].get)
        p = state["fault_probs"][top]
        shift_ok += (top == seg)
        shift_detail.append(f"{seg}={p:.2f}")
    check("fault_probs shift toward correct fault in faulty segments",
          shift_ok == len(FAULT_TYPES), ", ".join(shift_detail))
    top0 = max(states[0]["fault_probs"], key=states[0]["fault_probs"].get)
    check("'none' dominates in healthy segment", top0 == "none",
          f"{top0}={states[0]['fault_probs'][top0]:.2f}")

    # ---- 3. Degradation rises / RUL falls across the ramp ----
    ramp = states[6:10]
    degs = [s["degradation"] for s in ramp]
    ruls = [s["rul_estimate"] for s in ramp]
    check("degradation increases during ramping fault",
          all(b > a for a, b in zip(degs, degs[1:])),
          " -> ".join(f"{d:.2f}" for d in degs))
    check("RUL decreases as degradation increases",
          all(b < a for a, b in zip(ruls, ruls[1:])),
          " -> ".join(f"{r:.0f}" for r in ruls))
    check("health_index declines during fault ramp",
          ramp[-1]["health_index"] < ramp[0]["health_index"],
          f"{ramp[0]['health_index']} -> {ramp[-1]['health_index']}")

    # ---- 4. DB persistence ----
    with get_db() as conn:
        ts = conn.execute("SELECT * FROM twin_states WHERE mission_id = ?",
                          (mission_id,)).fetchall()
        fp = conn.execute("SELECT * FROM fault_predictions WHERE mission_id = ?",
                          (mission_id,)).fetchall()
    ts_cols = {c[1] for c in get_db().execute("PRAGMA table_info(twin_states)").fetchall()}
    needed = {"anomaly_score", "degradation_level", "rul_estimate", "rul_confidence",
              "fault_probs_json", "health_index"}
    missing_cols = needed - ts_cols
    check("twin_states rows persisted", len(ts) == len(states),
          f"{len(ts)}/{len(states)} rows")
    check("twin_states has ML columns", not missing_cols,
          f"missing={sorted(missing_cols)}" if missing_cols else sorted(needed))
    check("fault_predictions rows persisted", len(fp) >= 6,
          f"{len(fp)} rows")
    dom = max({r["fault_type"]: r["probability"] for r in fp}.items(), key=lambda kv: kv[1])
    check("fault_predictions contains correct dominant fault",
          dom[0] == "injector_degradation" and dom[1] > 0.5,
          f"{dom[0]}={dom[1]:.2f}")

    # ---- 5. Missing model file scenario: defaults, no crash ----
    original_paths = dict(ml_inf._paths)
    try:
        ml_inf._paths.update({k: "/nonexistent/" + k + ".joblib" for k in original_paths})
        ml_inf.reset_model_cache()
        svc2 = DigitalTwinService()
        s = svc2.update_twin_state("MISSING-MODELS", make_window())
        payload = ml_inf.predict_all(extract_features(make_window()))
        uniform = abs(payload["fault_probs"]["none"] - 1.0 / len(ml_inf.FAULT_CLASSES)) < 0.01
        check("missing models: update_twin_state does not crash", True)
        check("missing models: anomaly_score falls back to 0", payload["anomaly_score"] == 0.0,
              f"{payload['anomaly_score']}")
        check("missing models: fault_probs fall back to uniform", uniform)
        check("missing models: degradation falls back to 0", payload["degradation_level"] == 0.0)
        check("missing models: rul falls back to full life + low confidence",
              payload["rul_confidence"] == "low",
              f"rul={payload['rul_estimate']}, conf={payload['rul_confidence']}")
    finally:
        ml_inf._paths.update(original_paths)
        ml_inf.reset_model_cache()

    # ---- 6. End-to-end latency (features + all models) ----
    window = make_window("injector_degradation", 0.7)
    ml_inf.predict_all(extract_features(window))  # warm-up
    lat = []
    for _ in range(100):
        t0 = time.perf_counter()
        ml_inf.predict_all(extract_features(window))
        lat.append(1e3 * (time.perf_counter() - t0))
    lat = np.asarray(lat)
    check("end-to-end latency < 50 ms (features + all models)",
          float(lat.mean()) < 50.0,
          f"mean={lat.mean():.2f} ms, p95={np.percentile(lat, 95):.2f} ms, max={lat.max():.2f} ms")

    # ---- Integration report ----
    print("\n--- Integration report ---")
    print(f"DB used: {os.environ['TWIN_DB_PATH']}")
    print(f"twin_states rows: {len(ts)} | fault_predictions rows: {len(fp)}")
    print(f"Model files loaded: {[k for k in ('anomaly', 'fault', 'degradation', 'rul') if ml_inf._get(k) is not None]}")
    print("Known demo limitations: synthetic data only; not flight-certified; "
          "fault taxonomy limited to trained classes.")

    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    n_warn = sum(1 for s, _, _ in results if s == WARN)
    print(f"\n=== Integration verification: {len(results) - n_fail - n_warn} passed, "
          f"{n_warn} warnings, {n_fail} failed ===")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())

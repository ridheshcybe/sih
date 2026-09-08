# Model Card — SIH26054 ML Pipeline

## Models (PyTorch, GPU-trained — primary)

| Model | Architecture | Input | Output | File |
|---|---|---|---|---|
| Anomaly detection | Undercomplete autoencoder (64→32) | 78-dim feature vector | reconstruction error → z-score → 0–1 (EMA-smoothed) | `models/anomaly_autoencoder.pt` |
| Fault classifier | MLP (128→64), softmax | 78-dim feature vector | probabilities over 8 classes (`none`, misfire, injector_degradation, lubrication_issue, overheating, sensor_drift, abnormal_vibration, battery_alternator_degradation) | `models/fault_mlp.pt` |
| Degradation | MLP (128→64), sigmoid out | 78-dim feature vector | degradation level 0–1 | `models/degradation_mlp.pt` |
| RUL | MLP (128→64), relu out | 78-dim features + degradation | RUL hours (0–500) + confidence (low/medium/high) | `models/rul_mlp.pt` |

Each model ships with a `torch_*_meta.json` (feature names, classes,
standardization mean/std) that must travel with the `.pt` file. Training:
`docs/gpu_training.md`, script `ml/train_gpu.py`.

## Optional scikit-learn baselines (CPU)

`models/anomaly_model.joblib` (Isolation Forest on healthy windows),
`models/fault_classifier.joblib` (Random Forest), `models/degradation_model.joblib`
and `models/rul_model.joblib` (Random Forest regressors) — trained by
`ml/train_*.py`. Inference prefers the PyTorch models when both exist.

## Features (78 dims, per 3 s window)

- For each of 12 sensor channels (`rpm, cht, egt, oil_pressure, oil_temperature,
  fuel_flow, vibration_rms, battery_voltage, alternator_current, injection_timing,
  altitude, ambient_temperature`): **last value, mean, std, min, max, slope**.
- Physics residuals (observed − expected) for `cht, egt, oil_pressure,
  oil_temperature, vibration_rms, fuel_flow`. Expected values come from a
  stateful **healthy-model twin** driven by the same control inputs
  (throttle/altitude/ambient), so transients and noise cancel and residuals
  equal the pure fault signature.
- Missing values are interpolated; windows never cross mission boundaries.

## Training data

- **Source:** synthetic telemetry from the physics-inspired simulator.
- **Size:** 40 missions (160k rows) across 4 profiles; ~40% healthy,
  ~60% faulty (each of the 7 faults at varied severities).
- **Split:** train/val/test **by mission** (70/15/15) — no mission leakage.
- **Determinism:** fixed seeds and a fixed mission epoch — identical data and
  runs on every machine.

## Intended use

- Research/education prototype and hackathon demonstration only.
- Operator-facing demo of anomaly detection, fault classification, degradation
  tracking, and RUL estimation on synthetic data.

## Limitations

- **Synthetic data:** models have only seen simulated telemetry; they will not
  transfer to real engines without retraining on real (or HIL) data.
- **Not flight-certified.** No claims about real-world accuracy, false-alarm
  rates, or deployment readiness.
- RUL confidence is heuristic (derived from degradation level), not calibrated.
- Health Index and advisories are rule-based aggregations over ML outputs —
  interpretable, but not physics-validated.

## Fallback behavior (no models trained)

When model files are missing, the backend logs warnings and degrades safely:

- **Anomaly score:** rule-based residual z-score (observed vs healthy-model
  twin) — still rises clearly when faults are injected.
- **Fault label:** the simulator's ground-truth fault label is surfaced as the
  predicted fault so detections/advisories still stream (no-ML demo mode).
- **Degradation:** residual-derived proxy; **RUL:** 500 h nominal.
- Health Index drop and maintenance advisories therefore still work before
  training — training replaces the proxies with learned predictions.

## Evaluation metrics

Reported by `ml/train_gpu.py` on the test split:

- anomaly: mean/p95 score on healthy vs faulty segments (autoencoder
  reconstruction z-score).
- fault: test accuracy + per-class precision/recall/F1.
- degradation / RUL: test MAE and R².
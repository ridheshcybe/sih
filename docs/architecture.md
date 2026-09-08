# Architecture — SIH26054 Digital Twin

## Overview

```
┌──────────────────┐   REST + WS   ┌────────────────────────┐   ┌───────────────┐
│ React Dashboard  │◄────────────►│  FastAPI Backend        │──►│   SQLite DB   │
│ (localhost:3000) │  /api/v1 +    │  (localhost:8000)      │   │ data/sih26054 │
└──────────────────┘  /ws/telemetry└───────────┬────────────┘   └───────────────┘
                                               │
                                     ┌─────────▼─────────┐
                                     │  ML Inference     │◄── models/*.joblib
                                     │  (scikit-learn)   │
                                     └───────────────────┘
                                               ▲
                                     ┌─────────┴─────────┐
                                     │  Simulator        │  (in-process runner OR
                                     │  (engine model)   │   standalone --stream)
                                     └───────────────────┘
```

## Components

### 1. Simulator (`simulator/`)
- `engine_model.py` — stateful, physics-inspired model: RPM/EGT/CHT/oil
  pressure & temperature/fuel flow/vibration/battery/alternator/injection
  timing from throttle, altitude, ambient temperature (first-order lags + noise).
- `mission_profiles.py` — 4 profiles (standard ISR, high altitude, hot weather,
  aggressive) as phase sequences (startup → takeoff → climb → cruise →
  endurance → descent → landing → shutdown).
- `fault_injection.py` — 7 fault types with sudden/gradual envelopes scaled by
  severity; produces `fault_label`, `fault_severity`, `degradation_level`,
  `rul_label`.
- `simulate.py` / `generate_dataset.py` — mission simulation and train/val/test
  dataset generation (split **by mission**, no leakage).

### 2. ML pipeline (`ml/`)
- `feature_extractor.py` — fixed 78-dim vector per 3 s window: last value +
  mean/std/min/max/slope per sensor, plus physics residuals (observed − expected).
- Training: `train_anomaly.py` (Isolation Forest, healthy-only windows),
  `train_fault_classifier.py` (Random Forest, 8 classes), `train_degradation_rul.py`
  (two Random Forest regressors).
- `inference.py` — `Predictor.predict_all()` with EMA smoothing and **safe
  fallback defaults if any model file is missing**.

### 3. Backend (`backend/`)
- `main.py` — FastAPI app, CORS, lifespan (init DB, preload ML, default engine),
  WebSocket endpoint `/ws/telemetry/{engine_id}`.
- `services/digital_twin.py` — per row: expected values, residuals, feature
  window → ML inference → Health Index/status → advisory; persists twin state,
  fault predictions, advisories.
- `services/simulation_runner.py` — in-process mission loop at 10 Hz
  (ingest → twin → broadcast) + mission replay at 5x.
- `services/ws_manager.py` — per-engine client registry, throttled broadcast
  (max 5 msg/s/client, newest supersedes).
- `services/reports.py` — mission diagnostic summary (health stats, fault
  counts, advisories, final RUL).

### 4. Frontend (`frontend/`)
- Dashboard: Health gauge, RUL/anomaly/degradation strip, 4 live charts
  (Health/Anomaly, EGT/CHT, RPM/OilP, Vibration), alerts panel, telemetry
  table, mission controls, fault injector, replay controls.
- Missions / Reports pages. WebSocket auto-reconnect with exponential backoff;
  5 s REST polling as a fallback. Vite proxies `/api` and `/ws` to the backend.

## Data flow (one telemetry row @ 10 Hz)

```
simulator step ─► ingest (validate + store) ─► digital twin
   (expected sensors, residuals, feature window)
      ─► ML predict_all (anomaly, fault probs, degradation, RUL)
      ─► Health Index + status + advisory
      ─► persist (twin_states, fault_predictions, maintenance_advisories)
      ─► broadcast (telemetry_update, twin_state_update, fault_prediction)
```

## Non-functional notes

- End-to-end latency ≪ 200 ms budget (models are tree-based, inference < 5 ms).
- WS throttling protects the browser from 10 Hz rendering storms; the UI
  re-renders chart series at 500 ms cadence.
- ML failure is non-fatal: missing/corrupt model ⇒ default predictions + warning log.
- SQLite is per-process; restart recreates schema, data persists in `data/`.

## Known limits

- Single engine (ENG-001) focus; multi-engine is a schema/UI extension.
- Replay recomputes twin state from stored telemetry (does not duplicate rows).
- No auth, no TLS — local demo only.
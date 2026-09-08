# SIH26054 — AI-Enabled Digital Twin for Aero Piston Engines (MALE UAV)

An AI-powered real-time digital twin system for **health monitoring, fault prediction,
and mission-reliability enhancement** of aero piston engines used in MALE UAVs
(DRDO / iDEX problem statement SIH26054).

> **Disclaimer:** This is a hackathon software demonstrator. It runs on **realistic
> synthetic telemetry** and makes **no claim of flight certification or real-engine
> validation**.

## What it does

- Simulates a piston engine through realistic mission profiles (ISR, high-altitude,
  hot-weather, aggressive) at 10 Hz.
- Injects 7 fault types (misfire, injector degradation, lubrication issue,
  overheating, sensor drift, abnormal vibration, battery/alternator degradation).
- Computes a **digital twin state** per telemetry row: physics-based expected
  values, residuals, Health Index (0–100), anomaly score, degradation level,
  Remaining Useful Life (RUL) and maintenance advisories.
- Streams everything to a React dashboard over WebSockets.
- Records missions and generates post-mission diagnostic reports; supports
  mission replay.

## Tech stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + Uvicorn, SQLAlchemy, SQLite |
| Real-time | WebSockets (throttled to 5 msg/s/client) |
| ML | **PyTorch (GPU-trained, CPU inference)**; optional scikit-learn baselines |
| Simulator | Python + NumPy + Pandas |
| Frontend | React 18 + Vite + Recharts |
| Tests | pytest |

## Repository structure

```
project-root/
  backend/     FastAPI app: routers, services (ingest, digital twin, ML glue,
               WebSocket manager, simulation runner), SQLAlchemy models
  frontend/    React dashboard (Vite): live charts, twin state, mission controls
  ml/          Feature extractor, training scripts, inference service
  simulator/   Physics-inspired engine model, mission profiles, fault injection,
               dataset generation
  models/      Trained artifacts (anomaly, fault classifier, degradation, RUL)
  data/        Generated synthetic datasets (train/val/test CSV + DB)
  docs/        Architecture, API contract, task board, demo script, model card
  scripts/     setup.sh, train_all.sh, start_demo.sh, ...
  tests/       pytest smoke tests (simulator + backend)
```

## Quickstart (laptop-friendly)

### 1. Setup (once)

```bash
bash scripts/setup.sh        # creates .venv, installs pip + npm deps
```

### 2. Train the ML models (on your GPU server farm)

Training is designed for a CUDA machine — see `docs/gpu_training.md` for the
full guide. Short version:

```bash
# on the GPU server
pip install torch --index-url https://download.pytorch.org/whl/cu124   # match your driver
pip install -r requirements-gpu.txt
bash scripts/train_gpu.sh --device auto          # trains all 4 models, ~25 epochs
# copy models/*.pt + models/torch_*_meta.json back to the laptop models/
```

This trains with PyTorch (autoencoder for anomaly, MLP classifier, two MLP
regressors) and prints test metrics. The synthetic dataset is generated
automatically on first run (identical on every machine, fixed seed).

> **No models? No problem.** The backend runs fine **without** any trained
> models — it falls back to rule-based residual monitoring (anomaly score,
> Health Index drop, advisories all still work) and logs warnings. Train when
> you're ready; just restart the backend to pick up the new artifacts.

Optional CPU baselines (`bash scripts/train_all.sh`, scikit-learn) still exist
under `ml/train_*.py` if you want quick laptop checks — inference prefers the
PyTorch models when both are present.

### 3. Run the demo

```bash
bash scripts/start_demo.sh
```

- Dashboard → http://localhost:3000
- API docs → http://localhost:8000/docs

Or run components manually in three terminals:

```bash
# Terminal 1 - backend
.venv/bin/python -m uvicorn backend.main:app --reload --port 8000   # or .venv/Scripts/python.exe on Windows

# Terminal 2 - frontend
cd frontend && npm run dev

# Terminal 3 - standalone simulator (optional; the backend can run its own)
.venv/bin/python -m simulator.run_simulation --profile standard_isr --duration 300 \
    --fault-type injector_degradation --severity 0.6 --fault-start 60 --stream
```

### 4. Demo in the browser

1. On the Dashboard, pick a profile (e.g. `standard_isr`) and click **Start Mission**.
2. Watch Health Index, RPM/EGT/CHT charts and the telemetry table stream live.
3. Pick a fault (e.g. `injector_degradation`), set severity, click **Inject Fault**.
4. Watch anomaly score rise, Health Index fall, RUL count down and an advisory appear.
5. Click **Stop Mission**, then **Replay (5x)** to replay the mission, and open
   **Reports** to see the generated diagnostic summary.

## Manual commands

```bash
# Regenerate the dataset (train/val/test split by mission, no leakage)
.venv/bin/python -m simulator.generate_dataset --missions 40 --rows-per-mission 4000

# Train models (GPU farm)
.venv/bin/python -m ml.train_gpu --task all --device auto      # PyTorch + CUDA
# or CPU baselines (scikit-learn)
.venv/bin/python -m ml.train_anomaly
.venv/bin/python -m ml.train_fault_classifier
.venv/bin/python -m ml.train_degradation_rul

# Run a single mission to CSV
.venv/bin/python -m simulator.run_simulation --profile hot_weather \
    --fault-type overheating --output data/mission.csv

# Run tests (works with or without trained models)
.venv/bin/python -m pytest tests/ -q
```

## Documentation

- `docs/architecture.md` — system design and data flow
- `docs/api_contract.md` — REST endpoints + WebSocket messages
- `docs/gpu_training.md` — **train on your GPU server farm**
- `docs/task_board.md` — team task status and risks
- `docs/demo_script.md` — 5-minute and 2-minute demo scripts
- `docs/model_card.md` — ML models, data, metrics, limitations
- `PROJECT_PLAN.md` — the original planning document

---

*Synthetic data only. Not flight-certified; requires real-engine validation.*
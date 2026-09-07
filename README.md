# SIH26054: AI-Enabled Digital Twin for Aero Piston Engines

An AI-powered real-time digital twin system for monitoring, predicting faults, and enhancing mission reliability of Aero Piston Engines used in MALE UAVs.

## 🚀 Problem Statement

Maintaining optimal operational status of aero engines in MALE UAVs is critical for mission success. Failures or degradation can severely compromise flight safety and mission completion. We provide a comprehensive digital twin solution to monitor engine health in real-time, predict potential faults, and enhance overall mission reliability using AI.

## 🛠 Tech Stack

- __Backend:__ FastAPI (Python)
- __Frontend:__ React (JavaScript)
- __Database:__ SQLite (Local persistence, for simplicity)
- __ML/AI:__ Scikit-learn, TensorFlow/PyTorch (Python)
- __Simulator:__ Python/NumPy (Simulates engine telemetry)
- __Communication:__ WebSockets (Real-time data streaming)

## ⚙️ System Architecture (Conceptual)

The system operates as a closed loop: The __Simulator__ generates realistic telemetry (including fault injection). The __Backend__ receives this data via WebSockets, processes it using the __ML Models__ (Anomaly Detection, RUL), and stores the processed state/Health Index in the __SQLite__ database. The __Frontend__ consumes the real-time state and historical data to display the Digital Twin Dashboard.

## 💡 Getting Started

### 1. Prerequisites

Ensure you have Python (3.8+) and Node.js/npm installed.

```bash
pip install -r backend/requirements.txt
npm install # in backend-app/
```

### 2. Running Components

__🌐 Start Backend API (Python/FastAPI)__ The backend manages data ingestion, ML calls, and WebSocket connections.

```bash
uvicorn backend.main:app --reload --port 8000
# (Logs show API listening on http://localhost:8000)
```

__🖥️ Start Frontend Dashboard (React)__ The frontend consumes the real-time data stream from the backend.

```bash
cd backend-app
npm run dev
# (Dashboard should open in your browser, e.g., http://localhost:3000)
```

__🛰️ Run Simulator (Python)__ The simulator generates synthetic telemetry and pushes it to the backend WebSocket endpoint.

```bash
python -m simulator.run_simulation
# Generates synthetic mission datasets. The dashboard demo loop is started from the UI.
```

__🔬 ML Training (For Retraining/Testing)__ Run this command to train or validate the core ML models (e.g., Anomaly Detection or RUL).

```bash
python ml/train_all_models.py
```

### 3. Data Generation & Synthetic Simulation

Synthetic data is generated and managed within the `simulator/` and `data/` folders.

- __Simulation:__ Use `python simulator/run_simulation.py`. This simulates the entire operational cycle, including fault injection based on predefined mission profiles.
- __Data Preparation:__ For initial model testing, raw data and pre-processed feature sets are located in the `data/` directory.

### 4. Running a Full Demo Cycle

To run a complete, end-to-end demonstration:

1. __Start Backend:__ Open Terminal 1 and run `uvicorn backend.main:app --reload --port 8000`.
2. __Start Frontend:__ Open Terminal 2 and run `cd backend-app && npm run dev`.
3. __Start Mission:__ Open `http://localhost:3000` and click `Start Mission`.
4. __Observe:__ The dashboard updates with synthetic telemetry, Health Index, fault effects, and WebSocket status.

## 📚 Resources & Contracts

- __Architecture Diagram:__ `docs/architecture.md` (Detailed system flow and component interactions).
- __API Contract:__ `docs/api_contract.md` (Swagger/OpenAPI specification reference for all FastAPI endpoints and WebSocket message formats).
- __Code Implementation:__ The source code resides in `backend/`, `backend-app/`, `ml/`, and `simulator/`.

---

*Disclaimer: This prototype uses realistic synthetic telemetry data and does not claim flight certification or real-engine validation.*

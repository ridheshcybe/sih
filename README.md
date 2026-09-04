# SIH26054 Aero Piston Engine Digital Twin

This repository hosts the complete architecture and implementation components for the SIH26054 Digital Twin project. The system models, simulates, and predicts the performance, health, and potential failure modes of an aero piston engine in real-time.

## 🚀 Architecture Overview

The digital twin is structured as a microservices-oriented monorepo, separating core concerns:
- **`backend/`**: Handles API routing, business logic, and interaction with the database.
- **`simulator/`**: Contains the core physics and operational models (e.g., engine performance curves, mission profiles, fault injection logic).
- **`ml/`**: Houses machine learning pipelines for anomaly detection, Remaining Useful Life (RUL) prediction, and fault classification.
- **`frontend/`**: Provides the user interface for real-time monitoring, dashboard display, and historical report viewing.
- **`data/`**: Stores static data models and configuration files.
- **`docs/`**: Contains architectural documentation and model specifications.

## 💾 Database Schema (Part A)

The relational database models the entire lifecycle of the engine, from initial deployment through operation and eventual decommissioning.
[Detailed schema design is provided in `docs/architecture.md`.]

## <0xF0><0x9F><0x97><0x84>️ Core Data Model Principles

The database is designed to track:
1.  **Engine Identity**: `engines`
2.  **Operational Context**: `missions`, `telemetry`
3.  **System Health**: `twin_states`, `anomalies`, `fault_predictions`, `rul_predictions`
4.  **Management**: `maintenance_advisories`, `mission_reports`, `fault_injections`
5.  **Versioning**: `model_versions`, `system_events`

## ⚙️ Getting Started

1.  **Setup Environment**: Clone the repository and install dependencies (e.g., `pip install -r backend/requirements.txt`).
2.  **Run Migration**: Initialize the database and run migrations: `python backend/main.py migrate`.
3.  **Start Services**: Start the backend API and the frontend development server.
    - `python backend/main.py start`
    - `npm run dev` (in the frontend directory)
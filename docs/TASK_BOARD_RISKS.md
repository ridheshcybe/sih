# 🚀 SIH26054 Project Status Board & Risk Tracker

## 📋 Task Board (Kanban)

This board tracks all major development items across the team roles. Priority Levels:
*   **P0 (Critical):** Required for the Minimum Viable Demo (must be done).
*   **P1 (High):** Important features for a strong demo but might be cut if time is short.
*   **P2 (Medium):** Polish, polish, polish—nice to have if time permits.

### ⚪ To Do (Next Focus)
*   **Implement Backend CRUD Endpoints:** API for Mission Management, Engine State (`/state`, `/telemetry`). (Backend Engineer, P0)
*   **Set Up Frontend Shell:** React component scaffolding and basic connection to the FastAPI API. (Frontend Engineer, P0)
*   **Develop Basic Simulator Loop:** Create the core telemetry generation loop (normal operation only). (Simulation & Data Engineer, P0)
*   **ML Model Feature Extraction:** Finalize feature generation pipeline from raw telemetry. (ML Engineer, P0)
*   **Implement Database Schema & Initial Connection:** Define and implement all necessary SQLAlchemy models and connections. (Backend Engineer, P1)

### 🟠 In Progress (Current Focus)
*   **Streaming Data Flow:** Establish basic WebSocket connection from Simulator $\to$ Backend $\to$ Frontend (Initial `telemetry_update` only). (Simulation & Data Engineer, Backend Engineer, Frontend Engineer, P0)
*   **Health Index & RUL Logic Implementation:** Develop the core mathematical logic for combining sensor readings into a single health score. (ML Engineer, Backend Engineer, P0)
*   **Frontend Dashboard Visualization:** Build the UI dashboard to display real-time state, RUL, and historical charts. (Frontend Engineer, P0)
*   **Architecture Documentation Finalization:** Finalize `docs/architecture.md` using the current MVP flow. (Demo & Documentation Lead, P1)

### 🟡 Blocked (Need Resolution)
*   **ML/Simulation Coupling:** Connecting the ML inference step (using historical/streaming data) to the simulator's real-time output requires defined data contracts and robust error handling. (ML Engineer, Simulation & Data Engineer, Tech Lead, P0)
*   **System Environment Setup:** Finalizing the `docker/` and `scripts/` setup to ensure the entire stack can run with a single command. (Demo & Documentation Lead, Tech Lead, P1)

### ✅ Done (Completed)
*   MVP Scope Definition & API Contract Finalization.
*   Project Structure Setup (Folders created).
*   Basic Database Schema Drafted.

## 🚨 Risks & Blockers Tracker

| Risk Description | Impact | Mitigation / Owner |
| :--- | :--- | :--- |
| **R1: Data Model Complexity:** The physics model might require features beyond the scope of the allocated time, leading to inaccurate predictive metrics. | High | **Mitigation:** Focus only on a single, critical degradation mechanism (e.g., bearing wear) for MVP. (ML Engineer, Tech Lead) |
| **R2: Real-Time Performance:** FastAPI/WebSockets may struggle to maintain high throughput when processing complex ML inferences for every single data point. | High | **Mitigation:** Implement inference batching (process 5 readings at once, not 1-by-1). Profile heavily. (Backend Engineer, ML Engineer) |
| **R3: Dependency Hell:** Integrating FastAPI, React, Python ML dependencies, and Docker in a hackathon setting could cause build failures. | Medium | **Mitigation:** Dedicate 2 hours early on to test the full `docker-compose up` command end-to-end. (Demo & Documentation Lead, Tech Lead) |
| **R4: Scope Creep:** Getting distracted by advanced features (e.g., networking effect modeling) during the demonstration build. | Medium | **Mitigation:** Strictly adhere to the P0 tasks defined in the Task Board. (All Roles, Demo & Documentation Lead) |
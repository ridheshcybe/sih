# Aero-Twin Digital Twin Project Summary and Design Decisions

This document summarizes the scope, architecture, key decisions, and roadmap for the Aero-Twin Digital Twin project, designed to provide real-time health and risk monitoring for aero piston engines.

## 🎯 Project Goal
To create a Minimal Viable Product (MVP) that simulates the operation and degradation of an aero piston engine, providing actionable, prognostics-driven insights to maintenance crews.

## 🗺️ Project Scope and Milestones

### Part A: Minimum Viable Product (MVP) Acceptance Criteria
The system is considered successful if it meets the following 15 measurable criteria:
1. **Telemetry Update Latency:** Telemetry values must update on the dashboard with a simulated latency of $\leq 1$ second.
2. **Fault Simulation Range:** Simulator must generate data for $\geq 10$ time steps, covering $\geq 3$ operational regimes.
3. **Basic HI Tracking:** HI must visibly decrease when the injected fault is active.
4. **Sensor Failure Simulation:** Must detect simulated complete sensor loss (e.g., NaN).
5. **Fault Correlation:** Must correlate $\geq 2$ sensor readings to trigger a high-severity alarm.
6. **Anomaly Scoring:** Anomaly score must increase when a fault occurs, showing visible correlation.
7. **RUL Logic:** RUL must decrease monotonically as HI increases.
8. **Dashboard Readability:** The three core metrics (HI, RUL, Status) must be instantly readable.
9. **Failure State Handling:** Must transition to `SHUTDOWN IMMINENT` within 1-2 time steps upon reaching a critical threshold.
10. **Explainability Output:** Must display fault cause and physical explanation (e.g., "EGT spike due to fuel flow restriction").
11. **Mission Report Generation:** Must generate a summary report (JSON/Markdown) upon mission completion.
12. **Replay Functionality:** Must replay the exact sensor and alert timelines from the initial run.
13. **Interface Stability:** UI must remain functional even if the backend fails.
14. **Core Components:** Simulator, API, and Frontend must be in distinct, testable modules.
15. **Backend Resilience:** API must handle bad inputs without crashing.

### Part B: Core Technical Innovations (Top 3)
The following three innovations were selected as the focus areas, as they create a cohesive, high-impact narrative:
1. **Explainable Fault Diagnosis (Highest Priority):** Moving beyond *what* failed to *why* and *how*. This builds trust and actionable insight.
2. **Adaptive Health Index (Secondary Priority):** Making the HI dynamic by factoring in mission context (altitude, temperature) rather than treating degradation as linear.
3. **Mission-risk Prediction (Tertiary Priority):** Translating the component failure state into an operational impact: "Can the aircraft complete its mission safely?"

### Part C: MVP Final Scope and Architecture
*   **Title:** Aero-Twin: Real-Time Health & Risk Monitoring for Piston Engines
*   **Description:** A dashboard prototype that simulates the operation and degradation of an aero piston engine. The system ingests synthetic telemetry data and, through a simplified diagnostic engine, tracks the Engine Health Index (HI). When correlated anomalies are detected, it diagnoses the fault, projects the Remaining Useful Life (RUL), and updates a Mission Risk score, allowing immediate, actionable alerts and a final maintenance report.
*   **Implementation Features:** (List of 12 key implemented features, including the simulator and dashboard components).
*   **Simplifications Made:** The complex 19-stage failure timeline was reduced to three core, manageable phases: **Healthy Baseline $\rightarrow$ Controlled Degradation $\rightarrow$ Critical Failure**.
*   **Architecture:**
    *   **Backend (`simulator_server.py`):** Serves the REST API, coordinates the simulation.
    *   **Data Generation (`data_simulator.py`):** Generates synthetic, physics-informed time-series data for various operational states and failures.
    *   **Frontend (`index.html`, `script.js`):** Handles UI rendering, user interaction, and communicates with the backend API.

## 🚧 Roadmap and Risk Assessment

**Deferred Features (Future Roadmap):**
*   Adaptive Health Index (Context-aware HI decay)
*   Fleet-level analytics (Comparing multiple assets)
*   Full 3D Engine Simulation

**Top Project Risks:**
1. Simulation Oversimplification (Diagnostic Logic)
2. Integration Failure (API $\leftrightarrow$ Frontend)
3. Scope Creep
4. Time Constraint
5. Domain Knowledge Gap

**Team Roles:**
Backend (Simulator Logic), Frontend (Dashboard/UX), ML/Diagnostics (Fault Rules), Simulation (Data Generator), Docs (Reporting/Narrative).

**Definition of "Done":**
The system successfully completes an end-to-end simulation run, exhibiting controlled degradation, triggering an explainable critical fault alert, and successfully generating a final mission report, all while maintaining a highly usable and stable dashboard interface.
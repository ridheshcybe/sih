# Architectural and Technology Design Summary: Aero Piston Engine Digital Twin

## Context
This design outlines the architectural principles and technology stack for a Digital Twin of an Aero Piston Engine for MALE UAVs, adhering to late-stage student team constraints, requiring laptop execution, and anticipating future edge/CAN integration.

## 🎯 Task Progress
- [ ] Define architectural principles (Part A)
- [ ] Select and justify technology stack (Part B)
- [ ] Write final summary to DESIGN_SUMMARY.md
- [ ] Final review and completion

---

## Part A — Architectural Principles

The following 10 principles guide the development to ensure a robust, scalable, and testable system capable of bridging synthetic simulation with potential real-world hardware integration.

1.  **Modular Microkernel Design:**
    *   *Design Impact:* Core services (Telemetry Ingestion, Physics Model, ML Inference, Visualization) must operate as isolated modules communicating via a well-defined message bus or API layer. This allows independent development and future hot-swapping of components (e.g., swapping a MATLAB model for a native Python implementation).

2.  **Low-Latency Telemetry Processing:**
    *   *Design Impact:* All data paths, from simulation output to visualization, must prioritize low latency. This mandates the use of streaming protocols (e.g., WebSockets) and efficient, in-memory processing queues (e.g., using Redis/shared memory) to prevent bottlenecks.

3.  **Physics + ML Hybrid Modeling:**
    *   *Design Impact:* The core state estimation logic must integrate first-principles physics models (governed by known laws of physics) with data-driven Machine Learning models. Physics models define the boundaries and physical feasibility, while ML models refine estimates using observed patterns (e.g., wear prediction).

4.  **Explainability (XAI):**
    *   *Design Impact:* Every critical prediction (e.g., failure prediction, thrust estimation) must be accompanied by a measure of confidence and an explanation tracing the prediction back to the contributing data source (e.g., "Predicted failure due to bearing vibration exceeding X threshold, contributing 60% of risk score"). This is crucial for user trust and debugging.

5.  **Offline-First Operation:**
    *   *Design Impact:* The entire application must function fully when disconnected from the network. State data, local model weights, and the UI must cache locally. Synchronization logic will only update the cached state upon re-connection.

6.  **Graceful Degradation:**
    *   *Design Impact:* The system must fail predictably. If the ML inference module fails (e.g., due to bad input or corrupted weights), the system must automatically revert to the deterministic, physics-based fallback calculation, notifying the user of the degraded state rather than crashing.

7.  **Monitoring vs. Control Separation:**
    *   *Design Impact:* The system must strictly separate the read-only observation/monitoring services (Dashboard, Logging) from any potential command/control interfaces. Any proposed control action must pass through a dedicated, rate-limited 'Command Gateway' module for validation and logging.

8.  **Reproducible Simulation/Replay:**
    *   *Design Impact:* All simulated test runs must be entirely reproducible. This requires rigorous input data management, including version control for initial conditions, simulation parameters, and ML model weights used for every run.

9.  **Clear Model/Data Versioning:**
    *   *Design Impact:* Every component—the engine model parameters, the ML model weights, the simulation code base, and the required input data schema—must be versioned (e.g., using Semantic Versioning and stored in a Model Registry). The Digital Twin must clearly report which versions it is running against.

10. **Easy Migration from Synthetic to Real Telemetry:**
    *   *Design Impact:* The input/output data contracts (schemas) for the system must be highly stable and abstracted. The core engine logic should accept data based on defined abstract fields (e.g., `temperature_psi`) rather than hardcoded physical sources (e.g., `CAN_BUS_ID_3_TEMP`). This allows swapping the data source from a simulation emitter to a live CAN/Edge gateway easily.

---

## Part B — Final Technology Stack

Given the constraints (Modular monolith, Laptop run time, Future edge integration), the following stack is selected for its balance of developer speed, robust real-time capabilities, and ease of deployment on non-cloud/edge devices.

| Component | Selection | Why Suitable | Implementation Speed | Main Limitation | Hackathon Use | Production Roadmap Use |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Frontend Framework** | React (with TypeScript) | Excellent component model and large ecosystem for building complex UIs. TypeScript ensures type safety, critical for engineering projects. | Fast | Build complexity can increase overhead if not managed well. | Rapid prototyping of data visualization dashboards. | Production-grade UI/UX layer; easily scalable with Next.js/framework upgrades. |
| **UI/Component Library** | Material UI / Chakra UI | Provides pre-built, professionally designed components, drastically reducing boilerplate UI development time. | Very Fast | Can lead to a 'generic' look if not heavily customized. | Ensures a polished, professional look with minimal CSS effort. | Consistent, accessible UI across different views and devices. |
| **Charting Library** | Chart.js / ECharts | Both are highly optimized for web-based real-time data charting, offering diverse chart types and good performance. | Fast | Requires manual handling of real-time data updates (though manageable with React hooks). | Quick visualization of telemetry streams (e.g., speed, temp graphs). | Dedicated charting service integration; high performance on high-frequency data streams. |
| **Backend Framework** | Python (FastAPI) | Python is the industry standard for scientific computing and ML (libraries like NumPy, Pandas). FastAPI provides high-performance async API endpoints. | Moderate | As a monolith, horizontal scaling might require careful architectural planning later. | Fast setup of data ingestion endpoints and service orchestration. | Core business logic, ML orchestration, and data persistence layer. |
| **Real-time Method** | WebSocket (via FastAPI) | Provides persistent, low-latency, bi-directional communication crucial for Digital Twin updates (Simulator -> Frontend). | Moderate | Requires robust error handling and reconnection logic to prevent state loss. | Streaming simulated sensor data updates instantly to the dashboard. | Handling live data feeds from edge devices or high-frequency data simulators. |
| **Database** | SQLite | Ideal for a monolithic, laptop-based application. Zero-setup, single file deployment, and sufficient for storing simulation results and state history. | Very Fast | Not suitable for massive concurrent write loads or multi-node deployments. | Storing simulation history and configuration data locally during the hackathon. | Initial stage storage; migration to PostgreSQL/TimescaleDB will occur as load increases. |
| **ML Libraries** | Scikit-learn / PyTorch (Python) | Industry leaders providing comprehensive tools for everything from regression to anomaly detection. PyTorch is favored for state-of-art deep learning. | Moderate | Large dependency size and potential computational load on low-powered hardware (addressed by using simplified models). | Implementing initial predictive components (e.g., remaining useful life estimation). | Production deployment model serving via optimized containers (e.g., TorchScript). |
| **Data Format** | Parquet (Primary) & JSON (Secondary) | **Parquet** is columnar, highly efficient, and optimized for storage/retrieval of time-series telemetry data. **JSON** is used for lightweight API payloads and configuration. | Moderate | Data governance becomes complex when mixing formats, requiring strict protocol enforcement. | Storing historical simulation data efficiently for analysis. | Primary persistence format for large-scale, time-series data archives. |
| **Containerization** | Docker | Provides a lightweight, standardized, and reliable environment for packaging the entire application (Backend + dependencies). | Fast | Adds a layer of complexity (Docker setup/management) that must be mastered quickly. | Ensuring the entire system runs identically on any laptop/environment. | Essential for continuous integration/continuous deployment (CI/CD) pipelines. |
| **Testing Approach** | Unit, Integration, and Contract Testing | **Unit:** Test individual Python functions/React components. **Integration:** Test module interactions (e.g., FastAPI receiving data from simulator). **Contract:** Use OpenAPI schema validation to ensure module interfaces never break. | Moderate | Requires disciplined adherence to testing best practices; scope creep can slow down development. | Ensuring core data pipelines work reliably between modules. | Essential for maintaining a large, complex codebase over time; guarantees interface stability. |
| **Report Generation** | Python (e.g., Jinja2 + Pandas) | Utilizing Python's data manipulation strength (Pandas) to aggregate results and a templating engine (Jinja2) to structure the final PDF/HTML report. | Moderate | Custom PDF generation can be tricky; often requires specialized libraries like ReportLab. | Generating a PDF summary report of the simulation run parameters and results. | Formal publication of system performance and design reports. |
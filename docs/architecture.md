# SIH26054 Aero Piston Engine Digital Twin Architecture

## Architectural Philosophy

The twin adheres to a service-oriented, event-driven architecture pattern, simulating a near-real-time feedback loop. The core principle is the fusion of physical simulation (Physics-Inspired Expected Values) with data analysis (Anomaly Detection/ML) to generate a living, predictive representation of the engine's health and remaining operational lifecycle.

---

## Part A: MVP Architecture (24–72 hours)

The MVP is designed for maximal functional breadth while minimizing feature complexity, focusing on the core data path: Sensor Data $\rightarrow$ FastAPI $\rightarrow$ Digital Twin Model $\rightarrow$ WebSocket $\rightarrow$ React Dashboard.

### Reduced Architecture Components:

1.  **Synthetic Telemetry Simulator:** A Python module generating realistic, time-series data streams simulating sensor outputs (e.g., temperature, pressure, RPM, oil pressure) based on configurable operating regimes. It introduces structured faults (e.g., step changes, drift) for testing.
2.  **SQLite Database:** Used as the persistent, localized data store for mission logs, historical telemetry snapshots, and model parameters. Its simplicity allows rapid deployment in the hackathon context.
3.  **FastAPI Backend:** Acts as the primary API gateway. It handles data ingestion from the simulator/data sources, executes the core digital twin logic, and manages the persistent state.
4.  **WebSocket Streaming:** The primary communication channel. It pushes processed, calculated, and derived health data (e.g., current Health Index, predicted RUL) from the FastAPI backend to the React client in real-time.
5.  **Physics-Inspired Expected Values Module:** A set of calibrated Python functions (e.g., $P_{expected} = f(RPM, Temp, Load)$) that calculate physically plausible ranges and relationships between sensors, providing the baseline for residual calculation.
6.  **Residual Calculation Engine:** Calculates the deviation ($\text{Residual} = \text{Actual} - \text{Expected}$) for key sensor measurements. Large residuals immediately trigger alerts and inform the Health Index.
7.  **Health Index (HI):** A single, aggregate, normalized score (0-100) derived from a weighted combination of the residual magnitude, model predictions, and operational parameters. It serves as the primary user-facing health metric.
8.  **Anomaly Detection Model:** A simple, unsupervised model (e.g., Isolation Forest or simple Mahalanobis distance) trained on normal operating data to detect deviations from multi-variate 'normal' patterns.
9.  **Fault Classification Model:** A supervised classifier (e.g., Random Forest, simple SVM) trained to take feature vectors (residual features, HI, raw telemetry) and categorize the current state into known fault types (e.g., 'Bearing Wear', 'Fuel Restriction', 'Sensor Failure').
10. **Simplified RUL/Degradation Estimator:** A simple linear regression or exponential decay model using the trending Health Index or key wear indicators to estimate Remaining Useful Life (RUL).
11. **Fault Injection Module:** Allows the simulator or test harness to programmatically inject specific, defined faults (e.g., zeroing a sensor, causing constant offset) to test the system's response.
12. **Mission Replay:** Ability to load a stored mission log (from SQLite) and replay the simulated telemetry stream through the entire digital twin pipeline, updating the dashboard step-by-step without requiring a live data source.
13. **React Dashboard:** The frontend visualization layer. It subscribes to the WebSocket stream, displays raw/calculated telemetry, visualizes the HI trend, and presents actionable fault alerts.
14. **Mission Report:** A simple report generator that compiles the aggregated mission logs, key metrics (peak HI, fault instances), and the final RUL estimate for user review.

### Simplifications and Combinations:

*   **Model Abstraction:** Complex physics models are simplified to empirically calibrated expected value functions rather than full CFD/thermodynamic simulations.
*   **ML Sophistication:** State-of-the-art deep learning models are replaced by established, simpler ML techniques (Isolation Forest, Random Forest) due to the tight time constraint.
*   **Integration:** All components are orchestrated by the FastAPI backend, acting as the central digital twin brain, minimizing the need for complex microservice orchestration in the MVP.

---

## Part B: Production Roadmap

### 1. Hackathon Demonstrator (Current Scope)
*   **Hardware:** Local workstation, Virtualized/Simulated Environment (Laptop/Cloud).
*   **Data Source:** Synthetic Simulator (Python).
*   **Model Changes:** Simplified ML models (IF, RF). Model versioning is implicit (hardcoded).
*   **Cybersecurity Level:** Low (Internal Network/localhost only). Focus on functionality over hardening.
*   **Deployment Architecture:** Monolithic FastAPI/SQLite/React setup.
*   **Testing Requirements:** Pass pre-scripted fault injections and mission replay scenarios.
*   **Reliability Requirements:** Basic logging and graceful degradation on primary component failure (e.g., if simulator fails, dashboard shows 'Offline').
*   **Human Approval Requirements:** Basic confirmation of system state and alert visibility.
*   **Cannot Claim:** Real-world accuracy, robust security, resilience to external attacks, or full integration with physical systems.

### 2. Engine Test-Rig Integration (Mid-Term)
*   **Hardware:** High-speed data acquisition unit (DAQ), Local edge compute gateway (e.g., NVIDIA Jetson/industrial PC).
*   **Data Source:** Live stream from DAQ unit, capturing CAN/Ethernet payloads.
*   **Model Changes:** Transition to validated, parameterized, physics-informed deep learning models. Implement advanced anomaly detection (e.g., Variational Autoencoders) and model uncertainty quantification.
*   **Cybersecurity Level:** Moderate (Network Segmentation, TLS/VPN, basic authentication, firewalls).
*   **Deployment Architecture:** Distributed edge compute/cloud hybrid (Edge processes high-frequency data; Cloud handles long-term training/analytics).
*   **Testing Requirements:** Integration testing with known test-rig fault injection rigs. End-to-end latency benchmarking.
*   **Reliability Requirements:** High uptime (99.9%). Defined failure detection for edge compute resources.
*   **Human Approval Requirements:** Sign-off from Test Engineering and IT Security teams.
*   **Cannot Claim:** Full field deployment reliability, immunity to novel/zero-day fault patterns, or management of cross-site fleet data.

### 3. UAV GCS and Fleet Deployment (Production)
*   **Hardware:** Dedicated, hardened flight-qualified compute platform; Satellite/Cellular communication links.
*   **Data Source:** Primary telemetry link (Satellite/Cellular) + Local CAN/SocketCAN (redundant links).
*   **Model Changes:** Federated Learning structure for continuous, distributed model refinement. Comprehensive model validation and drift correction mechanisms.
*   **Cybersecurity Level:** High (Defense-in-depth, PKI, Hardware Root of Trust, compliance with aviation standards).
*   **Deployment Architecture:** Fully decentralized/decoupled. Edge nodes handle immediate control loops; cloud handles global optimization and retraining.
*   **Testing Requirements:** Field operational testing (Flight hours accumulation, diverse environmental/operational profiles). Full simulation testing (HIL).
*   **Reliability Requirements:** Mission-critical uptime (Six-Nines). Must adhere to strict safety standards (DO-178C, etc.).
*   **Human Approval Requirements:** Certification from Aviation Authorities (FAA/EASA). Detailed operational procedures and airworthiness certification.
*   **Future Integration (Post-Production):** CAN, SocketCAN, ECU, FADEC, edge, GCS, cloud, HIL, maintenance records are natively integrated starting in Stage 3, requiring modular interfaces and standardized data models.

---

## Part C: Failure and Recovery Behavior

| Failure Case | Detection Mechanism | User-Visible Behavior | Backend Behavior | Fallback/Recovery | Logging |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Telemetry Stops** | Heartbeat monitor (WebSocket/API) | Large HI drop, "Telemetry Lost" warning. | Switch to state prediction based on last known good values and physics model. | Hold prediction state for T_timeout. If timeout expires, activate "Best Guess" mode and cease RUL prediction. | Critical Log: `Telemetry_Stoppage` |
| **One Sensor Missing** | Data validation (Plausibility Check) | Warning indicator on the dashboard. HI calculation down-weights the missing sensor. | Use physics-informed imputation (e.g., estimating missing Temp from known RPM/Load). | If imputation fails, proceed with the reduced sensor set, noting the degraded certainty. | Warning Log: `Sensor_Imputation_Used` |
| **Sensor Drift** | Statistical analysis (EWMA, Mahalanobis distance) | Alert: "Sensor Drift Detected" with trending chart. | Continuously calculate running mean and standard deviation. Detect consistent offset from Expected Value. | Issue a warning/confidence reduction on the HI, requiring manual validation or expert review. | Warning Log: `Sensor_Drift_Detected` |
| **Impossible Sensor Values** | Range/Constraint validation (Hard Thresholds) | Hard Stop Alert: "Out-of-Range Value." | Reject the data point, logging the rejection reason and value. Continue processing with the next valid packet. | System state remains stable based on prior data. Does not crash. | Error Log: `Value_Out_of_Bounds` |
| **ML Model Unavailable** | Service Wrapper/Health Check | Warning: "ML Services Offline." HI calculation reverts to physics-based residuals only. | Use the fallback path: Rely entirely on known physics models and simple threshold logic, bypassing complex ML inferences. | Service Restart/Circuit Breaker pattern. If persistent, RUL estimation is disabled. | Warning Log: `ML_Model_Offline` |
| **Database Unavailable** | Connection Pooling/Health Check | Warning: "Mission History Unavailable." | All transient calculations continue in memory. Logging is redirected to a local, volatile buffer (FIFO). | Attempts automatic reconnection every T_retry. Historical data logging fails. | Error Log: `DB_Connection_Failure` |
| **WebSocket Disconnects** | Client-side retry mechanism/Server heartbeats | Dashboard indicator: "Reconnecting..." | Backend queues messages and attempts re-subscription/re-connection with exponential backoff. | Upon successful reconnect, sends a state sync message containing all calculated metrics since disconnection. | Info Log: `WebSocket_Reconnect` |
| **Simulator Crashes** | Process Watchdog (External service) | Dashboard shows the last valid data set and a 'Simulator Failed' banner. | State capture: Save the last valid state of the twin parameters and fault injector settings. | Automatic restart of the simulator service. System continues by displaying the last known operational state. | Critical Log: `Simulator_Crash` |
| **Invalid Timestamp** | Timestamp validation (Sequence checking) | Warning/Silent rejection (if time difference is excessive). | Reject the data point. If multiple invalid timestamps occur, flag a potential synchronization issue. | Logging includes the skipped packet count. Prediction is based on the last valid time step. | Warning Log: `Invalid_Timestamp_Skipped` |
| **Duplicate Packets** | Sequence ID Check (Sliding Window) | Silent handling (no user notification). | Check incoming packet sequence ID against a small sliding window. Discard duplicates. | Log the count of discarded duplicates. | Info Log: `Duplicate_Packet_Discarded` |
| **Low-Confidence Model Output** | Model output confidence score (e.g., probability score) | Warning: "Model Prediction Caution: Low Confidence." | Use the prediction output, but accompany it with the confidence score and treat it as a *guideline*, not a definitive state. | Trigger a mandatory human review action. Does not trigger a critical alert. | Warning Log: `Low_Confidence_Prediction` |
| **Multiple Simultaneous Faults** | Fault Correlation Engine | Alert: "Multiple Faults Detected. Highest Risk: [Fault A] and [Fault B]." | Run a hierarchical fault analysis: Identify the primary (Root Cause) fault, then list secondary/symptoms. | The HI drops sharply, and RUL is drastically reduced based on the combined failure effects. | Critical Log: `Multi_Fault_Event` |

---

## Part D: Security Boundary (Prototype vs Production)

| Feature | Prototype (Hackathon) | Production (Defense-Grade) |
| :--- | :--- | :--- |
| **User Roles** | View-Only (Read access to Dashboard) | Hierarchical (Operator, Engineer, Administrator, Auditor) |
| **Authentication** | None/Basic API Key (Single shared secret) | OAuth 2.0 / OpenID Connect (OIDC) integration; MFA enforced. |
| **API Access Control** | Basic endpoint restriction (e.g., only read/POST allowed). | Role-Based Access Control (RBAC) on every resource and method. Detailed rate limiting. |
| **Data Integrity** | Basic hashing/logging of inputs. Data is trusted from the simulator. | Chain of custody/Attestation signatures on all telemetry/data packets. Use Merkle trees for data integrity checks. |
| **Audit Logging** | Simple SQLite log of critical events (Fault, Replay). | Immutable, append-only ledger (e.g., blockchain/blockchain-like DB). Detailed logging of *who*, *what*, *when*, and *why* of every action. |
| **Model Integrity** | No formal checks. Models are treated as immutable code. | Digital signatures for all deployed model artifacts. Mandatory validation against adversarial input sets before serving. |
| **Offline Mode** | Limited to Mission Replay (local data persistence). | Full operational capability: Edge nodes can run prediction/control loops based on cached models and local rules for extended periods. |
| **Encryption Roadmap** | None/Basic HTTP transport. | End-to-End Encryption (TLS 1.3 minimum). Data at Rest (AES-256) and Data in Transit must be encrypted. |
| **Engine Control** | STRICTLY NO automatic engine-control commands. Output is informational only. | Maintained: System is purely advisory. Outputs must pass through a segregated, high-integrity command validation module. |
| **Separation** | Logical separation in codebase. | Hardware and software separation (Air-gapped or highly segregated networks). |
| **Secure Ingestion**| Direct write to backend services. | Dedicated, quarantined ingestion endpoint with deep packet inspection, format validation, and integrity checks. |

---

## Part E: Architecture Acceptance Criteria (Minimum 15)

1.  **Telemetry Validation:** All incoming telemetry data must pass mandatory validation (range check, type check) before entering the digital twin core pipeline.
2.  **Twin Update Rate:** The Digital Twin Core must update its internal state parameters (HI, RUL) at a fixed, measurable interval (e.g., 100ms) regardless of input data rate variation.
3.  **Real-Time Update:** The dashboard must receive and render updates via WebSocket within 50ms of the core state update.
4.  **Mission Replay Fidelity:** The system must successfully replay a completed mission log, accurately reproducing the historical time-series trends and state transitions visible to the user.
5.  **Alert Clarity:** Every active alert (Warning/Critical) must be accompanied by a brief, machine-generated explanation citing the primary cause (e.g., "HI dropped due to residual Temp/Pressure mismatch").
6.  **HI Trend Smoothness:** The Health Index must change smoothly and predictably when operational parameters are near nominal ranges, avoiding jitter or sudden, unexplained spikes.
7.  **Fallback Resilience:** If the primary ML model fails, the system must demonstrably continue functioning using the simplified threshold/physics logic without user intervention or data gaps.
8.  **Fault Logging:** Every injected fault (simulated or real) must be logged with its injection time, duration, and the system's measured response.
9.  **Prediction Traceability:** Every prediction or RUL calculation displayed on the dashboard must include the ID, version, and timestamp of the model used for that specific prediction.
10. **Report Completeness:** Mission reports must contain, at minimum, the total operational time, maximum HI recorded, count of critical faults, and the final RUL estimate.
11. **Data Synchronization:** The database write operations must be asynchronous to the core twin update loop to prevent I/O bottlenecks from degrading the real-time performance.
12. **Rate Limiting:** The FastAPI backend must implement rate limiting on all non-telemetry API endpoints to prevent DoS attacks.
13. **Event-Driven Architecture:** All major state changes (Fault Detection, HI change, RUL drop) must originate from an explicit event/message queue, ensuring decoupled module interactions.
14. **Error Isolation:** Failure in one subsystem (e.g., Anomaly Model) must not propagate exceptions to or degrade the performance of unrelated, stable subsystems (e.g., Physics Model).
15. **Historical Comparison:** The dashboard must allow the user to select and overlay metrics from different missions or historical data sets to compare current performance against past performance.

---

## Part F: Final Architectural Recommendation

### 1. Final Architecture Summary

The recommended architecture is a layered, distributed, and event-sourced system.

*   **Layer 1: Edge/Data Ingestion (Low Latency)**: Handles raw sensor data acquisition (CAN/SocketCAN). This layer performs critical, low-latency filtering, pre-processing, and initial anomaly detection using highly optimized, lightweight models (e.g., fixed-point math, VAEs).
*   **Layer 2: Digital Twin Core (Mid Latency)**: Hosted on a localized compute unit. This is the brain, executing the main digital twin logic. It fuses data streams, calculates residuals, updates the HI, and generates actionable events. It maintains the current operational state and the mission buffer.
*   **Layer 3: Cloud/Backend (High Latency)**: Handles long-term storage, model training (Federated Learning), complex analysis, user management (RBAC), and report generation.

### 2. Final Tech Stack Recap

*   **Backend/Core:** Python (FastAPI) for high throughput, asynchronous processing. Utilizes an internal Message Queue (e.g., Kafka/RabbitMQ) for event decoupling.
*   **Database:** PostgreSQL/TimescaleDB for time-series telemetry data; PostgreSQL/SQLite for relational metadata and mission logs.
*   **Frontend:** React/TypeScript for robust, maintainable UI development.
*   **Communication:** WebSocket (for real-time streams); gRPC or REST (for asynchronous API calls).
*   **Simulation/Modeling:** Python libraries (NumPy, SciPy, Scikit-learn, PyTorch/TensorFlow).

### 3. MVP Modules List (As defined in Part A)
*   Telemetry Simulator
*   SQLite Database
*   FastAPI Backend
*   WebSocket Streaming
*   Physics-Inspired Expected Values
*   Residual Calculation
*   Health Index
*   Anomaly Detection Model (IF)
*   Fault Classification Model (RF)
*   Simplified RUL/degradation estimator
*   Fault Injection
*   Mission Replay
*   React Dashboard
*   Mission Report

### 4. Modules to Combine/Simplify
*   **Combine:** Residual Calculation and Physics-Inspired Expected Values are intrinsically linked and should be implemented as a single `Prediction/Residual Service`.
*   **Simplify:** The initial implementation of the Digital Twin Core should prioritize a single, unified data model to prevent data mapping complexity.

### 5. Modules to Postpone (V2.0+)
*   **Advanced Simulation:** Full CFD integration (requires massive computational resources).
*   **High-Fidelity Data Sources:** Direct CAN/SocketCAN/FADEC/ECU integration (requires hardware abstraction layer).
*   **Deep Learning Training Loop:** Full end-to-end FL training loop (Model retraining should be offloaded to dedicated MLOps infrastructure).

### 6. Exact Development Order
1.  **Setup:** Project structure, logging, and core data model (Phase 1).
2.  **Simulation & Ingestion:** Implement the Simulator and the FastAPI data ingestion endpoint (Phase 2).
3.  **Core Logic:** Implement Expected Values, Residual Calculation, and the initial HI logic (Phase 3).
4.  **UI/Streaming:** Implement WebSocket and the basic React Dashboard display (Phase 4).
5.  **Prediction:** Implement Anomaly Detection and Fault Classification models, linking them to the HI calculation (Phase 5).
6.  **Completeness:** Implement Mission Replay and Report generation (Phase 6).

### 7. Team Allocation
*   **Backend/Digital Twin Core (Primary):** 2 Engineers
*   **Frontend/Dashboard (Primary):** 1 Engineer
*   **ML/Simulation:** 1 Engineer
*   **Documentation/Architecture:** 0.5 FTE (Architect/Tech Lead)

### 8. Top Architectural Risks
1.  **Time-Series Data Integrity:** Handling the synchronization of real-time data with historical and simulated data accurately.
2.  **Fault Interaction:** Accurately modeling the combined effects of multiple simultaneous faults (non-linear interaction effects).
3.  **State Consistency:** Ensuring the core digital twin state is consistent across asynchronous writes, model updates, and recovery scenarios.

### 9. Top 5 Implementation Actions for Today
1.  Define the canonical data schema for telemetry input (JSON/Protobuf).
2.  Set up the basic FastAPI endpoint structure for data ingestion (`/api/v1/telemetry`).
3.  Develop the basic Python class structure for the `DigitalTwinCore` to house the state, HI, and RUL.
4.  Create a minimal viable Simulator that writes to a local queue/memory buffer.
5.  Implement basic WebSocket connection establishment from the React scaffold.

### 10. Definition of Architectural Completion
The architecture is considered complete when:
1.  All parts of the original specification (A-F) have been documented and validated.
2.  The system successfully executes a full Fault Injection/Mission Replay cycle, demonstrating detection, fallback, and accurate reporting for all defined fault types (Part C).
3.  All 15 Acceptance Criteria (Part E) have been met and independently verified by the QA team.
# SIH26054 Digital Twin Feature Definition and MVP Strategy

This document evaluates 30 potential features for the SIH26054 aero piston engine digital twin, defining the Minimum Viable Product (MVP) scope and outlining a phased development roadmap. Features are grouped for logical evaluation and implementation prioritization.

---

## 📝 Phase 1: MVP Core Functionality (Must Build)

These features are critical for demonstrating the core value proposition of a digital twin: ingesting live data, calculating engine state, and detecting immediate issues.

### Group 1: Data Ingestion & Core State (Features 1, 2, 3, 4, 5, 24, 26)

| Feature | User value | Required for MVP? | Technical complexity | Demo impact | Recommended implementation | Acceptance criterion | What happens if not completed? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Real-time dashboard (24)** | Immediate understanding of engine health; single source of truth. | Yes | Low | High | Simple web GUI displaying key metrics (T, P, RPM, etc.). | Dashboard updates every 1 second with all core metrics. | The system is unusable for real-time monitoring. |
| **Real-time telemetry streaming (2)** | Allows dynamic monitoring of an engine over time. | Yes | Medium | High | Kafka/MQTT topic simulating data stream received by the dashboard. | Data streams continuously without dropping packets. | Cannot demonstrate "live" operation; limited to pre-recorded data. |
| **Digital twin state synchronization (3)** | Ensures the virtual model accurately reflects the physical engine's state. | Yes | Medium | High | State machine logic that updates the twin based on incoming telemetry. | The twin's calculated state matches the incoming telemetry readings within acceptable bounds. | The twin's representation of the engine is inaccurate or stale. |
| **Synthetic engine telemetry generation (1)** | Provides a reliable, controllable data source for testing and simulation. | Yes | Medium | Medium | Simulation module generating realistic, structured data (JSON/CSV). | Can generate full operational cycles (startup, cruise, shutdown) on demand. | Cannot test the system without a controlled data source. |
| **Physics-inspired expected sensor values (4)** | Provides a baseline for 'normal' operation, crucial for initial anomaly detection. | Yes | Medium | High | Implement basic differential equations (e.g., ideal adiabatic compression) to predict expected sensor values. | Predicted values track real/synthetic values closely during stable operation. | Anomaly detection is blind; it only reports deviations from a baseline, not predicting them. |
| **Sensor residual calculation (5)** | Quantifies the deviation between actual and expected sensor readings. | Yes | Low | Medium | Simple mathematical function: $Residual = |Actual - Expected|$. | Calculates a residual value for all core sensors (T, P, RPM) every cycle. | Cannot quantitatively assess the deviation or severity of a fault. |
| **CAN/ECU/FADEC integration (26)** | Makes the solution feel grounded in existing aerospace hardware systems. | Yes | High | Medium | Mocking the CAN bus input structure (e.g., using a simple message parser). | Successfully parses and maps a sample message payload into usable internal variables. | Lacks credibility and integration with the actual operational domain. |

### Group 2: Diagnosis and Health Assessment (Features 6, 7, 8, 9, 10, 14, 19, 20)

| Feature | User value | Required for MVP? | Technical complexity | Demo impact | Recommended implementation | Acceptance criterion | What happens if not completed? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Health Index (0–100) (6)** | Provides a single, easy-to-digest measure of overall engine health. | Yes | Medium | High | Weighted average calculation based on calculated residuals and detection flags. | The index changes plausibly and reflects the severity of injected faults. | The system is difficult for non-engineers to interpret; lacks a summarizing metric. |
| **Threshold-based safety limits (7)** | Immediate warning when parameters exceed physical safety boundaries. | Yes | Low | High | Simple comparison logic: `if sensor > threshold: trigger_alert()`. | Correctly triggers an alert and red status on simulated over-temperature or over-pressure. | Safety violations are missed, making the twin useless for safety assessment. |
| **Anomaly detection (8)** | Identifies deviations from normal behavior that aren't tied to specific faults. | Yes | Medium | High | Simple statistical model (e.g., Z-score) applied to key metrics to flag outliers. | Successfully flags a sudden, transient dip in oil pressure during steady-state operation. | The system fails to catch subtle, unexpected operational anomalies. |
| **Fault classification (9)** | Pinpoints *what* the specific problem is (e.g., "Low Oil Pressure," "High Exhaust Temp"). | Yes | Medium | High | Rule-based classification (e.g., if (residual > X) AND (metric = Y) THEN "Fault Z"). | Accurately classifies a simulated fault (e.g., 15% loss of expected RPM) into the correct category. | Reports generic warnings ("Anomaly detected") without actionable details. |
| **Sensor drift/dropout detection (10)** | Identifies failure modes related to the sensor itself, not the engine. | Yes | Low | Medium | Monitoring for zero/constant values over time (dropout) or slow, linear shifts (drift). | Correctly reports "Sensor X Dropped" when the input stream goes silent, and "Sensor Y Drifting" when the value moves outside a predicted band. | Maintenance cannot be planned; faulty sensors are misinterpreted as engine faults. |
| **Overheating prediction (14)** | Provides advanced warning of impending thermal failure. | No | High | High | Basic rate-of-change model (e.g., using historical trend and current rate) to predict time to threshold. | Predicts the temperature will cross the redline threshold within the next N simulated minutes. | Lacks predictive capability; only reports current readings. |
| **Mission-risk prediction (19)** | Provides a holistic assessment of mission completion likelihood. | No | High | High | Combination of Health Index, RUL, and current operating parameters. | Outputs a calculated probability (e.g., 95% confidence) for mission success based on current state. | The twin cannot be used for operational decision-making (e.g., "Can we finish the flight?"). |
| **Maintenance recommendations (20)** | Provides actionable next steps for maintainers. | No | Medium | Medium | Rule-based logic: IF (Fault X detected for > Y hours) THEN recommend (Action Z). | Generates a clear, actionable maintenance task (e.g., "Inspect Injector 3") when a fault persists. | The system reports problems but provides no path to resolution. |

---

## ⚙️ Phase 2: System Enhancements & Expansion (Build if Time Permits)

These features significantly enhance the utility and completeness of the system but are not strictly required for a working MVP demonstration.

### Group 2: Advanced Diagnostics (Features 11, 12, 13, 15, 16, 17, 18)

| Feature | User value | Required for MVP? | Technical complexity | Demo impact | Recommended implementation | Acceptance criterion | What happens if not completed? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Misfire detection (11)** | Identifies combustion issues by monitoring expected vs. actual performance metrics (e.g., torque fluctuation). | No | Medium | High | Analyze correlation between expected and measured parameters (e.g., specific output pressure vs. engine speed). | Successfully flags a simulated 2-cylinder misfire based on power output variance. | Key engine component failure modes are missed. |
| **Injector abnormality detection (12)** | Pinpoints issues with individual fuel delivery components. | No | Medium | High | Comparative analysis of expected versus measured fuel delivery parameters (e.g., injector timing deviation). | Identifies a simulated injector stuck open/closed based on related sensor data. | Cannot diagnose fuel system component failures. |
| **Lubrication issue detection (13)** | Specific detection for oil flow, pressure, and temperature issues. | No | Medium | Medium | Dedicated sensor residual calculation focused on oil system parameters. | Correctly flags issues like excessively high bearing temperatures or low oil flow rate. | Over-simplifies the system's mechanical failure modes. |
| **Vibration anomaly detection (15)** | Detects mechanical issues using vibration analysis (requires specific sensor data). | No | High | Medium | Requires advanced signal processing (e.g., FFT analysis) on accelerometer data. | Identifies a simulated bearing wear signature in the frequency spectrum. | Limited to thermal/pressure/electrical faults; ignores physical wear. |
| **Battery/alternator health (16)** | Assesses the electrical power system's state. | No | Low | Medium | Monitoring voltage, current, and charge/discharge cycles. | Tracks State of Charge (SoC) and flags degradation based on charging efficiency. | The electrical subsystem health cannot be managed or monitored. |
| **Degradation tracking (17)** | Models the gradual decrease in component efficiency over time. | No | Medium | Medium | Using remaining useful life (RUL) calculations to model wear patterns (e.g., oil pump wear). | Shows a predictable decline in the calculated efficiency parameter over a simulated flight mission. | System cannot forecast future component replacements or necessary servicing. |
| **RUL estimation (18)** | Estimates the remaining useful life for critical components. | No | High | High | Combining degradation modeling with operational stress factors (flight hours, cycles). | Provides a specific "Remaining Service Life" estimate (e.g., 300 flight hours). | The twin is purely reactive; it cannot provide critical longevity forecasting. |

---

## 🚀 Phase 3: Future Roadmap (Future Roadmap)

These features require significant integration, new data streams, or advanced AI/ML models and are best deferred beyond the initial MVP.

### Group 3: System & User Expansion (Features 21, 22, 23, 25, 27, 28, 29, 30)

| Feature | User value | Required for MVP? | Technical complexity | Demo impact | Recommended implementation | Acceptance criterion | What happens if not completed? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Mission simulation (21)** | Allows operators to test the twin's responsiveness to various mission profiles. | No | High | High | Advanced input control allowing programmatic change of altitude, throttle, and temp setpoints. | The twin successfully calculates expected engine parameters across a simulated climb-descent profile. | The system is limited to displaying the current, single-point-in-time operational data. |
| **Historical mission replay (22)** | Enables forensic analysis of past events for root cause analysis. | No | Medium | Medium | Storage of all telemetry data linked to mission timestamps and playback capability. | Successfully replays a fault event sequence, visualizing the timeline and sensor evolution. | Cannot perform post-mortem analysis; every issue must be identified in real-time. |
| **Fault injection controls (23)** | Allows engineers to systematically test failure modes safely. | No | Medium | High | Dedicated control panel to programmatically force sensor failures (e.g., set pressure to 0). | Successfully simulates and triggers a known failure mode (e.g., dropping an oxygen sensor reading). | The system cannot be thoroughly validated against known failure conditions. |
| **Mission-wise report generation (25)** | Provides formal documentation and compliance evidence of engine performance. | No | Medium | Medium | Backend service that compiles dashboard data, fault logs, and performance summaries into a PDF/XML format. | Generates a structured report summarizing the mission profile, total cycles, and average health score. | Requires manual data extraction and report writing, defeating automation. |
| **Edge deployment (27)** | Enables real-time processing capability in remote environments. | No | High | Medium | Containerizing the core detection logic (e.g., using Docker/K3s) for edge hardware. | The core Health Index calculation runs successfully on a simulated limited-resource environment. | Severely restricts deployment scope and connectivity options. |
| **Fleet-level monitoring (28)** | Allows managing and benchmarking multiple assets simultaneously from a central UI. | No | High | Medium | Database and UI structure designed to aggregate data from multiple unique asset IDs. | Displays a dashboard view showing the health index of 10 unique, simulated engines. | Operational management must be done asset-by-asset, scaling poorly. |
| **Federated learning (29)** | Improves the AI model by learning across decentralized datasets without sharing raw data. | No | Very High | Low | Complex ML framework integration for model sharing and aggregation. | Successfully aggregates model weight updates from simulated remote units. | The diagnostic accuracy improvement potential is capped by data silos. |
| **3D engine visualization (30)** | Provides an immersive, graphical view of the engine's internal state. | No | High | Medium | Integration with a 3D rendering engine (e.g., Unity/Unreal) driven by twin state variables. | The 3D model components visually change color or scale based on the Health Index and core parameters. | Lacks the physical visualization appeal, but does not stop the functional utility of the twin. |

---

## 🚦 Feature Classification Summary (Summary for Stakeholders)

The following classifications guide the MVP scope definition:

| Classification | Features (IDs) | Count | Rationale |
| :--- | :--- | :--- | :--- |
| **Must Build (MVP Scope)** | 2, 3, 5, 6, 7, 8, 9, 10, 24, 26, 1, 4 | 12 | Essential core functionality: data ingestion, state tracking, core anomaly detection, and primary reporting. Without these, the twin is non-functional. |
| **Build if time permits** | 11, 12, 13, 14, 15, 16, 17, 18, 20 | 9 | Major diagnostic enhancements that significantly boost value and credibility (e.g., RUL, specific fault detection). Ideal for the first iteration *after* MVP stabilization. |
| **Simulate or simplify** | 23 (Fault Injection) | 1 | Building a full fault injection mechanism is complex. For MVP, *simulating* a single, hard-coded fault condition (e.g., zero oil pressure) is sufficient to validate detection logic. |
| **Future Roadmap** | 19, 21, 22, 25, 27, 28, 29, 30 | 8 | These features require substantial ecosystem maturity (e.g., full mission profiles, federated learning, 3D integration) and should be prioritized after the core diagnostic loop is proven. |
| **Exclude from hackathon prototype** | (None) | 0 | All features provide unique value, but the prioritization groups them into the above categories for structured delivery. |
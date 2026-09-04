# SIH26054 Aero Piston Engine Digital Twin Architecture Design

This document outlines the core architectural modules, data definitions, and state representations for the Digital Twin of the SIH26054 aero piston engine.

## PART A: Module Responsibilities Table

The following table details the responsibilities, inputs, outputs, technologies, and ownership for the core modules of the Digital Twin ecosystem.

| Module | Responsibility | Input | Output | Technology | Processing Mode | MVP or Future | Team Owner Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Simulator** | Replicates engine physical behavior (thermodynamics, mechanics) based on operational parameters. | Inputs: Mission parameters (altitude, speed, throttle), Engine Model constants. | Simulated telemetry (P, T, RPM, etc.), Load profile data. | Python/C++, Modelica | Streaming | MVP | Simulation |
| **Telemetry Adapter** | Normalizes and translates raw, heterogeneous sensor data streams into a standard format. | Raw sensor readings (e.g., CAN bus, ARINC 429). | Standardized, timestamped, validated telemetry objects. | Python/Rust | Streaming | MVP | Backend |
| **Ingestion Service** | Handles high-volume, real-time data streaming from all adapters and sources into the data processing pipeline. | Standardized telemetry streams, event payloads. | Streamed event records ready for validation. | Kafka/MQTT | Streaming | MVP | Backend |
| **Validator** | Ensures incoming data conforms to physical constraints, data types, and operational limits. | Streamed event records. | Validated/Filtered telemetry records, Validation alerts. | Python/Rules Engine | Streaming | MVP | Backend |
| **Digital Twin** | Maintains the current, holistic state of the engine and the twin model itself. The single source of truth for the engine's status. | Validated telemetry, Health indices, Model parameters. | Digital Twin State Object (JSON/Internal Model). | Java/Go | Near Real-time | MVP | Backend |
| **Physics Model** | Provides the core mathematical relationships defining engine performance boundaries and thermodynamic constraints. | Operational parameters, Component constraints. | Performance curves, Predicted physical states. | C++/Modelica | Near Real-time | MVP | Simulation |
| **Feature Engineering** | Calculates high-level metrics and features from raw/processed data (e.g., efficiency ratios, pressure differentials). | Processed telemetry, Load profile. | Engineered feature vectors. | Python (Pandas/NumPy) | Batch/Streaming | MVP | ML |
| **Anomaly Detector** | Identifies deviations from expected behavior patterns that may indicate component failure or operational abnormality. | Feature vectors, Historical data. | Anomaly score, Alert confidence, Anomaly type. | ML (Autoencoders, Isolation Forest) | Streaming | MVP | ML |
| **Fault Classifier** | Determines the root cause and classification of detected anomalies based on patterns. | Anomaly score, Sensor data pattern. | Classified fault state (e.g., 'Fuel Injector Failure', 'Bearing Wear'). | ML (Random Forest, RNN) | Near Real-time | MVP | ML |
| **RUL Estimator** | Estimates the Remaining Useful Life (RUL) of critical components based on degradation patterns. | Fault history, Degradation state, Operating cycles. | RUL estimate (time/cycles), Uncertainty interval. | ML (Survival Analysis, Regression) | Near Real-time | MVP | ML |
| **Health Index Calculator** | Aggregates various metrics (anomaly, degradation, efficiency) into a single, normalized operational health score (0-100). | Fault state, Degradation state, Anomaly score, Physics Model output. | Health Index (HI) score, Trend report. | Algorithms/Statistical Model | Near Real-time | MVP | Simulation |
| **Recommendation Engine** | Provides actionable, context-aware maintenance or operational recommendations. | Health Index, RUL, Fault Classification, Mission Plan. | Actionable recommendation (e.g., 'Schedule Inspection', 'Reduce Throttle Limit'). | ML/Rules-based System | Near Real-time | MVP | ML |
| **Mission Simulator** | Simulates an entire mission profile (pre-flight to landing) to test the digital twin's expected behavior against a proposed mission. | Target mission profile (waypoints, duration, etc.). | Projected twin state trajectory, Performance degradation curve. | Python/Numerical Solver | Batch | MVP | Simulation |
| **Replay Engine** | Allows playback of past telemetry data and recalculates the digital twin state and metrics to analyze historical incidents. | Historical telemetry data, Historical model versions. | Reconstructed twin state history, Failure point analysis. | Python (Time Series) | Batch | MVP | Backend |
| **Report Generator** | Creates formatted reports (PDF, JSON) summarizing the mission's performance, failures, and recommendations. | Mission summary, Health Index timeline, Fault reports. | Structured report file (PDF/JSON). | Python/Template Engine | Batch | MVP | Docs |
| **REST API** | Provides synchronous access point for external applications (e.g., dashboard, ground control) to read twin state and history. | API Requests (GET/POST). | JSON payload of current twin state or historical data. | Python/FastAPI | Real-time | MVP | Backend |
| **WebSocket Server** | Provides real-time, push-based updates of the digital twin state to connected frontends. | Internal Digital Twin State updates. | Real-time JSON stream of state updates. | WebSockets (e.g., Socket.IO) | Streaming | MVP | Backend |
| **Frontend** | User interface for visualizing the digital twin state, history, and recommendations. | REST API, WebSocket stream. | Interactive Dashboard, Visualization. | React/Vue.js | User Interface | MVP | Frontend |
| **Database** | Persistently stores all historical sensor data, state snapshots, and model metadata. | All data streams (telemetry, state, logs). | Persistent storage (Time-Series DB). | TimeScaleDB/InfluxDB | High throughput | MVP | Backend |
| **Model Registry** | Manages, versions, and serves all machine learning models and physics model coefficients used by the system. | Model artifacts, Metadata, Versioning info. | Versioned model artifacts (H5, ONNX). | MLflow/Custom Service | N/A | MVP | ML |
| **Logging** | Captures comprehensive logs of all module inputs, outputs, failures, and state transitions for auditing and debugging. | Events from all modules. | Structured log records (JSON). | ELK Stack/Fluentd | Streaming | MVP | Backend |

---

## PART B: Digital Twin State Definition

The Digital Twin state is the comprehensive, aggregated snapshot of the physical engine at a specific moment in time. It is the single source of truth for the engine's operational status, fusing raw measurements with derived predictions and analyses.

### Stored Data Elements

A comprehensive digital twin state must store the following parameters:

*   **Engine ID:** Unique identifier for the specific physical engine instance (e.g., `SN-AERO-26054-001`).
*   **Mission ID:** Unique identifier for the current mission or flight profile.
*   **Mission Phase:** Current phase of operation (e.g., `Pre-flight`, `Climb`, `Cruise`, `Descent`, `Shutdown`).
*   **Operating Conditions:** Current environmental and operational parameters (Altitude, Ambient Temp, Mach Number, Throttle setting, etc.).
*   **Observed Sensors:** The actual, validated, and timestamped measurements from the physical engine sensors.
*   **Expected Sensors:** The permissible range or expected nominal values for key sensors, used for validation.
*   **Residuals:** The difference (error) between the expected sensor readings (from the physics model) and the observed readings.
*   **Health State:** A descriptive, qualitative assessment of the engine's current mechanical integrity (e.g., `Nominal`, `Degraded`, `Critical`).
*   **Degradation State:** Quantitative measure of wear or degradation against baseline models (e.g., `Turbine Blade Creep: 12%`).
*   **Fault State:** The current, classified fault, if any (e.g., `None`, `High Vibration in Bearing B`, `Oil Pressure Drop`).
*   **Sensor Confidence:** A score indicating the reliability and quality of the sensor data inputs (e.g., 0.95 - High).
*   **RUL Estimate:** The estimated Remaining Useful Life for critical components.
*   **Uncertainty:** The confidence interval associated with the RUL estimate and other predictions.
*   **Alert Status:** A binary or severity-graded list of active alerts (e.g., `Warning: Low Oil Temp`, `Critical: Over-speed`).
*   **Last Update Time:** Timestamp of the most recent state update.
*   **Model Version:** Identifier for the specific versions of the Physics Model, Anomaly Detector, and Health Index Calculator used to generate this state.

### Sample Twin-State JSON Object

```json
{
  "engine_id": "SN-AERO-26054-001",
  "mission_id": "MISSION-20260904-A",
  "timestamp": "2026-09-04T21:05:30Z",
  "mission_phase": "Cruise",
  "operating_conditions": {
    "altitude_ft": 35000,
    "mach_number": 0.75,
    "throttle_percent": 75,
    "ambient_temp_c": -55
  },
  "observed_sensors": {
    "turbine_temp_c": 980.5,
    "oil_pressure_bar": 3.5,
    "vibration_rms_g": 0.85
  },
  "expected_sensors": {
    "turbine_temp_c_expected_range": [970.0, 990.0],
    "oil_pressure_bar_expected_range": [3.2, 4.0],
    "vibration_rms_g_nominal": 0.6
  },
  "residuals": {
    "turbine_temp_residual_c": 10.5,
    "vibration_residual_g": 0.25
  },
  "health_state": "Degraded",
  "degradation_state": {
    "turbine_blade_creep_pct": 14.2,
    "oil_filter_efficiency_pct": 88.0
  },
  "fault_state": "Turbine Temp Spike Warning",
  "sensor_confidence": 0.92,
  "rul_estimate": {
    "component": "Combustion Chamber",
    "estimate_hours": 450,
    "uncertainty_hours": 35
  },
  "alert_status": ["Warning: Turbine Temp Spike", "Attention: Low Oil Pressure Trend"],
  "last_update_time": "2026-09-04T21:05:30Z",
  "model_version": {
    "physics": "V2.1.3",
    "anomaly_detector": "V1.4.0",
    "health_index": "V1.0.1"
  }
}
```

### Key Concept Differentiation

These concepts represent different stages of data transformation and analysis, moving from raw measurement to actionable insight.

*   **Raw Telemetry:**
    *   **Definition:** The unaltered, unprocessed electrical signals or sensor readings captured from the physical engine at a precise moment. It is high-volume, noisy, and heterogeneous.
    *   **Example:** A sequence of raw voltage readings representing engine RPM, manifold pressure, and oil temperature before any filtering or standardization.

*   **Processed Telemetry:**
    *   **Definition:** Raw telemetry that has been cleaned, filtered, calibrated, validated, and standardized into a common format. It has been transformed into engineering units (e.g., PSI, degrees Celsius).
    *   **Example:** A record stating: `Timestamp: T, Altitude: 35000ft, RPM: 4500`.

*   **Digital Twin State:**
    *   **Definition:** The aggregated, near real-time snapshot of the engine's operational condition. It combines validated sensor data (Processed Telemetry), derived metrics (Health Index, Residuals), and core identifiers into a single, structured object. It answers the question: *"What is the engine doing right now, based on all available data?"*
    *   **Components:** Contains Observed, Expected, Health State, RUL, etc.

*   **AI Prediction:**
    *   **Definition:** A statistically modeled forecast or estimate of future conditions or outcomes (e.g., predicting the RUL, or predicting tomorrow's fuel consumption). Predictions are probabilistic and always come with an associated uncertainty bound.
    *   **Example:** "The remaining useful life of the primary bearing is predicted to be $450 \pm 35$ hours."

*   **Maintenance Recommendation:**
    *   **Definition:** An actionable, high-level decision provided by the system based on analyzing the Digital Twin State and AI Predictions. It suggests what action *should* be taken.
    *   **Example:** "Reduce maximum continuous thrust by 10% immediately to prevent critical component stress."

*   **Mission Summary:**
    *   **Definition:** A compiled, comprehensive narrative or structured report detailing the performance and events of a completed mission. It synthesizes data from the entire flight/operational profile.
    *   **Example:** A report stating: "Mission achieved 98% of nominal performance. An elevated vibration alert was logged during the descent phase, contributing to a marginal reduction in overall engine efficiency."
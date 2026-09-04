# SIH26054 Aero Piston Engine Digital Twin Architecture Design

This document outlines the core architectural modules, data definitions, state representations, and communication protocols for the Digital Twin of the SIH26054 aero piston engine.

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

---

## PART C: REST API Design

This section defines the comprehensive API endpoints required for synchronous, request/response interactions with the Digital Twin backend. All endpoints are assumed to be secured via API keys and versioned (e.g., `/api/v1/...`).

### 1. Mission Management

| Endpoint | Method | Purpose | Request Schema (brief) | Response Schema (brief) | Example Error Responses |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/missions/start` | POST | Initiates a new mission profile simulation or operational logging session. | `{ "mission_id": "...", "engine_id": "...", "profile": [...] }` | `{ "status": "started", "mission_id": "...", "start_time": "..." }` | 400: Invalid profile structure; 404: Engine ID not found. |
| `/api/missions/stop` | POST | Terminates the currently active mission session/logging. | `{ "mission_id": "..." }` | `{ "status": "stopped", "message": "Mission ended successfully." }` | 403: Not authorized; 404: Mission ID not found. |
| `/api/missions` | GET | Retrieves a list of all mission records for a given engine or time range. | Query Params: `engine_id`, `start_date`, `end_date` | `[{ "mission_id": "...", "status": "...", "start_time": "..." }, ...]` | 500: Database connection failure. |
| `/api/missions/{mission_id}` | GET | Retrieves the full, summary details of a specific historical mission. | None | `{ "summary": "...", "overall_health": "...", "duration": "..." }` | 404: Mission ID not found. |

### 2. Engine State & Telemetry

| Endpoint | Method | Purpose | Request Schema (brief) | Response Schema (brief) | Example Error Responses |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/engines/{engine_id}` | GET | Retrieves a high-level summary of the engine (e.g., serial number, model). | None | `{ "engine_id": "...", "model": "...", "status": "Online" }` | 404: Engine ID not found. |
| `/api/engines/{engine_id}/state` | GET | Fetches the latest, aggregated Digital Twin State object. | None | `{ "timestamp": "...", "health_state": "Degraded", "rul": 450, ... }` | 403: State data too old. |
| `/api/engines/{engine_id}/telemetry` | GET | Retrieves historical time-series sensor data for the specified period. | Query Params: `start_time`, `end_time`, `sensors` | `[ { "timestamp": "...", "sensor_x": 10.5, "sensor_y": 22.1 }, ... ]` | 400: Invalid time range parameters. |
| `/api/engines/{engine_id}/health` | GET | Retrieves the time-series history of the calculated Health Index (HI). | Query Params: `start_time`, `end_time` | `[ { "timestamp": "...", "hi_score": 95.2 }, ... ]` | 403: Unauthorized access to health data. |
| `/api/engines/{engine_id}/faults` | GET | Lists all recorded fault events and warnings for the engine. | Query Params: `severity` (Critical, Warning) | `[ { "fault_id": "...", "severity": "...", "timestamp": "...", "description": "..." }, ... ]` | 204: No faults recorded. |
| `/api/engines/{engine_id}/rul` | GET | Retrieves the historical and current Remaining Useful Life (RUL) estimates. | Query Params: `component` (e.g., "Bearing A") | `{ "component": "Bearing A", "current_rul_hrs": 450, "history": [...] }` | 404: Component not tracked. |

### 3. Simulation & Replay

| Endpoint | Method | Purpose | Request Schema (brief) | Response Schema (brief) | Example Error Responses |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/simulation/start` | POST | Initiates a predictive simulation run based on a proposed mission profile. | `{ "mission_id": "...", "profile": [...] }` | `{ "status": "running", "simulation_id": "...", "message": "Simulation started." }` | 400: Invalid input profile. |
| `/api/simulation/stop` | POST | Terminates an active simulation run. | `{ "simulation_id": "..." }` | `{ "status": "stopped", "message": "Simulation aborted." }` | 404: Simulation ID not found. |
| `/api/simulation/status` | GET | Checks the current status and progress of a running simulation. | Query Params: `simulation_id` | `{ "status": "Running", "progress_percent": 75, "eta_minutes": 45 }` | 404: Simulation ID not found. |
| `/api/faults/inject` | POST | Used in testing/staging to simulate a specific component fault for analysis. | `{ "fault_type": "Bearing Failure", "severity": "Critical", "duration_sec": 30 }` | `{ "status": "success", "message": "Fault injection simulated." }` | 403: Requires elevated permissions. |
| `/api/replay/start` | POST | Initiates the replay of a historical data segment against the current model. | `{ "mission_id": "...", "start_time": "...", "end_time": "..." }` | `{ "status": "running", "replay_id": "...", "message": "Replay started." }` | 400: Time range is invalid or too large. |
| `/api/replay/stop` | POST | Stops an active replay session. | `{ "replay_id": "..." }` | `{ "status": "stopped", "message": "Replay aborted." }` | 404: Replay ID not found. |
| `/api/replay/status` | GET | Reports the status and progress of a running replay analysis. | Query Params: `replay_id` | `{ "status": "Processing", "progress_percent": 60, "analysis_metrics": {...} }` | 404: Replay ID not found. |

### 4. Reporting & System

| Endpoint | Method | Purpose | Request Schema (brief) | Response Schema (brief) | Example Error Responses |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/reports/{mission_id}` | GET | Generates and downloads a comprehensive PDF/JSON report for a mission. | None | `[File Stream: Report.pdf]` | 404: Mission ID not found; 503: Report generation service unavailable. |
| `/api/system/health` | GET | Checks the operational health and status of all connected backend services (APIs, Database, Services). | None | `{ "service": "Database", "status": "Operational", "last_check": "..." }` | 500: Internal system failure. |

---

## PART D: WebSocket Design (Real-Time Communication)

The WebSocket channel provides a persistent, bi-directional communication link for real-time updates, bypassing the latency of standard REST polling calls.

### Protocol Specifications

*   **WebSocket URL:** `wss://api.digitaltwin.com/ws/v1/{engine_id}`
*   **Connection Behavior:** Clients establish a connection and immediately send a **`subscribe`** message indicating interest in specific data streams (e.g., `telemetry`, `health`, `faults`).
*   **Message Types:** All messages are JSON objects requiring a mandatory `type` field to dictate the content.
*   **Message Frequency:**
    *   `telemetry_update`: High frequency (10 - 50 ms).
    *   `twin_state_update`: Moderate frequency (100 - 500 ms, or upon significant change).
    *   `anomaly_detected`, `fault_prediction`, `health_update`, `maintenance_advisory`: Event-driven (Immediate, upon occurrence).
    *   `mission_phase_change`: Event-driven (Immediate).
    *   `simulation_status`: Variable (As needed for status updates).
    *   `system_error`: Event-driven (Immediate).
*   **Reconnection Behavior:** Clients must implement exponential backoff reconnection logic. Attempt connection on failure with increasing delays (e.g., 1s, 2s, 4s, 8s...).
*   **Heartbeat Mechanism:** A mandatory bi-directional heartbeat is required. Both client and server must send a lightweight `{ "type": "heartbeat", "timestamp": "..." }` message every 30 seconds. Failure to receive a response within 90 seconds triggers a disconnect and reconnection attempt.
*   **Error Message Format:** Errors are encapsulated JSON messages: `{"type": "system_error", "code": 400, "message": "Invalid subscription requested: 'telemetry' is not supported.", "details": "..."}`.
*   **Backpressure Handling:** If the client cannot process the high-frequency `telemetry_update` stream, it should send a `flow_control` message: `{"type": "flow_control", "action": "throttle", "priority": "telemetry"}`, signaling the server to temporarily reduce the rate limit for that specific stream type.

### Example JSON Messages

#### 1. `telemetry_update` (High Frequency)
```json
{
  "type": "telemetry_update",
  "timestamp": "2026-09-04T21:06:00Z",
  "data": {
    "rpm": 4500,
    "oil_pressure_bar": 3.5,
    "turbine_temp_c": 980.5
  },
  "source": "adapter"
}
```

#### 2. `twin_state_update` (Medium Frequency)
```json
{
  "type": "twin_state_update",
  "timestamp": "2026-09-04T21:06:00Z",
  "state": {
    "mission_phase": "Cruise",
    "health_state": "Degraded",
    "hi_score": 85.2,
    "rul_estimate_hrs": 450,
    "alerts": ["Warning: Low Oil Pressure Trend"]
  }
}
```

#### 3. `anomaly_detected` (Event Driven)
```json
{
  "type": "anomaly_detected",
  "timestamp": "2026-09-04T21:06:05Z",
  "data": {
    "metric": "Vibration RMS",
    "observed_value": 0.95,
    "expected_range": [0.4, 0.7],
    "score": 0.91,
    "confidence": 0.99
  }
}
```

#### 4. `fault_prediction` (Event Driven)
```json
{
  "type": "fault_prediction",
  "timestamp": "2026-09-04T21:06:10Z",
  "fault": {
    "fault_id": "BHARE_003",
    "name": "Bearing High Vibration",
    "severity": "Critical",
    "description": "Vibration amplitude exceeds safety threshold. Immediate inspection required.",
    "predicted_failure_time": "2026-09-05T10:00:00Z"
  }
}
```

#### 5. `health_update` (Event Driven/Frequency)
```json
{
  "type": "health_update",
  "timestamp": "2026-09-04T21:06:15Z",
  "data": {
    "component": "Turbine Assembly",
    "health_score": 0.82,
    "trend_vector": [14.2, 0.5, 0.1],
    "status_description": "Accelerating degradation rate observed."
  }
}
```

#### 6. `rul_update` (Event Driven/Frequency)
```json
{
  "type": "rul_update",
  "timestamp": "2026-09-04T21:06:20Z",
  "data": {
    "component": "Combustion Chamber",
    "remaining_cycles": 500,
    "estimate_hours": 448,
    "confidence_interval_hrs": [30, 460]
  }
}
```

#### 7. `maintenance_advisory` (Event Driven)
```json
{
  "type": "maintenance_advisory",
  "timestamp": "2026-09-04T21:06:25Z",
  "recommendation": {
    "action": "Schedule Inspection",
    "priority": "High",
    "details": "Scheduled inspection of Turbine Blades required within the next 10 operational hours.",
    "source_module": "Recommendation Engine"
  }
}
```

#### 8. `mission_phase_change` (Event Driven)
```json
{
  "type": "mission_phase_change",
  "timestamp": "2026-09-04T21:06:30Z",
  "old_phase": "Cruise",
  "new_phase": "Descent",
  "details": "Commencing descent sequence as per flight plan."
}
```

#### 9. `simulation_status` (Event Driven/Status)
```json
{
  "type": "simulation_status",
  "timestamp": "2026-09-04T21:06:35Z",
  "data": {
    "simulation_id": "SIM-12345",
    "status": "Running",
    "progress_percent": 50,
    "progress_detail": "Mid-altitude simulation, reaching Mach 0.6."
  }
}
```

#### 10. `system_error` (Event Driven/Error)
```json
{
  "type": "system_error",
  "timestamp": "2026-09-04T21:06:40Z",
  "error_code": 503,
  "message": "Telemetry adapter failed to connect to CAN bus.",
  "source_module": "Telemetry Adapter",
  "details": "Check physical connections and service status."
}
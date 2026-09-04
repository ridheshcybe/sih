# Digital Twin System Architecture Documentation

This document outlines the proposed architecture for the SIH26054 Aero Piston Engine Digital Twin, covering the minimal relational database schema (Part A) and the final monorepo structure (Part B).

## Part A: Database Schema Design

We utilize a relational schema to model the complex relationships between operational data, prediction results, and maintenance activities.

### Schema Overview

| Table Name | Description | PK | Indexes | MVP/Future |
| :--- | :--- | :--- | :--- | :--- |
| `engines` | Core engine metadata (serial number, model, etc.) | `engine_id` | `engine_serial_number` | MVP |
| `missions` | Records of operational deployments or flights. | `mission_id` | `engine_id`, `start_time` | MVP |
| `telemetry` | High-frequency, time-series sensor readings. | `(engine_id, timestamp, sensor_id)` | `timestamp`, `sensor_id` | MVP |
| `twin_states` | Snapshot of key operating parameters at specific times. | `state_id` | `engine_id`, `timestamp` | MVP |
| `anomalies` | Detected deviations from normal operating parameters. | `anomaly_id` | `engine_id`, `timestamp` | MVP |
| `fault_predictions` | Predicted failures or component degradation events. | `prediction_id` | `engine_id`, `fault_type`, `prediction_timestamp` | MVP |
| `rul_predictions` | Remaining Useful Life estimations for components. | `rul_id` | `engine_id`, `component`, `prediction_date` | MVP |
| `maintenance_advisories` | Recommended maintenance actions based on predictions/anomalies. | `advisory_id` | `engine_id`, `priority`, `issued_date` | MVP |
| `mission_reports` | Summaries and analysis of completed missions. | `report_id` | `mission_id` | MVP |
| `fault_injections` | Data used for simulating and testing fault scenarios. | `injection_id` | `test_case_id`, `fault_type` | Future |
| `model_versions` | Records of ML model versions used for predictions. | `version_id` | `model_name`, `version` | MVP |
| `system_events` | Non-sensor related events (e.g., system reboots, mode changes). | `event_id` | `engine_id`, `timestamp` | MVP |

---

### Detailed Table Specifications

**1. `engines`**
*   **Columns:**
    *   `engine_id` (VARCHAR): Unique UUID assigned to the twin. (PK)
    *   `engine_serial_number` (VARCHAR): Manufacturer serial number.
    *   `model_type` (VARCHAR): e.g., 'AeroPiston-SIH26054'.
    *   `manufacturer` (VARCHAR): e.g., 'Rolls-Royce'.
    *   `acquisition_date` (DATE): Date the engine was integrated.
    *   `is_active` (BOOLEAN): Status flag.
*   **Primary Key:** `engine_id`
*   **Foreign Keys:** None
*   **Indexes:** `engine_serial_number` (for quick lookup)
*   **MVP/Future:** MVP

**2. `missions`**
*   **Columns:**
    *   `mission_id` (UUID): Unique ID for this mission run. (PK)
    *   `engine_id` (VARCHAR): FK to `engines`.
    *   `start_time` (TIMESTAMP): Start time of the mission.
    *   `end_time` (TIMESTAMP): End time of the mission.
    *   `duration` (INTEGER): Calculated duration in minutes.
    *   `mission_purpose` (VARCHAR): e.g., 'Testing', 'Operational'.
*   **Primary Key:** `mission_id`
*   **Foreign Keys:** `engine_id` -> `engines.engine_id`
*   **Indexes:** `engine_id`, `start_time`
*   **MVP/Future:** MVP

**3. `telemetry`**
*   **Columns:**
    *   `engine_id` (VARCHAR): FK to `engines`.
    *   `timestamp` (TIMESTAMP): Time of the measurement.
    *   `sensor_id` (VARCHAR): Identifier for the sensor (e.g., 'OilTemp_A').
    *   `value` (FLOAT): The recorded reading.
    *   `unit` (VARCHAR): Unit of measurement (e.g., 'PSI', 'C').
*   **Primary Key:** Composite (`engine_id`, `timestamp`, `sensor_id`)
*   **Foreign Keys:** `engine_id` -> `engines.engine_id`
*   **Indexes:** `timestamp`, `sensor_id` (Critical for time-series querying)
*   **MVP/Future:** MVP

**4. `twin_states`**
*   **Columns:**
    *   `state_id` (UUID): Unique snapshot ID. (PK)
    *   `engine_id` (VARCHAR): FK to `engines`.
    *   `timestamp` (TIMESTAMP): Time of the state snapshot.
    *   `operational_status` (VARCHAR): Current status (e.g., 'Running', 'Idle').
    *   `key_parameters` (JSONB/TEXT): JSON blob of aggregated parameters (RPM, etc.).
*   **Primary Key:** `state_id`
*   **Foreign Keys:** `engine_id` -> `engines.engine_id`
*   **Indexes:** `engine_id`, `timestamp`
*   **MVP/Future:** MVP

**5. `anomalies`**
*   **Columns:**
    *   `anomaly_id` (UUID): Unique ID. (PK)
    *   `engine_id` (VARCHAR): FK to `engines`.
    *   `timestamp` (TIMESTAMP): Time the anomaly was detected.
    *   `anomaly_type` (VARCHAR): e.g., 'HighVibration', 'TempSpike'.
    *   `severity` (VARCHAR): 'Critical', 'High', 'Medium', 'Low'.
    *   `description` (TEXT): Detailed description of the event.
    *   `source_data_ref` (VARCHAR): Reference to the triggering telemetry record.
*   **Primary Key:** `anomaly_id`
*   **Foreign Keys:** `engine_id` -> `engines.engine_id`
*   **Indexes:** `engine_id`, `timestamp`, `severity`
*   **MVP/Future:** MVP

**6. `fault_predictions`**
*   **Columns:**
    *   `prediction_id` (UUID): Unique ID. (PK)
    *   `engine_id` (VARCHAR): FK to `engines`.
    *   `fault_type` (VARCHAR): e.g., 'TurbineBladeFailure'.
    *   `prediction_timestamp` (TIMESTAMP): When the prediction was made.
    *   `confidence_score` (FLOAT): ML model confidence (0.0 to 1.0).
    *   `impact_assessment` (TEXT): Predicted operational impact.
*   **Primary Key:** `prediction_id`
*   **Foreign Keys:** `engine_id` -> `engines.engine_id`
*   **Indexes:** `engine_id`, `fault_type`, `prediction_timestamp`
*   **MVP/Future:** MVP

**7. `rul_predictions`**
*   **Columns:**
    *   `rul_id` (UUID): Unique ID. (PK)
    *   `engine_id` (VARCHAR): FK to `engines`.
    *   `component` (VARCHAR): Component being predicted (e.g., 'OilPump').
    *   `prediction_date` (DATE): Date of the prediction.
    *   `estimated_rul_hours` (FLOAT): Remaining Useful Life in hours.
    *   `model_version_id` (VARCHAR): FK to `model_versions`.
*   **Primary Key:** `rul_id`
*   **Foreign Keys:** `engine_id` -> `engines.engine_id`, `model_version_id` -> `model_versions.version_id`
*   **Indexes:** `engine_id`, `component`, `prediction_date`
*   **MVP/Future:** MVP

**8. `maintenance_advisories`**
*   **Columns:**
    *   `advisory_id` (UUID): Unique ID. (PK)
    *   `engine_id` (VARCHAR): FK to `engines`.
    *   `issued_date` (TIMESTAMP): When the advisory was generated.
    *   `priority` (VARCHAR): 'Immediate', 'Scheduled', 'Monitor'.
    *   `advisory_details` (TEXT): Recommended action.
    *   `is_resolved` (BOOLEAN): Status of the advisory.
*   **Primary Key:** `advisory_id`
*   **Foreign Keys:** `engine_id` -> `engines.engine_id`
*   **Indexes:** `engine_id`, `priority`, `issued_date`
*   **MVP/Future:** MVP

**9. `mission_reports`**
*   **Columns:**
    *   `report_id` (UUID): Unique ID. (PK)
    *   `mission_id` (UUID): FK to `missions`.
    *   `report_generated_date` (DATE): Date the report was finalized.
    *   `summary_text` (TEXT): Executive summary.
    *   `metrics_data` (JSONB): Aggregated metrics (min/max/avg temps, run time).
    *   `final_assessment` (VARCHAR): Overall system health grade.
*   **Primary Key:** `report_id`
*   **Foreign Keys:** `mission_id` -> `missions.mission_id`
*   **Indexes:** `mission_id`
*   **MVP/Future:** MVP

**10. `fault_injections`**
*   **Columns:**
    *   `injection_id` (UUID): Unique ID. (PK)
    *   `test_case_id` (VARCHAR): Identifier for the test suite.
    *   `fault_type` (VARCHAR): Type of fault (e.g., 'OilPumpFailure').
    *   `severity` (VARCHAR): Simulated severity.
    *   `parameters` (JSONB): Specific fault parameters (e.g., failure rate).
    *   `injection_timestamp` (TIMESTAMP): When the fault was injected.
*   **Primary Key:** `injection_id`
*   **Foreign Keys:** None
*   **Indexes:** `test_case_id`, `fault_type`
*   **MVP/Future:** Future (Primarily for ML/Testing)

**11. `model_versions`**
*   **Columns:**
    *   `version_id` (VARCHAR): Unique model identifier (e.g., 'v1.2.0_anomaly'). (PK)
    *   `model_name` (VARCHAR): Descriptive name (e.g., 'AnomalyDetector').
    *   `training_data_hash` (VARCHAR): Hash of data used for training.
    *   `trained_timestamp` (TIMESTAMP): Date of training completion.
    *   `metrics` (JSONB): Performance metrics (AUC, F1 Score, etc.).
*   **Primary Key:** `version_id`
*   **Foreign Keys:** None
*   **Indexes:** `model_name`
*   **MVP/Future:** MVP

**12. `system_events`**
*   **Columns:**
    *   `event_id` (UUID): Unique ID. (PK)
    *   `engine_id` (VARCHAR): FK to `engines`.
    *   `timestamp` (TIMESTAMP): Time of the event.
    *   `event_type` (VARCHAR): e.g., 'SoftwareUpdate', 'ModeSwitch', 'Shutdown'.
    *   `description` (TEXT): Detailed event notes.
    *   `source` (VARCHAR): Which component logged the event.
*   **Primary Key:** `event_id`
*   **Foreign Keys:** `engine_id` -> `engines.engine_id`
*   **Indexes:** `engine_id`, `timestamp`
*   **MVP/Future:** MVP

---

### Database Backend Selection Analysis (SQLite vs. PostgreSQL/TimescaleDB)

**1. Why SQLite is Sufficient for the Prototype (MVP):**
SQLite is excellent for prototypes and localized development environments.
*   **Pros:** Zero setup required (it's a single file), incredibly simple to implement for a Minimum Viable Product (MVP), and easy to embed directly into a single service/tool.
*   **Cons:** It is not designed for concurrent, high-volume, multi-client write operations. As the number of connected clients and the volume of telemetry data scale, SQLite will introduce significant write contention and performance bottlenecks.
*   **Use Case:** Ideal for initial data persistence, localized testing, and single-user development where high concurrency is not a concern.

**2. What Changes with PostgreSQL/TimescaleDB:**
For a production, enterprise-grade digital twin that handles massive streams of sensor data, a full-featured, scalable database like PostgreSQL with the TimescaleDB extension is necessary.

*   **Scalability and Concurrency:** PostgreSQL manages concurrent reads/writes from multiple services, which is mandatory for a real-time digital twin.
*   **Time-Series Optimization (TimescaleDB):**
    *   **Hyperscale Extension:** TimescaleDB implements the **time-series pattern** using "Hypertables" (specialized PostgreSQL tables built on chunking/partitioning). This is critical for the `telemetry` table. Instead of one massive table, data is automatically partitioned by time intervals (e.g., one chunk per day/hour). This drastically improves query performance for time range lookups (`SELECT * WHERE timestamp BETWEEN X AND Y`).
    *   **Compression:** It offers built-in time-series compression techniques, saving enormous amounts of storage space on raw sensor data.
*   **Data Modeling Improvement:** While the relational schema remains valid, the implementation changes:
    *   `telemetry` table would become a TimescaleDB Hypertable.
    *   The database schema would rely heavily on **JSONB** fields (for flexible key-value pairs like `key_parameters` or `metrics_data`) combined with the relational structure for strong consistency checks.
    *   The application layer would switch from simple file access to connection pooling and transaction management for maximum throughput.

---

## Part B: Monorepo Structure and Files

The proposed monorepo structure is designed for modularity, separation of concerns, and clear scaling paths.

```
project-root/
├── backend/             # Core APIs and business logic (Python/FastAPI)
│   ├── main.py          # FastAPI application entry point (Initializes routers)
│   ├── api/
│   │   └── routes.py    # API router definitions (HTTP endpoint mapping)
│   └── services/        # Business logic implementations (Service classes)
│       ├── digital_twin.py  # Handles telemetry ingestion and state retrieval
│       ├── health_index.py  # Calculates comprehensive health scores
│       └── predictor.py     # Orchestrates RUL and Fault Prediction models
├── frontend/            # User Interface (React/Next.js)
│   ├── src/
│   │   ├── pages/
│   │   │   └── Dashboard.jsx # Main page view of the twin
│   │   └── components/
│   │       ├── HealthGauge.jsx # Component for visual health score display
│   │       └── TelemetryChart.jsx # Component for time-series chart visualization
├── ml/                  # Machine Learning training scripts
│   ├── train_anomaly.py     # Training script for anomaly detection (e.g., Isolation Forest)
│   ├── train_fault_classifier.py # Training script for fault classification (e.g., CNN)
│   └── train_rul.py         # Training script for Remaining Useful Life (e.g., Survival Analysis)
├── simulator/           # Engine physics and mission simulation logic
│   ├── engine_model.py      # Core mathematical model (e.g., governing equations)
│   ├── mission_profiles.py  # Templates for operational profiles (e.g., taxi, cruise)
│   └── fault_injection.py    # Logic to inject simulated faults into the engine model
├── data/                # Persistent/Input data (e.g., ground truth datasets, calibration files)
├── models/              # Stored ML artifacts (e.g., pickled models, ONNX files)
├── reports/             # Generated analysis files (PDFs, reports)
├── docs/                # Project documentation and architectural diagrams
├── tests/               # Unit, integration, and end-to-end test suite
├── docker/              # Docker Compose and Dockerfile setup for deployment
├── scripts/             # Utility scripts (e.g., data ETL, schema initialization)
└── README.md            # Project overview and setup instructions
```

### Conclusion
The architecture is modular, separating concerns into distinct services (`backend/services`), clearly defining the data flow from `simulator` $\rightarrow$ `data` $\rightarrow$ `ml` $\rightarrow$ `backend` $\rightarrow$ `reports` $\rightarrow$ `frontend`.
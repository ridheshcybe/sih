# SIH26054 API Contract

The prototype uses synthetic telemetry and is not flight-certified or validated against real engine data.

## Base paths

- REST: `http://localhost:8000/api`
- WebSocket: `ws://localhost:8000/ws/telemetry/{engine_id}`

## REST endpoints

### `GET /engines/{engine_id}/state`

Returns the latest in-memory twin state:

```json
{
    "engine_id": "ENG-001",
    "status": "OPERATIONAL",
    "health_index": 96.0,
    "anomaly_score": 0.04,
    "sensors": {"rpm": 2450, "cht": 168, "egt": 610, "oil_pressure": 46},
    "fault_probs": {}
}
```

Health Index is normalized from `0` to `100`; status is `OPERATIONAL`, `WARNING`, or `CRITICAL`.

### `GET /engines/{engine_id}/telemetry`

Returns the latest buffered telemetry as `{ "engine_id": string, "data": array }`. Each row includes timestamp, engine/mission IDs, core sensors, electrical sensors, and altitude.

### `POST /missions/start`

Request: `{ "engine_id": "ENG-001", "profile_id": "normal_cruise" }`.
Returns a mission object containing `mission_id`, `engine_id`, `profile_id`, `status`, and buffered telemetry.

### `POST /missions/stop`

Request: `{ "mission_id": "uuid" }`. Marks the mission complete and stops its demo loop.

### `POST /faults/inject`

Request: `{ "engine_id": "ENG-001", "fault_type": "overheating", "severity": 0.7, "start_time": null }`.
Supported fault types are `injector_degradation`, `lubrication_issue`, `overheating`, `sensor_drift`, `abnormal_vibration`, and `battery_alternator_degradation`.

### `POST /telemetry/ingest`

Accepts one telemetry object or a list up to `TWIN_BATCH_LIMIT` rows. Rows use string `engine_id` and `mission_id` values and require timestamp, core sensor, battery, and alternator fields.

## WebSocket events

Connect to `/ws/telemetry/{engine_id}`. Messages use `{ "event": string, "payload": object }`.

- `telemetry_update`: one raw telemetry row.
- `twin_state_update`: latest Health Index, anomaly score, status, sensors, and fault probabilities.

The frontend retries disconnected sockets up to three times with a three-second delay.
# API Contract: SIH26054 Digital Twin Backend

This document defines the RESTful API endpoints and WebSocket message contracts for the FastAPI backend, ensuring clear communication between the frontend, simulator, and ML services.

## 🌐 I. RESTful Endpoints (FastAPI)

### 1. Mission Management (`/api/v1/missions`)

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/` | Starts a new mission run and returns a `mission_id`. |
| `GET` | `/{mission_id}` | Retrieves the full history and summary state for a given mission. |
| `GET` | `/list` | Lists all recorded mission IDs. |

**A. Start Mission (POST /)**
*   **Request Schema:**
    *   `mission_name` (str, required): Descriptive name of the mission.
    *   `profile_id` (str, required): ID of the mission profile to use (e.g., 'NormalCruise', 'HighAltitude').
    *   `initial_params` (dict, optional): Initial engine parameters.
*   **Response Schema:**
    *   `mission_id` (str): Unique identifier for the new mission.
    *   `status` (str): `STARTED`.
*   **Example:**
    *   *Request:* `{"mission_name": "TestFlight-1", "profile_id": "NormalCruise", "initial_params": {"alt": 1000, "rpm": 2000}}`
    *   *Response:* `{"mission_id": "AABBCCDD-1234", "status": "STARTED"}`

### 2. Engine State & Data (`/api/v1/engines/{engine_id}`)

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `GET` | `/state` | Gets the current, aggregated operational state of the engine (Digital Twin summary). |
| `GET` | `/telemetry` | Retrieves the last N raw telemetry readings (historical time series). |
| `GET` | `/health` | Get calculated Health Index and its trend over time. |
| `GET` | `/faults` | Retrieves a list of detected or predicted faults. |
| `GET` | `/rul` | Retrieves the Remaining Useful Life (RUL) estimate. |

**A. Get Engine State (GET /state)**
*   **Purpose:** Provides the primary dashboard view—a snapshot of the engine's current condition.
*   **Request Schema:** (None)
*   **Response Schema:**
    *   `engine_id` (str): ID of the engine.
    *   `status` (str): `OPERATIONAL`, `DEGRADED`, `FAULT`.
    *   `health_index` (float): Current health score (0.0 - 1.0).
    *   `rpm` (float): Current Revolutions Per Minute.
    *   `oil_temp` (float): Oil temperature (°C).
    *   `vibration_level` (float): Current vibration level.
*   **Example:**
    *   *Request:* `GET /api/v1/engines/ENG-001/state`
    *   *Response:* `{"engine_id": "ENG-001", "status": "DEGRADED", "health_index": 0.85, "rpm": 1980.5, "oil_temp": 75.2, "vibration_level": 0.45}`

### 3. Simulation Control (`/api/v1/simulation`)

| Method | Path | Purpose |
| :--- | :--- | :--- |
| `POST` | `/start` | Initializes and starts the simulator process. |
| `POST` | `/stop` | Stops the simulator process. |
| `GET` | `/status` | Reports the simulator's current running state. |

**A. Start Simulator (POST /start)**
*   **Request Schema:**
    *   `profile_id` (str): Mission profile to load.
    *   `engine_id` (str): Engine being simulated.
*   **Response Schema:**
    *   `message` (str): Confirmation message.
    *   `is_running` (bool): Initial status check.
*   **Example:**
    *   *Request:* `{"profile_id": "HighPowerTest", "engine_id": "ENG-002"}`
    *   *Response:* `{"message": "Simulation initiated for ENG-002.", "is_running": true}`

## 📡 II. WebSocket Contract

WebSockets (`/ws/telemetry/{engine_id}`) are the primary channel for real-time data streaming.

**A. Message Types & Payloads:**

1.  **`telemetry_update` (Core Data):** Raw sensor readings sent from the simulator.
    *   *Example:* `{"type": "telemetry_update", "timestamp": 1678886400.0, "data": {"rpm": 1950.2, "oil_temp": 74.5, "fuel_pressure": 350.1, "vibration": 0.38}}`
2.  **`twin_state_update` (Aggregated Health):** The ML backend's interpretation of the raw data.
    *   *Example:* `{"type": "twin_state_update", "timestamp": 1678886400.1, "data": {"status": "OPERATIONAL", "health_index": 0.92, "anomaly_score": 0.05}}`
3.  **`anomaly_detected` (Alert):** Triggered when ML detects a deviation.
    *   *Example:* `{"type": "anomaly_detected", "timestamp": 1678886400.2, "alert_level": "WARNING", "feature": "VIBRATION", "details": "Vibration exceeded 3-sigma limit."}`
4.  **`rul_update` (Prediction):** Major update on Remaining Useful Life.
    *   *Example:* `{"type": "rul_update", "timestamp": 1678886400.3, "remaining_hours": 45.5, "confidence": 0.95, "reason": "Based on current degradation trend."}`
5.  **`system_error` (System Feedback):** Non-data critical errors.
    *   *Example:* `{"type": "system_error", "timestamp": 1678886400.4, "severity": "CRITICAL", "message": "Database connection lost. Data saving paused."}`
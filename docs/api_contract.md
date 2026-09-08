# API Contract — SIH26054 Backend

Interactive docs: http://localhost:8000/docs (Swagger UI).

## REST endpoints

### System

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/system/health` | Liveness check → `{status, timestamp}` |
| GET | `/api/system/info` | App version, ML model status, sim/replay state |

### Missions (`/api/v1/missions`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/missions` | Start a mission (body: `{mission_name, profile_id, engine_id, duration_s?}`) → `{mission_id, status, engine_id, profile_id}` |
| POST | `/api/v1/missions/{mission_id}/stop` | Stop a mission → `{mission_id, status}` |
| GET | `/api/v1/missions/list` | List missions (newest first) |
| GET | `/api/v1/missions/{mission_id}` | Mission detail + counts + latest health index |

### Engines (`/api/v1/engines/{engine_id}`)

| Method | Path | Purpose |
|---|---|---|
| GET | `.../state` | Latest twin state + latest telemetry + mission status |
| GET | `.../telemetry?limit=50` | Last N telemetry rows (reversed chronological) |
| GET | `.../health` | `{health_index, trend:[{timestamp, health_index}]}` (last 120) |
| GET | `.../faults` | Fault predictions for the latest mission |
| GET | `.../rul` | `{rul_estimate, rul_confidence, degradation_level}` |

### Simulation (`/api/v1/simulation`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/start` | `{profile_id, engine_id, duration_s?}` → starts the in-process simulator. Validates profile (422) and engine (404) up front. |
| POST | `/stop` | `{engine_id}` → stops it |
| GET | `/status` | `{simulation: {engine_id: {running, mission_id, elapsed_sec}}, replay: {...}}` |

### Faults (`/api/v1/faults`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/inject` | `{engine_id, fault_type, severity(0.05–1), duration_sec, pattern(gradual\|sudden), start_offset_sec?}` → `{success, message, fault_type, severity, start_time_sec}`. Requires a running mission (409 otherwise). |

### Replay (`/api/v1/replay`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/start` | `{mission_id, speed?}` → replays stored mission over WS at `speed`× |
| POST | `/stop` | Stop replay |
| GET | `/status` | `{replaying, mission_id}` |

### Reports (`/api/v1/reports`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/{mission_id}` | Mission diagnostic summary (generates on first access) |
| POST | `/{mission_id}/generate` | Regenerate + persist summary |

### Telemetry ingest (`/api/v1/telemetry`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/ingest` | Push one row from the standalone simulator (`--stream` mode). Body = one telemetry row incl. `mission_id`. Validates required sensors; 422 on rejection. |

## WebSocket — `/ws/telemetry/{engine_id}`

Server→client JSON messages. **Throttled to max 5 msg/s per client per event.**
Client→server messages are ignored (used for disconnect detection).

| Event | Payload (key fields) |
|---|---|
| `telemetry_update` | full raw row: `timestamp, phase, throttle, rpm, cht, egt, oil_pressure, oil_temperature, fuel_flow, vibration_rms, battery_voltage, alternator_current, injection_timing, altitude, ambient_temperature, fault_label, degradation_level` |
| `twin_state_update` | `mission_id, timestamp, status, health_index, anomaly_score, degradation_level, rul_estimate, rul_confidence, top_fault, top_probability, fault_probs, residuals, sensors, expected_sensors, advisory{text, priority}` |
| `fault_prediction` | `{fault_type, probability, timestamp}` |
| `simulation_status` | `{running, mission_id}` |
| `replay_status` | `{replaying, mission_id, progress}` |
| `system_error` | `{severity, message}` |

Example `twin_state_update`:

```json
{
  "event": "twin_state_update",
  "payload": {
    "mission_id": "M-1A2B3C4D",
    "timestamp": "2026-09-09T12:00:00.123+00:00",
    "status": "DEGRADED",
    "health_index": 68.4,
    "anomaly_score": 0.61,
    "degradation_level": 0.42,
    "rul_estimate": 290.1,
    "rul_confidence": "medium",
    "top_fault": "injector_degradation",
    "top_probability": 0.87,
    "fault_probs": { "none": 0.02, "injector_degradation": 0.87, "...": 0.0 },
    "residuals": { "cht": 18.2, "oil_pressure": -0.31 },
    "sensors": { "cht": 131.4, "egt": 612.2, "oil_pressure": 3.44 },
    "advisory": {
      "text": "Fuel injector degradation detected. Schedule injector service within 25 flight hours and monitor fuel flow.",
      "priority": "MEDIUM"
    }
  }
}
```

## Mission statuses

`running` → `completed` (duration reached or stopped; report auto-generated)
or `failed` (simulation loop crashed; no report).

## Status codes

- `409` — mission already running / fault injection without a running mission /
  replay already in progress.
- `404` — unknown mission, engine, or report; also unknown `engine_id` when
  starting a mission or simulation.
- `422` — schema validation failure (incl. rejected telemetry rows) and unknown
  `profile_id` when starting a mission or simulation.
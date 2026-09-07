"""
backend/services/digital_twin.py -- Twin update service with ML integration (Task 4.4).

update_twin_state(mission_id, telemetry_window) is the integration point:
  telemetry window -> ml feature extraction -> predict_all() -> twin state

- Persists predictions to SQLite: twin_states (anomaly_score, degradation,
  rul) and fault_predictions (fault_probs rows).
- Falls back gracefully: missing/corrupt model files yield safe defaults from
  ml/inference.py; DB schema gaps are logged, never crash the request path.
- Broadcast hook: the WebSocket layer (Task 2.4) registers a callback via
  add_ws_broadcast_hook() and receives every twin state update.

All data is synthetic; this prototype is not flight-certified.
"""

import json
import logging
import math
import os
import random
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# --- ML integration (safe: works even if models/ is empty) ---
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ml.features import extract_features, SENSORS          # noqa: E402
from backend.services.ml_inference import predict_all       # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("digital_twin")

# --- SQLite setup (SQLite per MVP; swap URL for Postgres later) ---
DB_PATH = os.environ.get("TWIN_DB_PATH",
                         os.path.join(os.path.dirname(_ROOT), "backend", "digital_twin.db"))

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS engines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        engine_id TEXT UNIQUE, name TEXT, status TEXT DEFAULT 'OPERATIONAL',
        created_at TEXT)""",
    """CREATE TABLE IF NOT EXISTS missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_id TEXT UNIQUE, engine_id TEXT, profile_id TEXT,
        start_time TEXT, end_time TEXT, status TEXT DEFAULT 'RUNNING')""",
    """CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        engine_id TEXT, mission_id TEXT, timestamp TEXT,
        rpm REAL, cht REAL, egt REAL, oil_pressure REAL, oil_temperature REAL,
        fuel_flow REAL, vibration_rms REAL, battery_voltage REAL,
        alternator_current REAL, fault_label TEXT)""",
    """CREATE TABLE IF NOT EXISTS twin_states (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_id TEXT, engine_id TEXT, timestamp TEXT,
        expected_sensors_json TEXT, residuals_json TEXT,
        health_index REAL, anomaly_score REAL,
        degradation_level REAL, rul_estimate REAL, rul_confidence TEXT,
        fault_probs_json TEXT, ml_latency_ms REAL)""",
    """CREATE TABLE IF NOT EXISTS fault_predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mission_id TEXT, engine_id TEXT, timestamp TEXT,
        fault_type TEXT, probability REAL, severity TEXT)""",
]

_REQUIRED_COLUMNS = {
    "twin_states": ["anomaly_score", "degradation_level", "rul_estimate",
                    "rul_confidence", "fault_probs_json"],
    "fault_predictions": ["fault_type", "probability", "severity"],
}

# WebSocket broadcast hooks (registered by backend/api/ws or simulator_server)
_ws_hooks: List = []
_ws_lock = threading.Lock()


def add_ws_broadcast_hook(fn) -> None:
    """Register fn(payload_dict) called on every twin state update (throttle in WS layer)."""
    with _ws_lock:
        _ws_hooks.append(fn)


def _broadcast(payload: Dict[str, Any]) -> None:
    with _ws_lock:
        hooks = list(_ws_hooks)
    for fn in hooks:
        try:
            fn(payload)
        except Exception as exc:
            logger.warning("WS broadcast hook failed: %s", exc)


def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        for stmt in _SCHEMA:
            conn.execute(stmt)
    logger.info("Database ready at %s", DB_PATH)


def _existing_columns(conn: sqlite3.Connection, table: str) -> set:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def _schema_warnings(conn: sqlite3.Connection) -> Dict[str, set]:
    """Report missing columns once (Task 4.4 Part B: 'missing fields in database')."""
    missing = {}
    for table, cols in _REQUIRED_COLUMNS.items():
        have = _existing_columns(conn, table)
        miss = {c for c in cols if have and c not in have}
        if miss:
            logger.warning("Table %s is missing columns %s -- predictions will be "
                           "returned in memory but not persisted for those fields", table, sorted(miss))
            missing[table] = miss
    return missing


def _insert(conn: sqlite3.Connection, table: str, values: Dict[str, Any],
            skip_missing: bool = True) -> None:
    cols = _existing_columns(conn, table)
    if skip_missing:
        values = {k: v for k, v in values.items() if k in cols}
    if not values:
        return
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(values.values()))


def _severity(prob: float) -> str:
    return "critical" if prob > 0.8 else ("warning" if prob > 0.5 else "info")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def update_twin_state(mission_id, telemetry_row, engine_id: Optional[str] = None):
    """Compute a simple twin state update and broadcast it to connected clients."""
    if not isinstance(telemetry_row, dict):
        logger.warning("update_twin_state rejected: telemetry row must be a dict")
        return None

    if engine_id is None:
        engine_id = telemetry_row.get("engine_id")
    if mission_id is None or engine_id is None:
        logger.warning("update_twin_state rejected: missing mission_id or engine_id")
        return None

    sensor_keys = ["rpm", "cht", "egt", "oil_pressure", "oil_temperature", "fuel_flow", "vibration_rms"]
    observed = {}
    for key in sensor_keys:
        value = telemetry_row.get(key)
        try:
            observed[key] = float(value)
        except (TypeError, ValueError):
            observed[key] = 0.0

    expected = {
        "rpm": observed["rpm"] * 0.98,
        "cht": observed["cht"] * 0.95 + 4.0,
        "egt": observed["egt"] * 0.96 + 10.0,
        "oil_pressure": observed["oil_pressure"] * 0.99,
        "oil_temperature": observed["oil_temperature"] * 0.98 + 1.5,
        "fuel_flow": observed["fuel_flow"] * 0.97 + 0.4,
        "vibration_rms": max(0.0, observed["vibration_rms"] * 0.92),
    }
    residuals = {key: round(observed[key] - expected[key], 3) for key in sensor_keys if key in expected}

    health_index = max(70.0, min(100.0, 100.0 - abs(residuals.get("cht", 0.0)) * 0.15 - abs(residuals.get("egt", 0.0)) * 0.08 - abs(residuals.get("vibration_rms", 0.0)) * 1.5 + random.uniform(0.5, 2.0)))
    anomaly_score = min(1.0, max(0.0, sum(abs(v) for v in residuals.values()) / 500.0))
    fault_probs = {
        "injector_degradation": round(min(1.0, max(0.0, anomaly_score * 0.7 + 0.1)), 4),
        "temperature_rise": round(min(1.0, max(0.0, abs(residuals.get("egt", 0.0)) / 60.0)), 4),
        "vibration_issue": round(min(1.0, max(0.0, abs(residuals.get("vibration_rms", 0.0)) / 12.0)), 4),
    }

    twin_state = {
        "mission_id": mission_id,
        "engine_id": engine_id,
        "timestamp": _now_iso(),
        "health_index": round(health_index, 2),
        "anomaly_score": round(anomaly_score, 4),
        "sensors": {**observed},
        "fault_probs": fault_probs,
        "expected_sensors": expected,
        "residuals": residuals,
        "rul_estimate": round(120.0 - (anomaly_score * 70.0), 2),
        "rul_confidence": "medium",
    }

    try:
        from backend.db.database import SessionLocal
        from backend.db.models import TwinState

        db = SessionLocal()
        state_record = TwinState(
            mission_id=int(mission_id),
            timestamp=datetime.utcnow(),
            expected_sensors_json=expected,
            residuals_json=residuals,
            health_index=twin_state["health_index"],
            anomaly_score=twin_state["anomaly_score"],
            fault_probs_json=fault_probs,
            rul_estimate=twin_state["rul_estimate"],
            rul_confidence=twin_state["rul_confidence"],
        )
        db.add(state_record)
        db.commit()
        db.refresh(state_record)
        twin_state["id"] = state_record.id
    except Exception as exc:
        logger.warning("Could not persist twin_state for mission %s: %s", mission_id, exc)

    try:
        from backend.services.twin_update_service import broadcast_twin_state
        broadcast_twin_state(engine_id, twin_state)
    except Exception as exc:
        logger.warning("Twin broadcast failed for engine %s: %s", engine_id, exc)

    return twin_state


class DigitalTwinService:
    """Manages twin lifecycle, telemetry ingest and ML-driven state updates."""

    def __init__(self):
        init_db()
        self.last_states: Dict[str, Dict[str, Any]] = {}  # mission_id -> last twin state
        logger.info("DigitalTwinService initialized.")

    # ------------------------------------------------------------- ingest
    def ingest_telemetry_row(self, engine_id: str, mission_id: str,
                             row: Dict[str, Any]) -> bool:
        """Validate + persist one telemetry row. Returns False for invalid rows."""
        required = ["timestamp"] + SENSORS[:4]
        missing = [f for f in required if row.get(f) is None]
        if missing:
            logger.warning("Rejected telemetry row (missing %s) for engine %s", missing, engine_id)
            return False
        with get_db() as conn:
            _insert(conn, "telemetry", {
                "engine_id": engine_id, "mission_id": mission_id,
                "timestamp": str(row["timestamp"]),
                **{s: float(row[s]) for s in SENSORS if row.get(s) is not None},
                "fault_label": row.get("fault_label", "none"),
            })
        return True

    def ingest_telemetry(self, engine_id: str, data_points: List[Dict[str, Any]]) -> bool:
        if not data_points:
            logger.warning("No data points provided for engine %s.", engine_id)
            return False
        ok = all(self.ingest_telemetry_row(engine_id, "unassigned", dp) for dp in data_points)
        logger.info("Processed %d telemetry points for %s.", len(data_points), engine_id)
        return ok

    # --------------------------------------------------------- twin update
    def update_twin_state(self, mission_id: str, telemetry_window,
                          engine_id: str = "ENG-001") -> Dict[str, Any]:
        """
        ML-integrated twin update. Accepts a window (list of telemetry dicts)
        or a single row dict. Never raises: ML/DB failures degrade to defaults.
        """
        window = [telemetry_window] if isinstance(telemetry_window, dict) else list(telemetry_window)
        if not window:
            logger.warning("update_twin_state: empty window for mission %s", mission_id)
            return {}

        try:
            features = extract_features(window)
        except Exception as exc:
            logger.error("Feature extraction failed for mission %s: %s", mission_id, exc)
            return {}

        predictions = predict_all(features)  # never raises; safe defaults if models missing
        degradation = float(predictions["degradation_level"])
        anomaly = float(predictions["anomaly_score"])

        # Simple interpretable Health Index from ML outputs (0-100)
        health_index = round(max(0.0, 100.0 * (1.0 - 0.7 * degradation - 0.3 * anomaly)), 1)

        # Physics-lite expected values (window means) and residuals of last row
        expected = {s: float(sum(w.get(s, 0.0) or 0.0 for w in window) / len(window))
                    for s in SENSORS}
        residuals = {s: round(float(window[-1].get(s, 0.0) or 0.0) - expected[s], 3)
                     for s in SENSORS}

        state = {
            "event": "twin_state_update",
            "engine_id": engine_id,
            "mission_id": mission_id,
            "timestamp": _now_iso(),
            "health_index": health_index,
            "anomaly_score": anomaly,
            "fault_probs": predictions["fault_probs"],
            "degradation": degradation,
            "rul_estimate": predictions["rul_estimate"],
            "rul_confidence": predictions["rul_confidence"],
            "expected_sensors": {k: round(v, 2) for k, v in expected.items()},
            "residuals": residuals,
        }
        self.last_states[mission_id] = state

        # --- persist (twin_states + fault_predictions) ---
        try:
            with get_db() as conn:
                _schema_warnings(conn)
                _insert(conn, "twin_states", {
                    "mission_id": mission_id, "engine_id": engine_id,
                    "timestamp": state["timestamp"],
                    "expected_sensors_json": json.dumps(state["expected_sensors"]),
                    "residuals_json": json.dumps(residuals),
                    "health_index": health_index,
                    "anomaly_score": anomaly,
                    "degradation_level": degradation,
                    "rul_estimate": predictions["rul_estimate"],
                    "rul_confidence": predictions["rul_confidence"],
                    "fault_probs_json": json.dumps(predictions["fault_probs"]),
                })
                top_type = max(predictions["fault_probs"], key=predictions["fault_probs"].get)
                for ftype, prob in predictions["fault_probs"].items():
                    if prob >= 0.05 or ftype == top_type:  # keep signal, skip noise
                        _insert(conn, "fault_predictions", {
                            "mission_id": mission_id, "engine_id": engine_id,
                            "timestamp": state["timestamp"],
                            "fault_type": ftype, "probability": float(prob),
                            "severity": _severity(prob),
                        })
        except Exception as exc:
            logger.error("DB persist failed for mission %s (non-fatal): %s", mission_id, exc)

        _broadcast(state)  # WS layer (Task 2.4) forwards to clients
        return state

    # ------------------------------------------------------------ lookups
    def get_engine_state(self, engine_id: str) -> Dict[str, Any]:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM twin_states WHERE engine_id = ? ORDER BY id DESC LIMIT 1",
                (engine_id,)).fetchone()
        if row is None:
            return {"engine_id": engine_id, "last_updated": _now_iso(),
                    "operational_status": "NO_DATA", "key_parameters": {}}
        return {"engine_id": engine_id, "last_updated": row["timestamp"],
                "operational_status": "Running",
                "health_index": row["health_index"],
                "anomaly_score": row["anomaly_score"],
                "degradation": row["degradation_level"],
                "rul_estimate": row["rul_estimate"],
                "rul_confidence": row["rul_confidence"],
                "fault_probs": json.loads(row["fault_probs_json"] or "{}")}

    def get_historical_telemetry(self, engine_id: str, start_time, end_time) -> List[Dict[str, Any]]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM telemetry WHERE engine_id = ? AND timestamp BETWEEN ? AND ? "
                "ORDER BY timestamp", (engine_id, str(start_time), str(end_time))).fetchall()
        return [dict(r) for r in rows]

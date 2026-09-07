from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from backend.db.database import SessionLocal
    from backend.db.models import Telemetry
except ImportError:  # pragma: no cover
    from db.database import SessionLocal
    from db.models import Telemetry

logger = logging.getLogger("telemetry_ingest")

REQUIRED_FIELDS = [
    "timestamp",
    "engine_id",
    "mission_id",
    "rpm",
    "cht",
    "egt",
    "oil_pressure",
    "oil_temperature",
    "fuel_flow",
    "vibration_rms",
    "battery_voltage",
    "alternator_current",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value))
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.fromtimestamp(float(value))
            except (TypeError, ValueError, OverflowError, OSError):
                return None
    return None


def ingest_telemetry_row(row_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(row_dict, dict):
        logger.error("Telemetry ingest rejected: payload is not a dict.")
        return None

    timestamp = _parse_timestamp(row_dict.get("timestamp"))
    engine_id = row_dict.get("engine_id")
    mission_id = row_dict.get("mission_id")

    missing = [name for name in ["timestamp", "engine_id", "mission_id"] if row_dict.get(name) is None]
    if missing:
        logger.error("Telemetry ingest rejected for missing required fields: %s", missing)
        return None

    sensor_missing = [
        name for name in REQUIRED_FIELDS[3:]
        if row_dict.get(name) is None or not math.isfinite(_safe_float(row_dict.get(name), float("nan")))
    ]
    if sensor_missing:
        logger.error("Telemetry ingest rejected for invalid sensor values: %s", sensor_missing)
        return None

    if timestamp is None:
        logger.error("Telemetry ingest rejected: invalid timestamp %r", row_dict.get("timestamp"))
        return None

    engine_id = str(engine_id)
    mission_id = str(mission_id)

    db = SessionLocal()
    try:
        record = Telemetry(
            mission_id=mission_id,
            engine_id=engine_id,
            timestamp=timestamp,
            rpm=_safe_float(row_dict.get("rpm")),
            cht=_safe_float(row_dict.get("cht")),
            egt=_safe_float(row_dict.get("egt")),
            oil_pressure=_safe_float(row_dict.get("oil_pressure")),
            oil_temperature=_safe_float(row_dict.get("oil_temperature")),
            fuel_flow=_safe_float(row_dict.get("fuel_flow")),
            vibration_rms=_safe_float(row_dict.get("vibration_rms")),
            battery_voltage=_safe_float(row_dict.get("battery_voltage")),
            alternator_current=_safe_float(row_dict.get("alternator_current")),
            injection_timing=_safe_float(row_dict.get("injection_timing", 0.0)),
            altitude=_safe_float(row_dict.get("altitude", 0.0)),
            ambient_temperature=_safe_float(row_dict.get("ambient_temperature", 0.0)),
            fault_label=row_dict.get("fault_label", "none"),
            fault_severity=_safe_float(row_dict.get("fault_severity", 0.0)),
            degradation_level=_safe_float(row_dict.get("degradation_level", 0.0)),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info("Inserted telemetry row id=%s for mission=%s", record.id, mission_id)
        return {
            "id": record.id,
            "engine_id": record.engine_id,
            "mission_id": record.mission_id,
            "timestamp": record.timestamp.isoformat(),
            "rpm": record.rpm,
            "cht": record.cht,
            "egt": record.egt,
        }
    except Exception as exc:
        db.rollback()
        logger.exception("Telemetry row insert failed: %s", exc)
        return None
    finally:
        db.close()

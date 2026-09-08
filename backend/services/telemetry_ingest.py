"""Telemetry ingestion service.

Validates incoming rows, rejects malformed ones with a log line, and stores
valid rows in the telemetry table.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session

from backend.models import Telemetry

logger = logging.getLogger("sih26054.ingest")

# Sensors that must be present and finite on every accepted row.
REQUIRED_SENSORS = [
    "rpm",
    "cht",
    "egt",
    "oil_pressure",
    "oil_temperature",
    "fuel_flow",
    "vibration_rms",
]

ALL_SENSORS = REQUIRED_SENSORS + [
    "battery_voltage",
    "alternator_current",
    "injection_timing",
    "altitude",
    "ambient_temperature",
]

EXPECTED_SENSORS = [
    "expected_cht",
    "expected_egt",
    "expected_oil_pressure",
    "expected_oil_temperature",
    "expected_fuel_flow",
    "expected_vibration_rms",
]


def normalize_timestamp(value) -> str:
    """Accept ISO strings or Unix epoch floats; default to now (UTC ISO)."""
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat(timespec="milliseconds")
    text = str(value).strip()
    if not text:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    if "T" not in text:
        try:
            return datetime.fromtimestamp(float(text), tz=timezone.utc).isoformat(timespec="milliseconds")
        except ValueError:
            pass
    return text


def _is_valid_sensor(value) -> bool:
    if value is None:
        return False
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f)


def ingest_telemetry_row(db: Session, row: Dict) -> Optional[int]:
    """Validate + insert one telemetry row. Returns the row id or None if rejected."""
    mission_id = str(row.get("mission_id") or "").strip()
    if not mission_id:
        logger.error("Rejected telemetry row: missing mission_id")
        return None

    missing = [s for s in REQUIRED_SENSORS if not _is_valid_sensor(row.get(s))]
    if missing:
        logger.error("Rejected telemetry row for mission %s: missing/invalid sensors %s", mission_id, missing)
        return None

    ts = normalize_timestamp(row.get("timestamp"))
    telemetry = Telemetry(
        mission_id=mission_id,
        timestamp=ts,
        profile_id=str(row.get("profile_id") or ""),
        phase=str(row.get("phase") or ""),
        throttle=float(row.get("throttle") or 0.0),
        **{s: float(row.get(s) or 0.0) for s in ALL_SENSORS},
        **{s: float(row.get(s) or 0.0) for s in EXPECTED_SENSORS},
        fault_label=str(row.get("fault_label") or "none"),
        fault_severity=float(row.get("fault_severity") or 0.0),
        degradation_level=float(row.get("degradation_level") or 0.0),
    )
    db.add(telemetry)
    db.commit()
    db.refresh(telemetry)
    return telemetry.id
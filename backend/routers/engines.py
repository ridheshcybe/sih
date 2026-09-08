"""Engine read endpoints: state, telemetry, health, faults, RUL."""

from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Engine, FaultPrediction, Mission, Telemetry, TwinState
from backend.services.simulation_runner import runner

router = APIRouter(prefix="/api/v1/engines", tags=["engines"])


def _latest_mission(db: Session, engine_id: str) -> Optional[Mission]:
    return db.query(Mission).filter(Mission.engine_id == engine_id).order_by(Mission.start_time.desc()).first()


def _ensure_engine(db: Session, engine_id: str) -> Engine:
    engine = db.get(Engine, engine_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Unknown engine {engine_id}")
    return engine


@router.get("/{engine_id}/state")
def get_engine_state(engine_id: str, db: Session = Depends(get_db)) -> dict:
    _ensure_engine(db, engine_id)
    mission = _latest_mission(db, engine_id)
    if mission is None:
        return {"engine_id": engine_id, "mission": None, "running": False, "twin_state": None, "latest_telemetry": None}
    twin = db.query(TwinState).filter(TwinState.mission_id == mission.id).order_by(TwinState.id.desc()).first()
    telemetry = db.query(Telemetry).filter(Telemetry.mission_id == mission.id).order_by(Telemetry.id.desc()).first()
    return {
        "engine_id": engine_id,
        "mission": {
            "mission_id": mission.id,
            "profile_id": mission.profile_id,
            "status": mission.status,
        },
        "running": runner.is_running(engine_id),
        "twin_state": _twin_dict(twin) if twin else None,
        "latest_telemetry": _telemetry_dict(telemetry) if telemetry else None,
    }


@router.get("/{engine_id}/telemetry")
def get_engine_telemetry(
    engine_id: str,
    limit: int = Query(default=50, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_engine(db, engine_id)
    mission = _latest_mission(db, engine_id)
    if mission is None:
        return {"engine_id": engine_id, "mission_id": None, "rows": []}
    rows = db.query(Telemetry).filter(Telemetry.mission_id == mission.id).order_by(Telemetry.id.desc()).limit(limit).all()
    return {"engine_id": engine_id, "mission_id": mission.id, "rows": [_telemetry_dict(t) for t in reversed(rows)]}


@router.get("/{engine_id}/health")
def get_engine_health(engine_id: str, db: Session = Depends(get_db)) -> dict:
    _ensure_engine(db, engine_id)
    mission = _latest_mission(db, engine_id)
    if mission is None:
        return {"engine_id": engine_id, "health_index": None, "trend": []}
    rows = db.query(TwinState).filter(TwinState.mission_id == mission.id).order_by(TwinState.id.desc()).limit(120).all()
    trend = [{"timestamp": t.timestamp, "health_index": t.health_index} for t in reversed(rows)]
    return {"engine_id": engine_id, "health_index": trend[-1]["health_index"] if trend else None, "trend": trend}


@router.get("/{engine_id}/faults")
def get_engine_faults(engine_id: str, db: Session = Depends(get_db)) -> dict:
    _ensure_engine(db, engine_id)
    mission = _latest_mission(db, engine_id)
    if mission is None:
        return {"engine_id": engine_id, "faults": []}
    rows = (
        db.query(FaultPrediction)
        .filter(FaultPrediction.mission_id == mission.id)
        .order_by(FaultPrediction.id.desc())
        .limit(50)
        .all()
    )
    return {
        "engine_id": engine_id,
        "faults": [
            {"timestamp": f.timestamp, "fault_type": f.fault_type, "probability": f.probability, "severity": f.severity}
            for f in reversed(rows)
        ],
    }


@router.get("/{engine_id}/rul")
def get_engine_rul(engine_id: str, db: Session = Depends(get_db)) -> dict:
    _ensure_engine(db, engine_id)
    mission = _latest_mission(db, engine_id)
    if mission is None:
        return {"engine_id": engine_id, "rul_estimate": None, "rul_confidence": None, "degradation_level": 0.0}
    twin = db.query(TwinState).filter(TwinState.mission_id == mission.id).order_by(TwinState.id.desc()).first()
    return {
        "engine_id": engine_id,
        "rul_estimate": twin.rul_estimate if twin else None,
        "rul_confidence": twin.rul_confidence if twin else None,
        "degradation_level": twin.degradation_level if twin else 0.0,
    }


def _twin_dict(t: TwinState) -> dict:
    fault_probs = json.loads(t.fault_probs_json or "{}")
    top_fault = max(fault_probs, key=fault_probs.get) if fault_probs else "none"
    return {
        "mission_id": t.mission_id,
        "timestamp": t.timestamp,
        "status": t.status,
        "health_index": t.health_index,
        "anomaly_score": t.anomaly_score,
        "degradation_level": t.degradation_level,
        "rul_estimate": t.rul_estimate,
        "rul_confidence": t.rul_confidence,
        "top_fault": top_fault,
        "top_probability": round(float(fault_probs.get(top_fault, 0.0)), 4) if fault_probs else 0.0,
        "residuals": json.loads(t.residuals_json or "{}"),
        "fault_probs": fault_probs,
        "sensors": json.loads(t.latest_sensors_json or "{}"),
    }


def _telemetry_dict(t: Telemetry) -> dict:
    return {
        "timestamp": t.timestamp,
        "phase": t.phase,
        "throttle": t.throttle,
        "rpm": t.rpm,
        "cht": t.cht,
        "egt": t.egt,
        "oil_pressure": t.oil_pressure,
        "oil_temperature": t.oil_temperature,
        "fuel_flow": t.fuel_flow,
        "vibration_rms": t.vibration_rms,
        "battery_voltage": t.battery_voltage,
        "alternator_current": t.alternator_current,
        "injection_timing": t.injection_timing,
        "altitude": t.altitude,
        "ambient_temperature": t.ambient_temperature,
        "fault_label": t.fault_label,
        "degradation_level": t.degradation_level,
    }
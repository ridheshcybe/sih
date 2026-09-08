"""Mission management endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Engine, FaultPrediction, Mission, Telemetry, TwinState
from backend.schemas import MissionCreate
from backend.services.simulation_runner import runner
from simulator.mission_profiles import PROFILE_NAMES, get_profile

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])


def _mission_dict(m: Mission) -> dict:
    return {
        "mission_id": m.id,
        "engine_id": m.engine_id,
        "profile_id": m.profile_id,
        "mission_name": m.mission_name,
        "status": m.status,
        "start_time": m.start_time,
        "end_time": m.end_time,
        "duration_s": m.duration_s,
    }


@router.post("")
async def start_mission(payload: MissionCreate, db: Session = Depends(get_db)) -> dict:
    if db.get(Engine, payload.engine_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown engine {payload.engine_id}")
    try:
        get_profile(payload.profile_id)
    except KeyError:
        raise HTTPException(status_code=422, detail=f"Unknown profile '{payload.profile_id}'. "
                                                    f"Available: {PROFILE_NAMES}")
    if runner.is_running(payload.engine_id):
        raise HTTPException(status_code=409, detail=f"A mission is already running on engine {payload.engine_id}")
    mission = Mission(
        id=f"M-{uuid.uuid4().hex[:8].upper()}",
        engine_id=payload.engine_id,
        profile_id=payload.profile_id,
        mission_name=payload.mission_name,
        start_time=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        status="running",
        duration_s=payload.duration_s,
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    started = await runner.start_mission(mission)
    if not started:
        raise HTTPException(status_code=409, detail="Could not start simulation runner")
    return {"mission_id": mission.id, "status": "STARTED", "engine_id": mission.engine_id, "profile_id": mission.profile_id}


@router.post("/{mission_id}/stop")
async def stop_mission(mission_id: str, db: Session = Depends(get_db)) -> dict:
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Unknown mission {mission_id}")
    await runner.stop_mission(mission.engine_id)
    db.expire_all()
    mission = db.get(Mission, mission_id)
    return {"mission_id": mission_id, "status": mission.status if mission else "stopped"}


@router.get("/list")
def list_missions(db: Session = Depends(get_db)) -> List[dict]:
    rows = db.query(Mission).order_by(Mission.start_time.desc()).limit(50).all()
    return [_mission_dict(m) for m in rows]


@router.get("/{mission_id}")
def get_mission(mission_id: str, db: Session = Depends(get_db)) -> dict:
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Unknown mission {mission_id}")
    telemetry_count = db.query(func.count(Telemetry.id)).filter(Telemetry.mission_id == mission_id).scalar() or 0
    twin_count = db.query(func.count(TwinState.id)).filter(TwinState.mission_id == mission_id).scalar() or 0
    fault_count = db.query(func.count(FaultPrediction.id)).filter(FaultPrediction.mission_id == mission_id).scalar() or 0
    latest_twin = db.query(TwinState).filter(TwinState.mission_id == mission_id).order_by(TwinState.id.desc()).first()
    info = _mission_dict(mission)
    info.update({
        "telemetry_count": telemetry_count,
        "twin_state_count": twin_count,
        "fault_prediction_count": fault_count,
        "latest_health_index": latest_twin.health_index if latest_twin else None,
    })
    return info
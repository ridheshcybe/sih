"""Simulation control endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Engine, Mission
from backend.schemas import EngineStopIn, SimulationStartIn
from backend.services.simulation_runner import runner
from simulator.mission_profiles import PROFILE_NAMES, get_profile

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


@router.post("/start")
async def start_simulation(payload: SimulationStartIn, db: Session = Depends(get_db)) -> dict:
    if db.get(Engine, payload.engine_id) is None:
        raise HTTPException(status_code=404, detail=f"Unknown engine {payload.engine_id}")
    try:
        get_profile(payload.profile_id)
    except KeyError:
        raise HTTPException(status_code=422, detail=f"Unknown profile '{payload.profile_id}'. "
                                                    f"Available: {PROFILE_NAMES}")
    if runner.is_running(payload.engine_id):
        raise HTTPException(status_code=409, detail=f"Simulation already running on engine {payload.engine_id}")
    mission = Mission(
        id=f"M-{uuid.uuid4().hex[:8].upper()}",
        engine_id=payload.engine_id,
        profile_id=payload.profile_id,
        mission_name=f"Simulation {payload.profile_id}",
        start_time=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        status="running",
        duration_s=payload.duration_s,
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    ok = await runner.start_mission(mission)
    if not ok:
        raise HTTPException(status_code=409, detail="Could not start simulation runner")
    return {"mission_id": mission.id, "message": f"Simulation started for {payload.engine_id}", "is_running": True}


@router.post("/stop")
async def stop_simulation(payload: EngineStopIn, db: Session = Depends(get_db)) -> dict:
    stopped = await runner.stop_mission(payload.engine_id)
    return {"engine_id": payload.engine_id, "is_running": runner.is_running(payload.engine_id), "stopped": stopped}


@router.get("/status")
def simulation_status() -> dict:
    engines = {}
    for engine_id in runner.running_engines():
        engines[engine_id] = {
            "running": runner.is_running(engine_id),
            "mission_id": runner.active_mission_id(engine_id),
            "elapsed_sec": round(runner.elapsed(engine_id), 1),
        }
    return {"simulation": engines, "replay": {
        "replaying": runner.is_replaying(),
        "mission_id": runner.replay_mission_id(),
    }}
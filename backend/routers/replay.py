"""Mission replay endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Mission
from backend.schemas import ReplayStartIn
from backend.services.simulation_runner import runner

router = APIRouter(prefix="/api/v1/replay", tags=["replay"])


@router.post("/start")
async def start_replay(payload: ReplayStartIn, db: Session = Depends(get_db)) -> dict:
    mission = db.get(Mission, payload.mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Unknown mission {payload.mission_id}")
    if runner.is_replaying():
        raise HTTPException(status_code=409, detail="A replay is already in progress")
    ok = await runner.start_replay(payload.mission_id, speed=payload.speed)
    if not ok:
        raise HTTPException(status_code=409, detail="Could not start replay")
    return {"mission_id": payload.mission_id, "speed": payload.speed, "replaying": True}


@router.post("/stop")
async def stop_replay() -> dict:
    await runner.stop_replay()
    return {"replaying": False}


@router.get("/status")
def replay_status() -> dict:
    return {"replaying": runner.is_replaying(), "mission_id": runner.replay_mission_id()}
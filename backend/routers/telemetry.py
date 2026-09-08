"""Telemetry ingest endpoint used by the standalone simulator (--stream)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Mission
from backend.schemas import TelemetryIn
from backend.services import digital_twin, telemetry_ingest
from backend.services.simulation_runner import runner
from backend.services.ws_manager import manager

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


@router.post("/ingest")
async def ingest_telemetry(payload: TelemetryIn, db: Session = Depends(get_db)) -> dict:
    mission = db.get(Mission, payload.mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Unknown mission {payload.mission_id}")

    row = payload.model_dump()
    telemetry_id = telemetry_ingest.ingest_telemetry_row(db, row)
    if telemetry_id is None:
        raise HTTPException(status_code=422, detail="Telemetry row rejected: missing required sensors")

    twin = digital_twin.update_twin_state(db, mission, row)
    await manager.broadcast(mission.engine_id, {"event": "telemetry_update", "payload": row})
    await manager.broadcast(mission.engine_id, {"event": "twin_state_update", "payload": twin})
    return {"accepted": True, "telemetry_id": telemetry_id, "mission_id": payload.mission_id,
            "health_index": twin["health_index"]}
"""System endpoints: health and info."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.config import APP_NAME, APP_VERSION, DEFAULT_ENGINE_ID
from backend.database import get_db
from backend.services.ml_inference import get_ml_predictor
from backend.services.simulation_runner import runner

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
def system_health() -> dict:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds")}


@router.get("/info")
def system_info(db: Session = Depends(get_db)) -> dict:
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "engine_id": DEFAULT_ENGINE_ID,
        "models": get_ml_predictor().status,
        "simulation_running": runner.is_running(DEFAULT_ENGINE_ID),
        "replay_running": runner.is_replaying(),
    }
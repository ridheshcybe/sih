"""Mission report endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Mission
from backend.services.reports import generate_report, get_report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/{mission_id}")
def fetch_report(mission_id: str, db: Session = Depends(get_db)) -> dict:
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Unknown mission {mission_id}")
    return get_report(db, mission_id)


@router.post("/{mission_id}/generate")
def regenerate_report(mission_id: str, db: Session = Depends(get_db)) -> dict:
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Unknown mission {mission_id}")
    return generate_report(db, mission_id)
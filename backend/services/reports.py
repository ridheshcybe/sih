"""Mission report generation.

Builds a JSON summary for a mission from the stored telemetry, twin states,
fault predictions, and advisories; persists it in mission_reports.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import (
    FaultPrediction,
    MaintenanceAdvisory,
    Mission,
    MissionReport,
    Telemetry,
    TwinState,
)

logger = logging.getLogger("sih26054.reports")


def generate_report(db: Session, mission_id: str) -> Dict:
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise ValueError(f"Unknown mission {mission_id}")

    telemetry_count = db.query(func.count(Telemetry.id)).filter(Telemetry.mission_id == mission_id).scalar() or 0

    twin_rows = db.query(TwinState).filter(TwinState.mission_id == mission_id).order_by(TwinState.id).all()
    health_values = [t.health_index for t in twin_rows]
    avg_health = round(sum(health_values) / len(health_values), 1) if health_values else None
    min_health = round(min(health_values), 1) if health_values else None

    fault_counts: Dict[str, int] = {}
    for fp in db.query(FaultPrediction).filter(FaultPrediction.mission_id == mission_id).all():
        fault_counts[fp.fault_type] = fault_counts.get(fp.fault_type, 0) + 1

    advisories = [
        {"text": a.advisory_text, "priority": a.priority, "timestamp": a.timestamp}
        for a in db.query(MaintenanceAdvisory)
        .filter(MaintenanceAdvisory.mission_id == mission_id)
        .order_by(MaintenanceAdvisory.id)
        .all()
    ]

    latest = twin_rows[-1] if twin_rows else None
    duration_sec = None
    if mission.end_time:
        try:
            start = datetime.fromisoformat(mission.start_time)
            end = datetime.fromisoformat(mission.end_time)
            duration_sec = round((end - start).total_seconds(), 1)
        except ValueError:
            duration_sec = None

    summary = {
        "mission_id": mission_id,
        "engine_id": mission.engine_id,
        "profile_id": mission.profile_id,
        "mission_name": mission.mission_name,
        "status": mission.status,
        "start_time": mission.start_time,
        "end_time": mission.end_time,
        "duration_sec": duration_sec,
        "telemetry_rows": telemetry_count,
        "health_index": {
            "average": avg_health,
            "minimum": min_health,
            "final": latest.health_index if latest else None,
        },
        "fault_predictions": fault_counts,
        "rul_estimate_final": latest.rul_estimate if latest else None,
        "degradation_final": latest.degradation_level if latest else None,
        "advisories": advisories,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    report = db.query(MissionReport).filter(MissionReport.mission_id == mission_id).first()
    if report is None:
        report = MissionReport(mission_id=mission_id, summary_json="{}")
        db.add(report)
    report.summary_json = json.dumps(summary, indent=2)
    db.commit()
    return summary


def get_report(db: Session, mission_id: str) -> Dict:
    report = db.query(MissionReport).filter(MissionReport.mission_id == mission_id).first()
    if report is not None and report.summary_json:
        return json.loads(report.summary_json)
    return generate_report(db, mission_id)
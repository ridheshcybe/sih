from __future__ import annotations

import logging
from typing import Any, Dict, List, Union

from fastapi import APIRouter, HTTPException

try:
    from backend.services.digital_twin import update_twin_state
    from backend.services.telemetry_ingest import ingest_telemetry_row
except ImportError:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from services.digital_twin import update_twin_state
    from services.telemetry_ingest import ingest_telemetry_row

logger = logging.getLogger("api.telemetry")
router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.post("/ingest")
async def ingest_telemetry(payload: Union[Dict[str, Any], List[Dict[str, Any]]]):
    """Accept a single row or a batch of rows and persist them."""
    if isinstance(payload, list):
        if not payload:
            return {"status": "error", "inserted": 0, "message": "Empty batch received."}

        inserted = []
        for row in payload:
            result = ingest_telemetry_row(row)
            if result is None:
                logger.warning("Rejected telemetry row in batch: %s", row)
                continue
            inserted.append(result)
            mission_id = result.get("mission_id")
            if mission_id is not None:
                update_twin_state(mission_id, row)

        return {
            "status": "ok" if inserted else "error",
            "inserted": len(inserted),
            "rows": inserted,
        }

    result = ingest_telemetry_row(payload)
    if result is None:
        raise HTTPException(status_code=400, detail="Telemetry row rejected: missing or invalid required values.")

    mission_id = result.get("mission_id")
    if mission_id is not None:
        update_twin_state(mission_id, payload)

    return {"status": "ok", "inserted": 1, "row": result}

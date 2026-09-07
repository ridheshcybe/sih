from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
async def get_system_health():
    """Return basic health information for the service."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


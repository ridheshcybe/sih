"""Legacy compatibility routes.

The canonical API is registered from routes_system, routes_telemetry, and
routes_control in backend.main.
"""

from fastapi import APIRouter

router = APIRouter(tags=["legacy"])


@router.get("/health/status")
async def get_system_status():
    return {"status": "Operational", "service": "Digital Twin"}

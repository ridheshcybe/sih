from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.websocket.server import connection_manager

router = APIRouter(prefix="/api", tags=["demo-control"])

_missions: Dict[str, Dict[str, Any]] = {}
_engine_state: Dict[str, Dict[str, Any]] = {}
_tasks: Dict[str, asyncio.Task] = {}


class StartMissionRequest(BaseModel):
    engine_id: str = "ENG-001"
    profile_id: str = "normal_cruise"


class StopMissionRequest(BaseModel):
    mission_id: str


class FaultRequest(BaseModel):
    engine_id: str = "ENG-001"
    fault_type: str
    severity: float = Field(ge=0, le=1)
    start_time: Optional[str] = None


def _initial_state(engine_id: str) -> Dict[str, Any]:
    return {
        "engine_id": engine_id,
        "status": "OPERATIONAL",
        "health_index": 96.0,
        "anomaly_score": 0.04,
        "sensors": {"rpm": 2450.0, "cht": 168.0, "egt": 610.0, "oil_pressure": 46.0, "oil_temperature": 92.0, "fuel_flow": 17.5, "vibration_rms": 1.4, "altitude": 1200.0},
        "fault_probs": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _state_for(engine_id: str) -> Dict[str, Any]:
    return _engine_state.setdefault(engine_id, _initial_state(engine_id))


async def _publish(engine_id: str, event: str, payload: Dict[str, Any]) -> None:
    message = {"event": event, "payload": payload}
    for websocket in list(connection_manager.connections.get(str(engine_id), set())):
        try:
            await websocket.send_json(message)
        except Exception:
            connection_manager.disconnect(websocket, engine_id)


async def _mission_loop(mission_id: str, engine_id: str) -> None:
    step = 0
    while _missions.get(mission_id, {}).get("status") == "running":
        step += 1
        state = _state_for(engine_id)
        fault = state.get("active_fault")
        severity = float(fault.get("severity", 0)) if fault else 0.0
        fault_type = fault.get("fault_type") if fault else None
        sensors = state["sensors"]
        egt = 610 + math.sin(step / 6) * 8
        vibration = 1.4 + random.uniform(-0.08, 0.08)
        oil_pressure = 46 + random.uniform(-0.8, 0.8)
        if fault_type in {"overheating", "injector_degradation"}:
            egt += 180 * severity
        if fault_type in {"abnormal_vibration", "sensor_drift"}:
            vibration += 4 * severity
        if fault_type == "lubrication_issue":
            oil_pressure -= 28 * severity
        sensors.update({
            "rpm": round(2450 + math.sin(step / 9) * 45, 2), "cht": round(168 + (egt - 610) * 0.18, 2), "egt": round(egt, 2),
            "oil_pressure": round(max(4, oil_pressure), 2), "oil_temperature": round(92 + max(0, egt - 610) * 0.04, 2),
            "fuel_flow": round(17.5 + math.sin(step / 7) * 0.5, 2), "vibration_rms": round(max(0.1, vibration), 2),
            "altitude": round(1200 + math.sin(step / 12) * 300, 2),
        })
        anomaly = min(1, max(0.02, severity * 0.75 + abs(sensors["egt"] - 610) / 700))
        health = max(20, min(100, 98 - anomaly * 34))
        status = "CRITICAL" if health < 55 else "WARNING" if health < 80 else "OPERATIONAL"
        state.update({"health_index": round(health, 1), "anomaly_score": round(anomaly, 3), "status": status, "timestamp": datetime.now(timezone.utc).isoformat()})
        row = {"engine_id": engine_id, "mission_id": mission_id, "timestamp": state["timestamp"], **sensors}
        _missions[mission_id].setdefault("telemetry", []).append(row)
        _missions[mission_id]["telemetry"] = _missions[mission_id]["telemetry"][-120:]
        await _publish(engine_id, "telemetry_update", row)
        await _publish(engine_id, "twin_state_update", {k: state[k] for k in ("engine_id", "timestamp", "health_index", "anomaly_score", "sensors", "status", "fault_probs")})
        await asyncio.sleep(1)


@router.get("/engines/{engine_id}/state")
async def get_engine_state(engine_id: str):
    return _state_for(engine_id)


@router.get("/engines/{engine_id}/telemetry")
async def get_engine_telemetry(engine_id: str):
    mission = next((item for item in _missions.values() if item["engine_id"] == engine_id and item["status"] == "running"), None)
    return {"engine_id": engine_id, "data": mission.get("telemetry", []) if mission else []}


@router.post("/missions/start")
async def start_mission(request: StartMissionRequest):
    existing = next((item for item in _missions.values() if item["engine_id"] == request.engine_id and item["status"] == "running"), None)
    if existing:
        return existing
    mission_id = str(uuid4())
    mission = {"mission_id": mission_id, "engine_id": request.engine_id, "profile_id": request.profile_id, "status": "running", "telemetry": []}
    _missions[mission_id] = mission
    _state_for(request.engine_id)
    _tasks[mission_id] = asyncio.create_task(_mission_loop(mission_id, request.engine_id))
    return mission


@router.post("/missions/stop")
async def stop_mission(request: StopMissionRequest):
    mission = _missions.get(request.mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    mission["status"] = "stopped"
    task = _tasks.pop(request.mission_id, None)
    if task:
        task.cancel()
    return mission


@router.post("/faults/inject")
async def inject_fault(request: FaultRequest):
    state = _state_for(request.engine_id)
    state["active_fault"] = {"fault_type": request.fault_type, "severity": request.severity, "start_time": request.start_time}
    state["fault_probs"] = {request.fault_type: request.severity}
    return {"status": "injected", "engine_id": request.engine_id, **state["active_fault"]}
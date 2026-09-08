"""Simulation runner.

Runs the in-process engine simulator as an asyncio task, feeding every row
through ingest -> digital twin -> WebSocket broadcast. Also supports replaying
a stored mission over WebSockets at an accelerated rate.

Faults injected via the REST API are registered here with mission-relative
start times.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from backend.config import SIM_DT
from backend.database import SessionLocal
from backend.models import Mission, Telemetry
from backend.services import digital_twin, telemetry_ingest
from backend.services.ws_manager import manager
from simulator.engine_model import EngineModel
from simulator.fault_injection import InjectedFault, apply_faults, degradation_level, dominant_fault
from simulator.mission_profiles import get_profile, phase_at

logger = logging.getLogger("sih26054.sim")

_TELEMETRY_COLUMNS = [
    "mission_id", "timestamp", "profile_id", "phase", "throttle",
    "rpm", "cht", "egt", "oil_pressure", "oil_temperature", "fuel_flow",
    "vibration_rms", "battery_voltage", "alternator_current", "injection_timing",
    "altitude", "ambient_temperature",
    "expected_cht", "expected_egt", "expected_oil_pressure",
    "expected_oil_temperature", "expected_fuel_flow", "expected_vibration_rms",
    "fault_label", "fault_severity", "degradation_level",
]


def telemetry_row_to_dict(t: Telemetry) -> dict:
    return {col: getattr(t, col) for col in _TELEMETRY_COLUMNS}


class SimulationRunner:
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._stop: Dict[str, bool] = {}
        self._faults: Dict[str, List[InjectedFault]] = {}
        self._elapsed: Dict[str, float] = {}
        self._missions: Dict[str, str] = {}
        self._replay_task: Optional[asyncio.Task] = None
        self._replay_mission: Optional[str] = None

    # --- live mission -------------------------------------------------------
    def is_running(self, engine_id: str) -> bool:
        task = self._tasks.get(engine_id)
        return task is not None and not task.done()

    def elapsed(self, engine_id: str) -> float:
        return self._elapsed.get(engine_id, 0.0)

    def active_mission_id(self, engine_id: str) -> Optional[str]:
        return self._missions.get(engine_id)

    def running_engines(self) -> List[str]:
        return [eid for eid in self._missions if self.is_running(eid)]

    async def start_mission(self, mission: Mission) -> bool:
        if self.is_running(mission.engine_id):
            return False
        self._stop[mission.engine_id] = False
        self._faults[mission.engine_id] = []
        self._elapsed[mission.engine_id] = 0.0
        self._missions[mission.engine_id] = mission.id
        digital_twin.reset_buffers(mission.id)
        task = asyncio.create_task(self._run_loop(mission))
        self._tasks[mission.engine_id] = task
        return True

    async def stop_mission(self, engine_id: str) -> bool:
        if not self.is_running(engine_id):
            return False
        self._stop[engine_id] = True
        task = self._tasks[engine_id]
        try:
            await asyncio.wait_for(task, timeout=8.0)
        except asyncio.TimeoutError:
            task.cancel()
        return True

    async def _run_loop(self, mission: Mission) -> None:
        engine_id = mission.engine_id
        model = EngineModel(seed=int(np.random.default_rng().integers(0, 2**31)))
        rng = np.random.default_rng(42)
        profile = get_profile(mission.profile_id)
        total = mission.duration_s
        db = SessionLocal()
        try:
            elapsed = 0.0
            while not self._stop.get(engine_id, False) and (total is None or elapsed < total):
                phase, throttle, altitude, ambient = phase_at(profile, elapsed)
                healthy = model.step(throttle, altitude, ambient, dt=SIM_DT)
                faults = self._faults.get(engine_id, [])
                sensors = apply_faults(healthy, faults, elapsed, rng)
                deg = degradation_level(faults, elapsed)
                label = dominant_fault(faults, elapsed)
                severity = max((f.severity for f in faults), default=0.0) if faults else 0.0
                expected_fields = {f"expected_{s}": healthy[s] for s in
                                   ["cht", "egt", "oil_pressure", "oil_temperature",
                                    "fuel_flow", "vibration_rms"]}
                row = {
                    "mission_id": mission.id,
                    "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                    "profile_id": mission.profile_id,
                    "phase": phase,
                    "throttle": round(throttle, 1),
                    **sensors,
                    **expected_fields,
                    "altitude": round(float(altitude), 1),
                    "ambient_temperature": round(float(ambient), 1),
                    "fault_label": label,
                    "fault_severity": round(severity, 2),
                    "degradation_level": deg,
                }
                telemetry_ingest.ingest_telemetry_row(db, row)
                twin = digital_twin.update_twin_state(db, mission, row)

                await manager.broadcast(engine_id, {"event": "telemetry_update", "payload": row})
                await manager.broadcast(engine_id, {"event": "twin_state_update", "payload": twin})
                if twin["top_fault"] != "none":
                    await manager.broadcast(engine_id, {
                        "event": "fault_prediction",
                        "payload": {"fault_type": twin["top_fault"],
                                    "probability": twin["top_probability"],
                                    "timestamp": twin["timestamp"]},
                    })

                await asyncio.sleep(SIM_DT)
                elapsed += SIM_DT
                self._elapsed[engine_id] = elapsed
        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled for engine %s", engine_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Simulation loop failed for engine %s: %s", engine_id, exc)
            self._finalize_mission(mission.id, status="failed")
            await manager.broadcast(engine_id, {"event": "system_error",
                                                "payload": {"severity": "ERROR", "message": str(exc)}})
        finally:
            db.close()
            self._finalize_mission(mission.id)
            await manager.broadcast(engine_id, {"event": "simulation_status",
                                                "payload": {"running": False, "mission_id": mission.id}})

    def _finalize_mission(self, mission_id: str, status: str = "completed") -> None:
        db = SessionLocal()
        try:
            mission = db.get(Mission, mission_id)
            if mission and mission.status == "running":
                mission.status = status
                mission.end_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
                db.commit()
                if status == "completed":
                    from backend.services.reports import generate_report
                    generate_report(db, mission_id)
                logger.info("Mission %s %s", mission_id, status)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to finalize mission %s", mission_id)
        finally:
            db.close()

    # --- fault injection ------------------------------------------------------
    def inject_fault(self, engine_id: str, fault_type: str, severity: float,
                     duration_sec: float, pattern: str = "gradual",
                     start_offset_sec: Optional[float] = None) -> Optional[InjectedFault]:
        if not self.is_running(engine_id):
            return None
        start = start_offset_sec if start_offset_sec is not None else self._elapsed.get(engine_id, 0.0)
        fault = InjectedFault(fault_type, severity, start, duration_sec, pattern)
        self._faults.setdefault(engine_id, []).append(fault)
        logger.info("Injected fault %s (severity=%.2f) on %s at t=%.1fs", fault_type, severity, engine_id, start)
        return fault

    # --- replay ----------------------------------------------------------------
    def is_replaying(self) -> bool:
        return self._replay_task is not None and not self._replay_task.done()

    def replay_mission_id(self) -> Optional[str]:
        return self._replay_mission if self.is_replaying() else None

    async def start_replay(self, mission_id: str, speed: float = 5.0) -> bool:
        if self.is_replaying():
            return False
        self._replay_mission = mission_id
        self._replay_task = asyncio.create_task(self._replay_loop(mission_id, speed))
        return True

    async def stop_replay(self) -> None:
        if self._replay_task is not None and not self._replay_task.done():
            self._replay_task.cancel()
            try:
                await self._replay_task
            except asyncio.CancelledError:
                pass
        self._replay_mission = None

    async def _replay_loop(self, mission_id: str, speed: float) -> None:
        db = SessionLocal()
        try:
            mission = db.get(Mission, mission_id)
            if mission is None:
                return
            engine_id = mission.engine_id
            rows = db.query(Telemetry).filter(Telemetry.mission_id == mission_id).order_by(Telemetry.id).all()
            digital_twin.reset_buffers(mission_id)
            n = len(rows)
            logger.info("Replaying mission %s (%d rows) at %gx", mission_id, n, speed)
            for i, t in enumerate(rows):
                if self._replay_task is None or self._replay_task.cancelled():
                    break
                row = telemetry_row_to_dict(t)
                twin = digital_twin.compute_twin_state(mission_id, row)
                await manager.broadcast(engine_id, {"event": "telemetry_update", "payload": row})
                await manager.broadcast(engine_id, {"event": "twin_state_update", "payload": twin})
                await manager.broadcast(engine_id, {"event": "replay_status", "payload": {
                    "replaying": True, "mission_id": mission_id, "progress": round(100.0 * (i + 1) / n, 1)}})
                await asyncio.sleep(SIM_DT / speed)
            await manager.broadcast(engine_id, {"event": "replay_status", "payload": {
                "replaying": False, "mission_id": mission_id, "progress": 100.0}})
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.exception("Replay failed: %s", exc)
        finally:
            db.close()


runner = SimulationRunner()
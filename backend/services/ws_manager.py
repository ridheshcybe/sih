"""WebSocket connection manager.

Tracks clients per engine_id, broadcasts JSON messages, and throttles each
client to WS_MAX_MSGS_PER_SEC messages per second (newer messages supersede
dropped ones, so the UI always converges on the latest state).
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Set

from fastapi import WebSocket

from backend.config import WS_MAX_MSGS_PER_SEC

logger = logging.getLogger("sih26054.ws")

MESSAGE_TYPES = {
    "telemetry_update",
    "twin_state_update",
    "anomaly_detected",
    "fault_prediction",
    "health_update",
    "rul_update",
    "maintenance_advisory",
    "mission_phase_change",
    "simulation_status",
    "system_error",
    "replay_status",
}


class WSManager:
    def __init__(self, max_msgs_per_sec: int = WS_MAX_MSGS_PER_SEC):
        self.max_per_sec = max_msgs_per_sec
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._send_times: Dict[int, list] = {}

    async def connect(self, engine_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(engine_id, set()).add(websocket)
        logger.info("WS client connected for engine %s (total: %d)", engine_id, len(self._connections[engine_id]))

    async def disconnect(self, engine_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(engine_id)
        if conns and websocket in conns:
            conns.discard(websocket)
            logger.info("WS client disconnected for engine %s", engine_id)
        self._send_times.pop(id(websocket), None)

    async def _send_throttled(self, websocket: WebSocket, message: dict) -> None:
        key = id(websocket)
        now = time.monotonic()
        times = [t for t in self._send_times.get(key, []) if now - t < 1.0]
        if len(times) >= self.max_per_sec:
            return  # drop; a newer message will supersede this one
        times.append(now)
        self._send_times[key] = times
        try:
            await websocket.send_json(message)
        except Exception:  # noqa: BLE001 - broken client is cleaned up elsewhere
            pass

    async def broadcast(self, engine_id: str, message: dict) -> None:
        for websocket in list(self._connections.get(engine_id, ())):
            await self._send_throttled(websocket, message)

    async def broadcast_all(self, message: dict) -> None:
        for engine_id in list(self._connections):
            await self.broadcast(engine_id, message)

    def client_count(self, engine_id: str) -> int:
        return len(self._connections.get(engine_id, ()))


manager = WSManager()
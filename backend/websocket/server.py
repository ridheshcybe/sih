from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("websocket.server")
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.connections = defaultdict(set)

    async def connect(self, websocket: WebSocket, engine_id: str):
        await websocket.accept()
        self.connections[str(engine_id)].add(websocket)
        logger.info("WebSocket client connected to engine_id=%s; total=%d", engine_id, len(self.connections[str(engine_id)]))

    def disconnect(self, websocket: WebSocket, engine_id: str):
        engine_key = str(engine_id)
        self.connections.get(engine_key, set()).discard(websocket)
        if not self.connections.get(engine_key):
            self.connections.pop(engine_key, None)
        logger.info("WebSocket client disconnected from engine_id=%s", engine_id)

    async def broadcast(self, engine_id: str, message: dict):
        for websocket in list(self.connections.get(str(engine_id), set())):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(websocket, engine_id)


connection_manager = ConnectionManager()


@router.websocket("/ws/telemetry/{engine_id}")
async def telemetry_ws(websocket: WebSocket, engine_id: str):
    await connection_manager.connect(websocket, engine_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, engine_id)
    except Exception as exc:  # pragma: no cover
        logger.exception("WS error for engine_id=%s: %s", engine_id, exc)
        connection_manager.disconnect(websocket, engine_id)

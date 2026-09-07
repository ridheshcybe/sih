from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Set

logger = logging.getLogger("twin_update_service")

_RATE_LIMIT_SECONDS = 1.0
_RATE_LIMIT_PER_CLIENT = 5
_client_windows: Dict[Any, Deque[float]] = defaultdict(deque)


def _allowed_for_client(client: Any) -> bool:
    window = _client_windows[client]
    now = time.monotonic()
    cutoff = now - _RATE_LIMIT_SECONDS
    while window and window[0] <= cutoff:
        window.popleft()
    if len(window) >= _RATE_LIMIT_PER_CLIENT:
        return False
    window.append(now)
    return True


def broadcast_twin_state(engine_id: Any, twin_state: Dict[str, Any]) -> None:
    """Send twin updates to connected engine clients with basic throttling."""
    try:
        from backend.websocket.server import connection_manager
    except ImportError:  # pragma: no cover
        from websocket.server import connection_manager

    message = {
        "event": "twin_state_update",
        "payload": {
            "mission_id": twin_state.get("mission_id"),
            "timestamp": twin_state.get("timestamp"),
            "health_index": twin_state.get("health_index"),
            "anomaly_score": twin_state.get("anomaly_score"),
            "sensors": twin_state.get("sensors", {}),
            "fault_probs": twin_state.get("fault_probs", {}),
            "rul_estimate": twin_state.get("rul_estimate"),
            "rul_confidence": twin_state.get("rul_confidence"),
        },
    }

    clients = list(connection_manager.connections.get(str(engine_id), set()) | connection_manager.connections.get(engine_id, set()))
    for client in clients:
        if not _allowed_for_client(client):
            logger.warning("Dropping throttled twin message for engine_id=%s", engine_id)
            continue
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(client.send_json(message))
        except RuntimeError:
            try:
                asyncio.run(client.send_json(message))
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to send twin update to websocket client: %s", exc)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to enqueue twin update: %s", exc)

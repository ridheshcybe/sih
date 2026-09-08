"""SIH26054 FastAPI backend entrypoint.

Run from the project root:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import APP_NAME, APP_VERSION, DEFAULT_ENGINE_ID, DEFAULT_ENGINE_NAME
from backend.database import SessionLocal, init_db
from backend.models import Engine
from backend.routers import engines, faults, missions, replay, reports, simulation, system, telemetry
from backend.services.ml_inference import get_ml_predictor
from backend.services.simulation_runner import runner
from backend.services.ws_manager import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sih26054")


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("Backend starting ...")
    init_db()
    _ensure_default_engine()
    get_ml_predictor()  # preload ML models (fallbacks if missing)
    print("Backend ready. ML models:", get_ml_predictor().status)
    yield
    print("Backend shutting down ...")
    for engine_id in list(runner.running_engines()):
        await runner.stop_mission(engine_id)
    await runner.stop_replay()


def _ensure_default_engine() -> None:
    db = SessionLocal()
    try:
        if db.get(Engine, DEFAULT_ENGINE_ID) is None:
            db.add(Engine(id=DEFAULT_ENGINE_ID, name=DEFAULT_ENGINE_NAME, status="OPERATIONAL"))
            db.commit()
            logger.info("Created default engine %s", DEFAULT_ENGINE_ID)
    finally:
        db.close()


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(missions.router)
app.include_router(engines.router)
app.include_router(simulation.router)
app.include_router(faults.router)
app.include_router(replay.router)
app.include_router(reports.router)
app.include_router(telemetry.router)


@app.websocket("/ws/telemetry/{engine_id}")
async def ws_telemetry(websocket: WebSocket, engine_id: str) -> None:
    await manager.connect(engine_id, websocket)
    try:
        while True:
            # Block until the client sends something or disconnects; inbound
            # client messages are informational only.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(engine_id, websocket)
    except Exception:  # noqa: BLE001
        await manager.disconnect(engine_id, websocket)


@app.get("/")
def root() -> dict:
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/api/system/health",
        "ws": f"/ws/telemetry/{DEFAULT_ENGINE_ID}",
    }
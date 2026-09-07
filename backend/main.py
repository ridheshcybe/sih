import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_system import router as system_router
from backend.api.routes_telemetry import router as telemetry_router
from backend.api.routes_control import router as control_router
from backend.config import APP_NAME, APP_VERSION, DEBUG, HOST, PORT
from backend.db.database import create_all_tables
from backend.websocket.server import router as websocket_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("backend.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Backend starting")
    logger.info("Loading backend configuration")
    create_all_tables()
    yield
    print("Backend shutting down")


app = FastAPI(title=APP_NAME, version=APP_VERSION, debug=DEBUG, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info("%s %s -> %s in %.2f ms", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.get("/")
async def read_root():
    return {"status": "API Running", "service": "DigitalTwinBackend"}


app.include_router(system_router)
app.include_router(telemetry_router)
app.include_router(control_router)
app.include_router(websocket_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=DEBUG)

"""Application configuration for the digital twin backend."""

import os
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


def _as_bool(value: str, default: str = "false") -> bool:
    return str(value or default).strip().lower() in {"1", "true", "yes", "on"}


APP_NAME = "Digital Twin API"
APP_VERSION = "1.0.0"
DEBUG = _as_bool(os.getenv("TWIN_DEBUG", "true"))
HOST = os.getenv("TWIN_HOST", "0.0.0.0")
PORT = int(os.getenv("TWIN_PORT", "8000"))

DATABASE_URL = os.getenv(
    "TWIN_DATABASE_URL",
    f"sqlite:///{ROOT / 'backend' / 'digital_twin.db'}",
)
MODEL_PATH = os.getenv("TWIN_MODEL_PATH", str(ROOT / "models"))
TELEMETRY_BATCH_LIMIT = int(os.getenv("TWIN_BATCH_LIMIT", "500"))
WS_MAX_MSG_PER_SEC = float(os.getenv("TWIN_WS_RATE", "5"))
WS_QUEUE_MODE = os.getenv("TWIN_WS_QUEUE_MODE", "drop_oldest")

settings = SimpleNamespace(
    APP_NAME=APP_NAME,
    APP_VERSION=APP_VERSION,
    DEBUG=DEBUG,
    HOST=HOST,
    PORT=PORT,
    DATABASE_URL=DATABASE_URL,
    MODEL_PATH=MODEL_PATH,
    TELEMETRY_BATCH_LIMIT=TELEMETRY_BATCH_LIMIT,
    WS_MAX_MSG_PER_SEC=WS_MAX_MSG_PER_SEC,
    WS_QUEUE_MODE=WS_QUEUE_MODE,
)


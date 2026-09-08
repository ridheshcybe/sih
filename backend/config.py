"""Backend configuration.

Everything has laptop-friendly defaults and can be overridden with
environment variables (e.g. SIH_DATABASE_URL, SIH_MODEL_PATH).
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("SIH_DATABASE_URL", f"sqlite:///{DATA_DIR / 'sih26054.db'}")
MODEL_PATH = os.environ.get("SIH_MODEL_PATH", str(MODELS_DIR))

# Simulation step (seconds) and default engine identity.
SIM_DT = float(os.environ.get("SIH_SIM_DT", "0.1"))
DEFAULT_ENGINE_ID = os.environ.get("SIH_ENGINE_ID", "ENG-001")
DEFAULT_ENGINE_NAME = "Aero Piston Engine Prototype"
DEFAULT_PROFILE_ID = "standard_isr"

# WebSocket throttling: max messages per second per client connection.
WS_MAX_MSGS_PER_SEC = 5

APP_NAME = "SIH26054 Digital Twin"
APP_VERSION = "0.1.0"
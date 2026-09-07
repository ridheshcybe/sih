from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TRAIN_PATH = DATA_DIR / "train.csv"
VAL_PATH = DATA_DIR / "val.csv"
TEST_PATH = DATA_DIR / "test.csv"
README_PATH = DATA_DIR / "README.md"

PHASE_ORDER = [
    "startup",
    "takeoff",
    "climb",
    "cruise",
    "endurance",
    "descent",
    "landing",
]

PHASE_DURATIONS = {
    "startup": (0, 30),
    "takeoff": (30, 90),
    "climb": (90, 300),
    "cruise": (300, 900),
    "endurance": (900, 1500),
    "descent": (1500, 1650),
    "landing": (1650, 1800),
}

PROFILE_IDS = [
    "standard_isr",
    "high_altitude",
    "hot_weather",
    "aggressive",
]

FAULT_TYPES = [
    "misfire",
    "injector_degradation",
    "lubrication_issue",
    "overheating",
    "sensor_drift",
    "sensor_dropout",
    "abnormal_vibration",
    "battery_alternator_degradation",
]

SENSOR_COLUMNS = [
    "timestamp",
    "mission_id",
    "profile_id",
    "phase",
    "throttle",
    "rpm",
    "altitude",
    "ambient_temperature",
    "cht",
    "egt",
    "oil_pressure",
    "oil_temperature",
    "fuel_flow",
    "vibration_rms",
    "battery_voltage",
    "alternator_current",
    "injection_timing",
    "fault_type",
    "fault_severity",
    "degradation_level",
    "rul_label",
]

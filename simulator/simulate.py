"""Mission simulation core: step the engine model through a profile with faults.

Produces a tidy pandas DataFrame of telemetry rows with label columns, matching
the backend telemetry schema exactly.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from simulator import LABEL_COLUMNS, SENSOR_COLUMNS

# Sensors whose healthy-model value is recorded for residual computation.
# The twin compares observed vs this healthy-model value, so residuals reflect
# exactly the fault signature (transients and noise cancel out).
EXPECTED_SENSORS = [
    "cht", "egt", "oil_pressure", "oil_temperature", "fuel_flow", "vibration_rms",
]
from simulator.engine_model import EngineModel
from simulator.fault_injection import (
    InjectedFault,
    apply_faults,
    degradation_level,
    dominant_fault,
    parse_fault_config,
    rul_label,
)
from simulator.mission_profiles import get_profile, phase_at

# Fixed mission epoch so identical seeds produce identical CSVs (reproducibility).
_MISSION_EPOCH = _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)


def simulate_mission(
    profile_id: str = "standard_isr",
    duration_s: Optional[float] = None,
    fault_type: Optional[str] = None,
    severity: float = 0.6,
    fault_start_s: float = 300.0,
    fault_duration_s: float = 240.0,
    pattern: str = "gradual",
    dt: float = 0.1,
    seed: int = 42,
    mission_id: Optional[str] = None,
) -> pd.DataFrame:
    """Simulate one mission and return a DataFrame of telemetry + labels.

    If duration_s is None the full profile is simulated (typically ~40 min).
    """
    profile = get_profile(profile_id)
    total = duration_s if duration_s is not None else sum(p[1] for p in profile)
    if total <= 0:
        raise ValueError("duration_s must be > 0")

    mission_id = mission_id or f"M-{int(seed) % 100000000:08d}"
    model = EngineModel(seed=seed)
    rng = np.random.default_rng(seed)
    fault = parse_fault_config(fault_type, severity, fault_start_s, fault_duration_s, pattern)
    faults: List[InjectedFault] = [fault] if fault else []

    rows: List[Dict] = []
    t = 0.0
    while t < total:
        phase, throttle, altitude, ambient = phase_at(profile, t)
        healthy = model.step(throttle, altitude, ambient, dt=dt)
        ambient_temperature = ambient
        sensors = apply_faults(healthy, faults, t, rng)
        expected_fields = {f"expected_{s}": healthy[s] for s in EXPECTED_SENSORS}
        deg = degradation_level(faults, t)
        label = dominant_fault(faults, t)
        ts = (_MISSION_EPOCH + _dt.timedelta(seconds=round(t, 1))).isoformat(timespec="milliseconds")
        row = {
            "timestamp": ts,
            "mission_id": mission_id,
            "profile_id": profile_id,
            "phase": phase,
            "throttle": round(throttle, 1),
            **sensors,
            **expected_fields,
            "altitude": round(float(altitude), 1),
            "ambient_temperature": round(float(ambient_temperature), 1),
            "fault_label": label,
            "fault_severity": round(max(f.severity for f in faults) if faults else 0.0, 2),
            "degradation_level": deg,
            "rul_label": rul_label(deg, rng),
        }
        rows.append(row)
        t += dt

    df = pd.DataFrame(rows)
    expected_cols = [f"expected_{s}" for s in EXPECTED_SENSORS]
    cols = (["timestamp", "mission_id", "profile_id", "phase", "throttle"]
            + SENSOR_COLUMNS + expected_cols + LABEL_COLUMNS)
    return df[cols]


def healthy_slice(df: pd.DataFrame) -> pd.DataFrame:
    """Rows of a mission where no fault is active (fault_label == 'none')."""
    return df[df["fault_label"] == "none"].copy()


if __name__ == "__main__":
    df = simulate_mission(profile_id="standard_isr", duration_s=60, seed=1)
    print(df.head(10).to_string(index=False))
    print(f"\nSimulated {len(df)} rows.")
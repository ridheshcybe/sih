"""Fault injection for the SIH26054 simulator.

Each fault type modifies specific sensor channels with a time pattern
('gradual' ramp or 'sudden' step) scaled by a severity 0..1, over an active
window [start_s, start_s + duration_s]. It also produces label columns:
fault_label, fault_severity, degradation_level, rul_label.
"""

from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np

FAULT_TYPES = [
    "misfire",
    "injector_degradation",
    "lubrication_issue",
    "overheating",
    "sensor_drift",
    "abnormal_vibration",
    "battery_alternator_degradation",
]

RUL_MAX_HOURS = 500.0  # nominal remaining useful life of a healthy engine

SENSOR_RANGES: Dict[str, tuple] = {
    "rpm": (0.0, 5800.0),
    "cht": (20.0, 300.0),
    "egt": (100.0, 900.0),
    "oil_pressure": (0.2, 5.5),
    "oil_temperature": (10.0, 150.0),
    "fuel_flow": (0.5, 26.0),
    "vibration_rms": (0.05, 6.0),
    "battery_voltage": (18.0, 28.5),
    "alternator_current": (0.0, 60.0),
    "injection_timing": (5.0, 40.0),
}


class InjectedFault:
    """One active fault: which sensors it touches and how."""

    def __init__(self, fault_type: str, severity: float, start_s: float, duration_s: float,
                 pattern: str = "gradual", ramp_s: float = 60.0):
        self.fault_type = fault_type
        self.severity = float(np.clip(severity, 0.05, 1.0))
        self.start_s = float(start_s)
        self.duration_s = float(duration_s)
        self.pattern = pattern  # 'gradual' or 'sudden'
        self.ramp_s = float(ramp_s)

    def is_active(self, t: float) -> bool:
        return self.start_s <= t <= self.start_s + self.duration_s

    def envelope(self, t: float) -> float:
        """0..1 multiplier describing how fully the fault has manifested."""
        if not self.is_active(t):
            return 0.0
        local = t - self.start_s
        if self.pattern == "sudden":
            return self.severity
        ramp = min(local / max(self.ramp_s, 1.0), 1.0)
        tail = min((self.start_s + self.duration_s - t) / max(self.ramp_s, 1.0), 1.0)
        return self.severity * min(ramp, tail)


FAULT_EFFECTS: Dict[str, Dict[str, str]] = {
    "misfire": {
        "vibration_rms": "add 1.6",
        "egt": "add 45",
        "rpm": "jitter 1.6",
    },
    "injector_degradation": {
        "fuel_flow": "scale 0.65",
        "egt": "add 65",
        "cht": "add 28",
    },
    "lubrication_issue": {
        "oil_pressure": "sub 1.9",
        "oil_temperature": "add 28",
    },
    "overheating": {
        "cht": "add 75",
        "egt": "add 55",
        "oil_temperature": "add 22",
    },
    "sensor_drift": {
        "cht": "drift 55",
        "egt": "drift 40",
    },
    "abnormal_vibration": {
        "vibration_rms": "add 2.2",
        "egt": "add 18",
    },
    "battery_alternator_degradation": {
        "battery_voltage": "sub 2.8",
        "alternator_current": "sub 18",
    },
}


def apply_faults(sensors: Dict[str, float], faults: list, t: float,
                 rng: np.random.Generator) -> Dict[str, float]:
    """Modify a healthy sensor dict in place according to active faults."""
    out = dict(sensors)
    for f in faults:
        env = f.envelope(t)
        if env <= 0.0:
            continue
        for sensor, spec in FAULT_EFFECTS.get(f.fault_type, {}).items():
            op, _, val = spec.partition(" ")
            val = float(val)
            if op == "add":
                out[sensor] = out.get(sensor, 0.0) + val * env
            elif op == "sub":
                out[sensor] = out.get(sensor, 0.0) - val * env
            elif op == "scale":
                out[sensor] = out.get(sensor, 0.0) * (1.0 - (1.0 - val) * env)
            elif op == "jitter":
                out[sensor] = out.get(sensor, 0.0) + rng.normal(0.0, 1.0) * val * env
            elif op == "drift":
                # Drift grows linearly over the fault lifetime.
                local = max(0.0, min((t - f.start_s) / max(f.duration_s, 1.0), 1.0))
                out[sensor] = out.get(sensor, 0.0) + val * env * local
    # Clamp everything to plausible ranges so combined faults stay physical.
    for sensor, (lo, hi) in SENSOR_RANGES.items():
        if sensor in out:
            out[sensor] = float(np.clip(out[sensor], lo, hi))
    return out


def degradation_level(faults: list, t: float) -> float:
    """0..1: how degraded the engine is at time t (max over active faults)."""
    level = 0.0
    for f in faults:
        env = f.envelope(t)
        if env > level:
            level = env
    return round(float(level), 4)


def rul_label(degradation: float, rng: np.random.Generator) -> float:
    """Remaining useful life label (hours) consistent with degradation."""
    return round(max(0.0, RUL_MAX_HOURS * (1.0 - degradation) + rng.normal(0.0, 5.0)), 1)


def dominant_fault(faults: list, t: float) -> Optional[str]:
    active = [f.fault_type for f in faults if f.envelope(t) > 0.05]
    return active[0] if active else "none"


def parse_fault_config(fault_type: Optional[str], severity: float, start_s: float,
                       duration_s: float, pattern: str = "gradual",
                       ramp_s: float = 60.0) -> Optional[InjectedFault]:
    """Build an InjectedFault from config values, or None for a healthy mission."""
    if not fault_type or fault_type == "none":
        return None
    if fault_type not in FAULT_TYPES:
        raise ValueError(f"Unknown fault type '{fault_type}'. Available: {FAULT_TYPES}")
    return InjectedFault(fault_type, severity, start_s, duration_s, pattern, ramp_s)
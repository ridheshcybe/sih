from __future__ import annotations

import math
import random
from typing import Dict, List

from simulator.config import PHASE_DURATIONS, PHASE_ORDER


PROFILE_LIBRARY: Dict[str, Dict[str, Dict[str, float]]] = {
    "standard_isr": {
        "throttle": {
            "startup": 25.0,
            "takeoff": 90.0,
            "climb": 75.0,
            "cruise": 64.0,
            "endurance": 60.0,
            "descent": 45.0,
            "landing": 30.0,
        },
        "rpm": {
            "startup": 1100.0,
            "takeoff": 2700.0,
            "climb": 2450.0,
            "cruise": 2300.0,
            "endurance": 2200.0,
            "descent": 1800.0,
            "landing": 1200.0,
        },
        "altitude": {
            "startup": 0.0,
            "takeoff": 0.0,
            "climb": 3000.0,
            "cruise": 3000.0,
            "endurance": 2800.0,
            "descent": 0.0,
            "landing": 0.0,
        },
        "ambient_temperature": {
            "startup": 24.0,
            "takeoff": 25.0,
            "climb": 20.0,
            "cruise": 18.0,
            "endurance": 17.0,
            "descent": 18.0,
            "landing": 22.0,
        },
    },
    "high_altitude": {
        "throttle": {
            "startup": 28.0,
            "takeoff": 95.0,
            "climb": 80.0,
            "cruise": 68.0,
            "endurance": 66.0,
            "descent": 48.0,
            "landing": 32.0,
        },
        "rpm": {
            "startup": 1200.0,
            "takeoff": 2800.0,
            "climb": 2550.0,
            "cruise": 2400.0,
            "endurance": 2300.0,
            "descent": 1850.0,
            "landing": 1250.0,
        },
        "altitude": {
            "startup": 0.0,
            "takeoff": 0.0,
            "climb": 5000.0,
            "cruise": 5000.0,
            "endurance": 4500.0,
            "descent": 0.0,
            "landing": 0.0,
        },
        "ambient_temperature": {
            "startup": 10.0,
            "takeoff": 8.0,
            "climb": -2.0,
            "cruise": -8.0,
            "endurance": -12.0,
            "descent": 2.0,
            "landing": 8.0,
        },
    },
    "hot_weather": {
        "throttle": {
            "startup": 30.0,
            "takeoff": 92.0,
            "climb": 78.0,
            "cruise": 66.0,
            "endurance": 62.0,
            "descent": 46.0,
            "landing": 35.0,
        },
        "rpm": {
            "startup": 1150.0,
            "takeoff": 2750.0,
            "climb": 2500.0,
            "cruise": 2350.0,
            "endurance": 2250.0,
            "descent": 1850.0,
            "landing": 1250.0,
        },
        "altitude": {
            "startup": 0.0,
            "takeoff": 0.0,
            "climb": 2500.0,
            "cruise": 2500.0,
            "endurance": 2300.0,
            "descent": 0.0,
            "landing": 0.0,
        },
        "ambient_temperature": {
            "startup": 42.0,
            "takeoff": 44.0,
            "climb": 46.0,
            "cruise": 47.0,
            "endurance": 48.0,
            "descent": 44.0,
            "landing": 40.0,
        },
    },
    "aggressive": {
        "throttle": {
            "startup": 35.0,
            "takeoff": 100.0,
            "climb": 88.0,
            "cruise": 74.0,
            "endurance": 68.0,
            "descent": 52.0,
            "landing": 28.0,
        },
        "rpm": {
            "startup": 1250.0,
            "takeoff": 2900.0,
            "climb": 2700.0,
            "cruise": 2450.0,
            "endurance": 2350.0,
            "descent": 1900.0,
            "landing": 1300.0,
        },
        "altitude": {
            "startup": 0.0,
            "takeoff": 0.0,
            "climb": 4200.0,
            "cruise": 3500.0,
            "endurance": 3000.0,
            "descent": 0.0,
            "landing": 0.0,
        },
        "ambient_temperature": {
            "startup": 28.0,
            "takeoff": 30.0,
            "climb": 34.0,
            "cruise": 33.0,
            "endurance": 35.0,
            "descent": 31.0,
            "landing": 29.0,
        },
    },
}


def _phase_value(phase_name: str, metric: str, t: float, profile: Dict[str, Dict[str, float]]) -> float:
    start_value = profile[metric][phase_name]
    return start_value


def _noise(value: float, scale: float) -> float:
    return value + random.uniform(-scale, scale)


def _interpolate(start: float, end: float, progress: float) -> float:
    return start + (end - start) * progress


def _phase_transition_metrics(profile_id: str, phase_name: str, t: float, baseline_t: float) -> Dict[str, float]:
    profile = PROFILE_LIBRARY[profile_id]
    if phase_name == "startup":
        return {
            "throttle": _noise(profile["throttle"][phase_name], 3.0),
            "rpm": _noise(profile["rpm"][phase_name], 2.0),
            "altitude": max(0.0, _noise(profile["altitude"][phase_name], 5.0)),
            "ambient_temperature": _noise(profile["ambient_temperature"][phase_name], 1.0),
        }

    if phase_name == "takeoff":
        progress = min(1.0, max(0.0, (t - 30.0) / 60.0))
        return {
            "throttle": _interpolate(30.0, profile["throttle"][phase_name], progress) + random.uniform(-2.0, 2.0),
            "rpm": _interpolate(1200.0, profile["rpm"][phase_name], progress) + random.uniform(-2.0, 2.0),
            "altitude": _interpolate(0.0, profile["altitude"][phase_name], progress) + random.uniform(-10.0, 10.0),
            "ambient_temperature": profile["ambient_temperature"][phase_name] + random.uniform(-1.0, 1.0),
        }

    if phase_name == "climb":
        progress = min(1.0, max(0.0, (t - 90.0) / 210.0))
        return {
            "throttle": _interpolate(profile["throttle"]["takeoff"], profile["throttle"][phase_name], progress) + random.uniform(-3.0, 3.0),
            "rpm": _interpolate(profile["rpm"]["takeoff"], profile["rpm"][phase_name], progress) + random.uniform(-2.0, 2.0),
            "altitude": _interpolate(0.0, profile["altitude"][phase_name], progress) + random.uniform(-15.0, 15.0),
            "ambient_temperature": profile["ambient_temperature"][phase_name] + random.uniform(-1.5, 1.5),
        }

    if phase_name == "cruise":
        progress = min(1.0, max(0.0, (t - 300.0) / 600.0))
        return {
            "throttle": _interpolate(profile["throttle"]["climb"], profile["throttle"][phase_name], progress) + random.uniform(-2.5, 2.5),
            "rpm": _interpolate(profile["rpm"]["climb"], profile["rpm"][phase_name], progress) + random.uniform(-1.5, 1.5),
            "altitude": profile["altitude"][phase_name] + random.uniform(-15.0, 15.0),
            "ambient_temperature": profile["ambient_temperature"][phase_name] + random.uniform(-1.0, 1.0),
        }

    if phase_name == "endurance":
        return {
            "throttle": _noise(profile["throttle"][phase_name], 2.0),
            "rpm": _noise(profile["rpm"][phase_name], 1.5),
            "altitude": max(0.0, profile["altitude"][phase_name] + random.uniform(-20.0, 20.0)),
            "ambient_temperature": profile["ambient_temperature"][phase_name] + random.uniform(-1.5, 1.5),
        }

    if phase_name == "descent":
        progress = min(1.0, max(0.0, (t - 1500.0) / 150.0))
        return {
            "throttle": _interpolate(profile["throttle"]["endurance"], profile["throttle"][phase_name], progress) + random.uniform(-2.0, 2.0),
            "rpm": _interpolate(profile["rpm"]["endurance"], profile["rpm"][phase_name], progress) + random.uniform(-1.5, 1.5),
            "altitude": _interpolate(profile["altitude"]["endurance"], profile["altitude"][phase_name], progress) + random.uniform(-15.0, 15.0),
            "ambient_temperature": profile["ambient_temperature"][phase_name] + random.uniform(-1.0, 1.0),
        }

    if phase_name == "landing":
        progress = min(1.0, max(0.0, (t - 1650.0) / 150.0))
        return {
            "throttle": _interpolate(profile["throttle"]["descent"], profile["throttle"][phase_name], progress) + random.uniform(-2.0, 2.0),
            "rpm": _interpolate(profile["rpm"]["descent"], profile["rpm"][phase_name], progress) + random.uniform(-2.0, 2.0),
            "altitude": _interpolate(profile["altitude"]["descent"], profile["altitude"][phase_name], progress) + random.uniform(-10.0, 10.0),
            "ambient_temperature": profile["ambient_temperature"][phase_name] + random.uniform(-1.0, 1.0),
        }

    return {
        "throttle": profile["throttle"][phase_name],
        "rpm": profile["rpm"][phase_name],
        "altitude": profile["altitude"][phase_name],
        "ambient_temperature": profile["ambient_temperature"][phase_name],
    }


def _resolve_phase_name(seconds: float) -> str:
    for phase_name in PHASE_ORDER:
        start, end = PHASE_DURATIONS[phase_name]
        if start <= seconds < end:
            return phase_name
    return "landing"


def generate_mission_profile(profile_id: str, duration_seconds: int = 1800) -> Dict[str, List[Dict[str, float]] | str | int]:
    """Return per-phase metadata and a second-by-second timeline with realistic target values."""
    if profile_id not in PROFILE_LIBRARY:
        raise ValueError(f"Unsupported profile_id: {profile_id}")

    phases = []
    timeline = []

    for phase_name in PHASE_ORDER:
        start_sec, end_sec = PHASE_DURATIONS[phase_name]
        if end_sec > duration_seconds:
            end_sec = duration_seconds
        if start_sec >= duration_seconds:
            continue
        phase_entry = {
            "phase": phase_name,
            "start_time": start_sec,
            "end_time": end_sec,
            "throttle_target": PROFILE_LIBRARY[profile_id]["throttle"][phase_name],
            "rpm_target": PROFILE_LIBRARY[profile_id]["rpm"][phase_name],
            "altitude_target": PROFILE_LIBRARY[profile_id]["altitude"][phase_name],
            "ambient_temperature_target": PROFILE_LIBRARY[profile_id]["ambient_temperature"][phase_name],
        }
        phases.append(phase_entry)

        for t in range(start_sec, end_sec):
            metrics = _phase_transition_metrics(profile_id, phase_name, float(t), float(start_sec))
            timeline.append({
                "timestamp": float(t),
                "phase": phase_name,
                "throttle": max(0.0, min(100.0, metrics["throttle"])),
                "rpm": max(600.0, metrics["rpm"]),
                "altitude": max(0.0, metrics["altitude"]),
                "ambient_temperature": metrics["ambient_temperature"],
            })

    return {
        "profile_id": profile_id,
        "duration_seconds": duration_seconds,
        "phases": phases,
        "timeline": timeline,
    }


PROFILES = list(PROFILE_LIBRARY.keys())

__all__ = ["PROFILE_LIBRARY", "PROFILES", "generate_mission_profile"]

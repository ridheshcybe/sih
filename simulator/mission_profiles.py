"""Mission profiles and phase logic for the SIH26054 simulator.

Each profile is a sequence of phases with (duration, throttle %, altitude m,
ambient °C). The engine model's first-order lags smooth the transitions between
phases so the telemetry ramps instead of jumping.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# phase: (duration_seconds, throttle_%, altitude_m, ambient_temperature_°C)
Phase = Tuple[str, float, float, float, float]
Profile = List[Phase]

PROFILES: Dict[str, Profile] = {
    "standard_isr": [
        ("startup", 30, 15, 0, 15),
        ("takeoff", 60, 85, 0, 15),
        ("climb", 300, 70, 4000, 10),
        ("cruise", 1200, 55, 4000, 10),
        ("endurance", 900, 45, 4000, 8),
        ("descent", 240, 30, 0, 12),
        ("landing", 90, 20, 0, 15),
        ("shutdown", 30, 0, 0, 15),
    ],
    "high_altitude": [
        ("startup", 30, 15, 0, 10),
        ("takeoff", 60, 90, 0, 10),
        ("climb", 600, 75, 9000, -5),
        ("cruise", 1800, 60, 9000, -10),
        ("descent", 300, 35, 0, 5),
        ("landing", 90, 20, 0, 10),
        ("shutdown", 30, 0, 0, 10),
    ],
    "hot_weather": [
        ("startup", 30, 15, 0, 42),
        ("takeoff", 60, 85, 0, 42),
        ("climb", 300, 70, 4000, 36),
        ("cruise", 1200, 55, 4000, 34),
        ("endurance", 900, 45, 4000, 32),
        ("descent", 240, 30, 0, 38),
        ("landing", 90, 20, 0, 40),
        ("shutdown", 30, 0, 0, 40),
    ],
    "aggressive": [
        ("startup", 15, 20, 0, 15),
        ("takeoff", 30, 95, 0, 15),
        ("climb", 90, 90, 2000, 12),
        ("cruise", 180, 60, 2000, 12),
        ("descent", 90, 85, 500, 14),
        ("climb", 120, 90, 3500, 10),
        ("cruise", 240, 65, 3500, 10),
        ("descent", 90, 40, 0, 15),
        ("landing", 60, 25, 0, 15),
        ("shutdown", 20, 0, 0, 15),
    ],
}

PROFILE_NAMES = list(PROFILES.keys())


def total_duration(profile: Profile) -> float:
    return sum(p[1] for p in profile)


def get_profile(profile_id: str) -> Profile:
    if profile_id not in PROFILES:
        raise KeyError(f"Unknown profile '{profile_id}'. Available: {PROFILE_NAMES}")
    return PROFILES[profile_id]


def phase_at(profile: Profile, elapsed: float) -> Tuple[str, float, float, float]:
    """Return (phase_name, throttle, altitude, ambient) for the given elapsed time."""
    t = 0.0
    for name, duration, throttle, altitude, ambient in profile:
        if elapsed < t + duration or (name == profile[-1][0]):
            return name, throttle, altitude, ambient
        t += duration
    last = profile[-1]
    return last[0], last[2], last[3], last[4]
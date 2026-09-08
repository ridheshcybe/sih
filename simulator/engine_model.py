"""Physics-inspired engine model for a MALE-UAV aero piston engine.

Simplified first-order relationships between throttle / altitude / ambient
temperature and the 10 monitored sensor channels. The model is deliberately
simple (no claim of thermodynamic fidelity) but produces plausible, smooth,
noisy telemetry suitable for a software demonstrator.
"""

from __future__ import annotations

import math
from typing import Dict

import numpy as np

# --- Operating limits (plausible ranges for a ~100 hp UAV piston engine) ---
IDLE_RPM = 1800.0
MAX_RPM = 5500.0
EGT_RANGE = (120.0, 820.0)      # °C exhaust gas temperature
CHT_RANGE = (40.0, 260.0)       # °C cylinder head temperature
OIL_P_RANGE = (0.3, 5.5)        # bar
OIL_T_RANGE = (15.0, 130.0)     # °C
FUEL_RANGE = (2.0, 24.0)        # L/h
VIB_RANGE = (0.1, 4.0)          # g
BATT_RANGE = (22.0, 28.5)       # V
ALT_RANGE = (0.0, 60.0)         # A
INJ_RANGE = (10.0, 36.0)        # deg BTDC

TAU_RPM = 0.8    # s, rpm inertia
TAU_CHT = 6.0    # s, thermal inertia of cylinder head
TAU_OILT = 25.0  # s, thermal inertia of oil


class EngineModel:
    """Stateful engine model: call step() with control inputs to get a sensor reading."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.rpm = IDLE_RPM
        self.cht = 95.0
        self.oil_temperature = 55.0
        self.egt = 250.0
        self._last_throttle = 0.0

    def reset(self, seed: int | None = None) -> None:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.rpm = IDLE_RPM
        self.cht = 95.0
        self.oil_temperature = 55.0
        self.egt = 250.0
        self._last_throttle = 0.0

    def step(
        self,
        throttle: float,
        altitude: float,
        ambient_temperature: float,
        dt: float = 0.1,
    ) -> Dict[str, float]:
        """Advance the model by dt seconds and return one telemetry sample."""
        throttle = float(np.clip(throttle, 0.0, 100.0))
        altitude = float(np.clip(altitude, 0.0, 15000.0))
        ambient_temperature = float(np.clip(ambient_temperature, -20.0, 55.0))
        r = self.rng

        # --- RPM: first-order lag toward throttle target ---
        rpm_target = IDLE_RPM + (MAX_RPM - IDLE_RPM) * (throttle / 100.0) ** 1.15
        self.rpm += (rpm_target - self.rpm) * (1.0 - math.exp(-dt / TAU_RPM))
        rpm_n = self.rpm / MAX_RPM

        # --- EGT: rises with power, mild altitude penalty, ambient shift ---
        egt_target = (
            180.0
            + 460.0 * rpm_n
            + 75.0 * (throttle / 100.0) ** 2
            + 0.012 * altitude
            - 0.35 * (ambient_temperature - 15.0)
        )
        self.egt += (egt_target - self.egt) * (1.0 - math.exp(-dt / 2.0))
        egt = float(np.clip(self.egt + r.normal(0.0, 4.0), *EGT_RANGE))

        # --- CHT: follows EGT with slow thermal lag ---
        cht_target = 40.0 + 0.30 * egt + 0.010 * altitude + 0.20 * (ambient_temperature - 15.0)
        self.cht += (cht_target - self.cht) * (1.0 - math.exp(-dt / TAU_CHT))
        cht = float(np.clip(self.cht + r.normal(0.0, 1.5), *CHT_RANGE))

        # --- Oil system ---
        oil_pressure = float(np.clip(0.8 + 3.4 * rpm_n + r.normal(0.0, 0.04), *OIL_P_RANGE))
        oil_temp_target = 55.0 + 28.0 * (throttle / 100.0) + 0.006 * altitude + 0.35 * (ambient_temperature - 15.0)
        self.oil_temperature += (oil_temp_target - self.oil_temperature) * (1.0 - math.exp(-dt / TAU_OILT))
        oil_temperature = float(np.clip(self.oil_temperature + r.normal(0.0, 0.2), *OIL_T_RANGE))

        # --- Fuel flow ---
        fuel_flow = float(np.clip(4.5 + 14.0 * rpm_n * (throttle / 100.0) ** 0.6 + r.normal(0.0, 0.25), *FUEL_RANGE))

        # --- Vibration: base + rpm + throttle-transient bump ---
        throttle_delta = abs(throttle - self._last_throttle)
        self._last_throttle = throttle
        vibration = float(
            np.clip(
                0.22 + 0.40 * rpm_n + 0.35 * min(throttle_delta, 30.0) / 30.0 + r.normal(0.0, 0.05),
                *VIB_RANGE,
            )
        )

        # --- Electrical system ---
        battery_voltage = float(np.clip(27.2 - 1.1 * (throttle / 100.0) - 0.5 * rpm_n + r.normal(0.0, 0.04), *BATT_RANGE))
        alternator_current = float(np.clip(8.0 + 30.0 * rpm_n + r.normal(0.0, 0.5), *ALT_RANGE))

        # --- Injection timing: advances (deg BTDC grows) as rpm falls ---
        injection_timing = float(np.clip(18.0 + 14.0 * (1.0 - rpm_n) + r.normal(0.0, 0.2), *INJ_RANGE))

        return {
            "rpm": round(self.rpm, 1),
            "cht": round(cht, 1),
            "egt": round(egt, 1),
            "oil_pressure": round(oil_pressure, 3),
            "oil_temperature": round(oil_temperature, 1),
            "fuel_flow": round(fuel_flow, 2),
            "vibration_rms": round(vibration, 3),
            "battery_voltage": round(battery_voltage, 2),
            "alternator_current": round(alternator_current, 1),
            "injection_timing": round(injection_timing, 1),
        }


def expected_sensors(operating_point: Dict[str, float]) -> Dict[str, float]:
    """Deterministic expected (healthy) values for residual computation.

    Computed from CONTROL INPUTS ONLY (throttle, altitude, ambient temperature)
    using the same model equations as step(). This is important: expected
    values must not be conditioned on observed sensor readings, otherwise a
    fault that corrupts a sensor would also corrupt its own expected value and
    the residual would cancel out.
    """
    throttle = float(np.clip(operating_point.get("throttle", 55.0), 0.0, 100.0))
    altitude = float(np.clip(operating_point.get("altitude", 1000.0), 0.0, 15000.0))
    ambient = float(np.clip(operating_point.get("ambient_temperature", 15.0), -20.0, 55.0))
    throttle_f = throttle / 100.0
    rpm = IDLE_RPM + (MAX_RPM - IDLE_RPM) * throttle_f ** 1.15
    rpm_n = rpm / MAX_RPM
    egt = 180.0 + 460.0 * rpm_n + 75.0 * throttle_f ** 2 + 0.012 * altitude - 0.35 * (ambient - 15.0)
    return {
        "rpm": rpm,
        "egt": egt,
        "cht": 40.0 + 0.30 * egt + 0.010 * altitude + 0.20 * (ambient - 15.0),
        "oil_pressure": float(np.clip(0.8 + 3.4 * rpm_n, *OIL_P_RANGE)),
        "oil_temperature": 55.0 + 28.0 * throttle_f + 0.006 * altitude + 0.35 * (ambient - 15.0),
        "fuel_flow": float(np.clip(4.5 + 14.0 * rpm_n * throttle_f ** 0.6, *FUEL_RANGE)),
        "vibration_rms": 0.22 + 0.40 * rpm_n,
        "battery_voltage": 27.2 - 1.1 * throttle_f - 0.5 * rpm_n,
        "alternator_current": 8.0 + 30.0 * rpm_n,
        "injection_timing": 18.0 + 14.0 * (1.0 - rpm_n),
    }
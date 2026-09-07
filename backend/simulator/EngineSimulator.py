from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

MissionStep = Dict[str, Any]


class EngineSimulator:
    """Physics-inspired synthetic telemetry generator for demo missions."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self.base_params = {
            "min_rpm": 1000.0,
            "max_rpm": 6000.0,
            "max_alt": 30000.0,
        }

    def _phase_steps(
        self,
        phase: str,
        count: int,
        throttle: Any,
        altitude: Any,
        ambient_temperature: float,
        compute: float,
    ) -> List[MissionStep]:
        steps = []
        for index in range(count):
            fraction = index / max(count - 1, 1)
            throttle_value = throttle(fraction) if callable(throttle) else throttle
            altitude_value = altitude(fraction) if callable(altitude) else altitude
            steps.append({
                "throttle": max(0.0, float(throttle_value) + self.rng.normal(0, 0.35)),
                "altitude": max(0.0, float(altitude_value) + self.rng.normal(0, 20.0)),
                "ambient_temperature": float(ambient_temperature) + self.rng.normal(0, 1.5),
                "mission_phase": phase,
                "compute": float(compute),
            })
        return steps

    def _get_mission_profile(self, profile_name: str = "standard_isr") -> List[MissionStep]:
        if profile_name == "standard_isr":
            return (
                self._phase_steps("Startup", 20, lambda t: 10 + 15 * t, 0, 25, 10)
                + self._phase_steps("Takeoff", 40, lambda t: 65 + 25 * t, lambda t: 500 + 2500 * t, 25, 50)
                + self._phase_steps("Cruise", 80, lambda t: 52 + 4 * np.sin(t * np.pi), lambda t: 12000 + 2000 * np.sin(t * np.pi), 15, 20)
                + self._phase_steps("Descent", 40, lambda t: 40 - 25 * t, lambda t: 15000 - 14500 * t, 20, 10)
                + self._phase_steps("Landing", 20, 5, 500, 25, 1)
            )
        if profile_name == "high_altitude":
            return self._phase_steps("Climb_High", 40, lambda t: 30 + 25 * t, lambda t: 25000 * t, 10, 15) + self._phase_steps("Cruise_High", 60, 32, 25000, 10, 15)
        if profile_name == "hot_weather":
            return self._phase_steps("Takeoff_Hot", 40, lambda t: 45 + 35 * t, lambda t: 100 + 1000 * t, 40, 60) + self._phase_steps("Cruise_Hot", 60, 60, 1200, 40, 30)
        if profile_name == "aggressive":
            return self._phase_steps("Rapid_Accel", 40, lambda t: 20 + 75 * t, lambda t: 1000 * t, 25, 70) + self._phase_steps("Rapid_Decel", 30, lambda t: 95 - 85 * t, 1000, 25, 5)
        raise ValueError(f"Unknown mission profile: {profile_name}")

    def _calculate_telemetry(self, step: MissionStep) -> Dict[str, Any]:
        throttle = float(np.clip(step["throttle"], 0, 100))
        altitude = max(0.0, float(step["altitude"]))
        ambient_temperature = float(step["ambient_temperature"])
        compute = float(step["compute"])
        altitude_factor = max(0.0, 1.0 - altitude / self.base_params["max_alt"])
        rpm = np.clip(1000 + 50 * throttle + 80 * np.cos(altitude / 1000), 1000, 6000)
        cht = 500 + 7 * throttle * altitude_factor
        egt = 600 + 4 * throttle * (0.8 + 0.2 * np.cos(altitude / 1000))
        oil_pressure = np.clip(3 + 4 * (1 - 0.00003 * altitude), 3, 7)
        oil_temperature = np.clip(50 + 0.5 * throttle + 0.05 * ambient_temperature, 50, 100)
        fuel_flow = 5 + 0.45 * throttle
        vibration_rms = 0.5 + 2.5 * (0.5 + 0.5 * np.tanh(compute / 50))
        return {
            "rpm": float(rpm), "cht": float(cht), "egt": float(egt), "oil_pressure": float(oil_pressure),
            "oil_temperature": float(oil_temperature), "fuel_flow": float(fuel_flow), "vibration_rms": float(vibration_rms),
            "battery_voltage": float(27.5 - 0.5 * throttle / 100), "alternator_current": float(10 + 5 * throttle / 100),
            "injection_timing": float(0.1 + 0.02 * throttle / 100), "throttle": throttle, "altitude": altitude,
            "ambient_temperature": ambient_temperature, "mission_phase": step["mission_phase"], "compute": compute,
            "fault_label": "none",
        }

    def simulate_mission(self, mission: Union[str, List[MissionStep]], profile_overrides: Optional[dict] = None) -> str:
        """Return a CSV string for a named profile or explicit mission steps."""
        del profile_overrides
        steps = self._get_mission_profile(mission) if isinstance(mission, str) else mission
        return pd.DataFrame([self._calculate_telemetry(step) for step in steps]).to_csv(index=False)


if __name__ == "__main__":
    print("\n".join(EngineSimulator(seed=7).simulate_mission("standard_isr").splitlines()[:5]))

import pandas as pd
import numpy as np
from typing import List, Dict, Any

class EngineSimulator:
    """
    Core physics-inspired engine model simulator. Generates plausible, healthy telemetry data.
    """
    def __init__(self):
        # Base parameters for plausible range simulation
        self.base_params = {
            'min_rpm': 1000, 'max_rpm': 6000,
            'min_cht': 500, 'max_cht': 1200,
            'min_egt': 600, 'max_egt': 1000,
            'min_oil_pressure': 3.0, 'max_oil_pressure': 7.0,
            'min_oil_temp': 50.0, 'max_oil_temp': 100.0,
            'min_fuel_flow': 5.0, 'max_fuel_flow': 50.0,
            'min_vib_rms': 0.5, 'max_vib_rms': 3.0,
            'min_volt': 24.0, 'max_volt': 28.0,
            'min_alt': 0, 'max_alt': 30000
        }

    def _calculate_telemetry(self, t: float, alt: float, ambt: float, phase: str, compute: float) -> Dict[str, float]:
        """Calculates a single set of telemetry readings."""
        
        # 1. RPM: Scales with throttle and varies with altitude/load.
        rpm = self.base_params['min_rpm'] + (self.base_params['max_rpm'] - self.base_params['min_rpm']) * (t / 100.0) * (1.0 + 0.1 * np.cos(alt / 1000.0))
        rpm = np.clip(rpm, self.base_params['min_rpm'], self.base_params['max_rpm'])

        # 2. Temperatures: High with high throttle and low altitude.
        cht = self.base_params['min_cht'] + (self.base_params['max_cht'] - self.base_params['min_cht']) * (t / 100.0) * (1.0 - alt / self.base_params['max_alt'])
        egt = self.base_params['min_egt'] + (self.base_params['max_egt'] - self.base_params['min_egt']) * (t / 100.0) * (0.8 + 0.2 * np.cos(alt / 1000.0))
        
        # Oil Pressure: Stable, dips slightly with altitude.
        oil_pressure = self.base_params['min_oil_pressure'] + (self.base_params['max_oil_pressure'] - self.base_params['min_oil_pressure']) * (1 - 0.0005 * alt)
        
        # Oil Temperature: Depends on load and altitude.
        oil_temperature = 60.0 + 30.0 * (t / 100.0) + 5.0 * (alt / self.base_params['max_alt'])

        # 3. Consumption & Auxiliary Systems
        # Fuel Flow: Proportional to throttle.
        fuel_flow = self.base_params['min_fuel_flow'] + (self.base_params['max_fuel_flow'] - self.base_params['min_fuel_flow']) * (t / 100.0) * 1.5
        
        # Vibration RMS: Higher during critical maneuvers.
        vibration_rms = self.base_params['min_vib_rms'] + (self.base_params['max_vib_rms'] - self.base_params['min_vib_rms']) * (0.5 + 0.5 * np.tanh(compute / 50.0))

        # Electrical System: Dependent on RPM and load.
        battery_voltage = 24.0 + 0.5 * np.cos(rpm / 1000.0)
        alternator_current = 10.0 + 5.0 * (t / 100.0)
        
        # Injection Timing: Varies with altitude/load.
        injection_timing = 0.1 + 0.05 * np.sin(alt / 1000.0) + 0.02 * (t / 100.0)

        # 4. Final Data Structure
        telemetry = {
            'rpm': rpm,
            'cht': cht,
            'egt': egt,
            'oil_pressure': oil_pressure,
            'oil_temperature': oil_temperature,
            'fuel_flow': fuel_flow,
            'vibration_rms': vibration_rms,
            'battery_voltage': battery_voltage,
            'alternator_current': alternator_current,
            'injection_timing': injection_timing,
            'throttle': t,
            'altitude': alt,
            'ambient_temperature': ambt,
            'mission_phase': phase,
            'compute': compute,
            'fault_label': 'none'
        }
        return telemetry

    def simulate_mission(self, mission_profile: List[Dict[str, Any]]) -> str:
        """
        Runs the simulation for a list of mission steps and generates a CSV string.
        
        Args:
            mission_profile: List of dicts containing mission settings for each step.
        
        Returns:
            A string formatted as CSV.
        """
        all_telemetry = []
        for step in mission_profile:
            telemetry = self._calculate_telemetry(
                t=step['throttle'],
                alt=step['altitude'],
                ambt=step['ambient_temperature'],
                phase=step['mission_phase'],
                compute=step['compute']
            )
            all_telemetry.append(telemetry)
        
        # Convert list of dicts to DataFrame and then to CSV string
        df = pd.DataFrame(all_telemetry)
        
        return df.to_csv(index=False)

if __name__ == '__main__':
    print("--- Running Engine Simulator Example ---")
    
    # Mission Profile: Takeoff -> Cruise -> Descent
    mission_steps = [
        {'throttle': 80.0, 'altitude': 100.0, 'ambient_temperature': 25.0, 'mission_phase': 'Takeoff', 'compute': 50.0},
        {'throttle': 50.0, 'altitude': 10000.0, 'ambient_temperature': 15.0, 'mission_phase': 'Cruise', 'compute': 20.0},
        {'throttle': 20.0, 'altitude': 500.0, 'ambient_temperature': 20.0, 'mission_phase': 'Descent', 'compute': 5.0}
    ]

    simulator = EngineSimulator()
    csv_output = simulator.simulate_mission(mission_steps)

    print("\n[CSV Output Snippet (First 5 lines)]:")
    print("\\n".join(csv_output.splitlines()[:5]))
    print("... (Full CSV generated successfully)")
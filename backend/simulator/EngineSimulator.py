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


  def _get_mission_profile(self, profile_name: str = 'standard_isr') -> List[Dict[str, Any]]:
      """
      Generates a sequence of steps representing a full mission profile.
      This structure is designed to be easily extended for new profiles.
      
      Args:
          profile_name: The name of the mission profile to load.
          
      Returns:
          List[Dict[str, Any]]: A list of dictionaries, where each dict 
                                  represents a simulation step (phase).
      """
      # Initialize noise parameters if not present (using defaults)
      self.noise_params = {
          'throttle': 0.5,
          'alt': 50.0,
          'temp': 5.0
      }
      
      # A helper function to create a noisy step sequence
      def _create_steps(start_throttle: float, start_alt: float, start_ambt: float, phase: str, compute: float, num_steps: int, 
                         fn_throttle=None, fn_alt=None, fn_ambt=None) -> List[Dict[str, Any]]:
          """Generates a sequence of steps for a phase with noise and controlled function mapping."""
          steps = []
          for i in range(num_steps):
              # Calculate core parameters based on time fraction (t)
              t = i / num_steps
              
              # Use provided function or default linear interpolation
              throttle = fn_throttle(t) if fn_throttle else start_throttle * (1 - 0.1 * t)
              alt = fn_alt(t) if fn_alt else start_alt + (start_alt - start_alt) * (1 - 0.1 * t)
              ambt = fn_ambt(t) if fn_ambt else start_ambt
              
              # Apply small noise/variability
              noisy_throttle = max(0.0, throttle + np.random.normal(0, self.noise_params['throttle']))
              noisy_alt = max(0.0, alt + np.random.normal(0, self.noise_params['alt']))
              noisy_ambt = ambt + np.random.normal(0, self.noise_params['temp'])

              steps.append({
                  'throttle': noisy_throttle, 
                  'altitude': noisy_alt, 
                  'ambient_temperature': noisy_ambt, 
                  'mission_phase': phase, 
                  'compute': compute
              })
          return steps

      if profile_name == 'standard_isr':
          # Standard ISR Profile (Ideal/Normal Operation): Takeoff -> Climb -> Cruise -> Descent -> Landing
          steps = []
          
          # 1. Startup (0-500 ft): Low throttle, ground level
          steps.extend(_create_steps(20.0, 0.0, 25.0, 'Startup', 10.0, 50, 
                                      lambda t: 0.1 + 0.9 * t, lambda t: 0.0 + 500.0 * t))
          
          # 2. Takeoff (500-3000 ft): Rapid climb and throttle increase
          steps.extend(_create_steps(80.0, 500.0, 25.0, 'Takeoff', 50.0, 100, 
                                     lambda t: 0.1 + 0.8 * t + 0.1 * np.sin(t*np.pi), 
                                     lambda t: 500.0 + 2500.0 * t))
          
          # 3. Cruise (3000-15000 ft): Stable operation
          steps.extend(_create_steps(50.0, 3000.0, 15.0, 'Cruise', 20.0, 200, 
                                     lambda t: 50.0 + 5.0 * np.sin(t*np.pi/5), 
                                     lambda t: 3000.0 + 2000.0 * np.sin(t*np.pi/10)))
          
          # 4. Descent (15000-500 ft): Gradual decline
          steps.extend(_create_steps(40.0, 15000.0, 20.0, 'Descent', 10.0, 150, 
                                     lambda t: 40.0 * (1 - t/1.0), 
        steps = self._get_mission_profile(profile_name)
        
        if profile_overrides:
            # Apply overrides if provided (e.g., for fault simulation)
            # Implementation for merging overrides would go here
            pass # Placeholder for future fault injection merge logic
        
        # Run simulation step-by-step based on the loaded profile
        all_telemetry = []
        for step in steps:
            telemetry = self._calculate_telemetry(
                t=step['throttle'],
                alt=step['altitude'],
                ambt=step['ambient_temperature'],
                phase=step['mission_phase'],
                compute=step['compute']
            )
            all_telemetry.append(telemetry)
        
        # Convert list of dicts to DataFrame and then to CSV string
    simulator = EngineSimulator()
    # Demonstrating the 'Standard ISR' profile
    profile_name = 'standard_isr'
    csv_output = simulator.simulate_mission(profile_name)
    
    print(f"--- Running Simulator for Profile: {profile_name.upper()} ---")
    
    # Read the generated CSV string into a DataFrame for visualization
    df = pd.read_csv(pd.io.common.StringIO(csv_output))
    
    print(f"\n[CSV Output Snippet (First 5 lines for {profile_name.upper()})]:")
    # Showing the first 5 rows of the resulting DataFrame
    print("\\n".join(df.head(5).astype(str).to_string(index=False)))
    print("\n... (Full CSV generated successfully)")
        df = pd.DataFrame(all_telemetry)
        
        return df.to_csv(index=False)
                                     lambda t: 15000.0 * (1 - t/1.0)))
          
          # 5. Landing/Idle (0-500 ft): Minimum operation
          steps.extend(_create_steps(5.0, 500.0, 25.0, 'Landing', 1.0, 50, 
                                     lambda t: 5.0, lambda t: 500.0))
          
          return steps

      elif profile_name == 'high_altitude':
          # High-Altitude Profile: Low temp, low pressure, minimal activity
          steps = []
          # Climb to 25,000 ft
          steps.extend(_create_steps(30.0, 0.0, 10.0, 'Climb_High', 15.0, 200, 
                                     lambda t: 0.1 + 0.9 * t, lambda t: 0.0 + 25000.0 * t))
          
          # Long cruise at high altitude
          steps.extend(_create_steps(30.0, 25000.0, 10.0, 'Cruise_High', 15.0, 300, 
                                     lambda t: 30.0 + 1.0 * np.sin(t*np.pi/10), 
                                     lambda t: 25000.0))
          return steps

      elif profile_name == 'hot_weather':
          # Hot-Weather Profile: High ambient temp, stressing components
          steps = []
          # Takeoff in hot conditions
          steps.extend(_create_steps(50.0, 100.0, 40.0, 'Takeoff_Hot', 60.0, 150, 
                                     lambda t: 0.1 + 0.8 * t + 0.1 * np.cos(t*np.pi), 
                                     lambda t: 100.0 + 1000.0 * t))
          
          # Cruise in hot conditions
          steps.extend(_create_steps(60.0, 1000.0, 40.0, 'Cruise_Hot', 30.0, 300, 
                                     lambda t: 60.0 + 5.0 * np.cos(t*np.pi/5), 
                                     lambda t: 1000.0 + 500.0 * np.sin(t*np.pi/20)))
          return steps
      
      elif profile_name == 'aggressive':
          # Aggressive Profile: Rapid cycling, high dynamic stress
          steps = []
          # Rapid acceleration phase
          steps.extend(_create_steps(20.0, 0.0, 25.0, 'Rapid_Accel', 70.0, 100, 
                                     lambda t: 0.1 + 0.9 * t + 0.5 * np.sin(t*np.pi), 
                                     lambda t: 0.0 + 1000.0 * t))
          
          # Quick transition/rapid deceleration
          steps.extend(_create_steps(10.0, 1000.0, 25.0, 'Rapid_Decel', 5.0, 50, 
                                     lambda t: 10.0 * (1 - t/1.0), 
                                     lambda t: 1000.0 + 500.0 * np.sin(t*np.pi/5)))
          return steps
      
      else:
          raise ValueError(f"Unknown mission profile: {profile_name}")

  def _get_mission_profile(self, profile_name: str = 'standard_isr') -> List[Dict[str, Any]]:
      """
      Generates a sequence of steps representing a full mission profile.
      This structure is designed to be easily extended for new profiles.
      
      Args:
          profile_name: The name of the mission profile to load.
          
      Returns:
          List[Dict[str, Any]]: A list of dictionaries, where each dict 
                                  represents a simulation step (phase).
      """
      # Define base physical constraints and noise parameters
      self.noise_params = {
          'throttle_noise': 0.5,
          'alt_noise': 50.0,
          'temp_noise': 5.0
      }
      
      # A helper function to create a noisy step
      def create_step(throttle: float, alt: float, ambt: float, phase: str, compute: float, duration: int = 10):
          # Creates a list of dictionary steps for a duration
          steps = []
          for i in range(duration):
              # Add small noise/variability to prevent perfect smoothness
              noisy_throttle = max(0.0, throttle + np.random.normal(0, self.noise_params['throttle_noise']))
              noisy_alt = alt + np.random.normal(0, self.noise_params['alt_noise'])
              noisy_ambt = ambt + np.random.normal(0, self.noise_params['temp_noise'])
              
              steps.append({
                  'throttle': noisy_throttle, 
                  'altitude': max(0.0, noisy_alt), 
                  'ambient_temperature': noisy_ambt, 
                  'mission_phase': phase, 
                  'compute': compute
              })
          return steps

      if profile_name == 'standard_isr':
          # Standard ISR Profile: Takeoff -> Climb -> Cruise (15,000 ft) -> Descent -> Landing
          return []
      elif profile_name == 'high_altitude':
          # High-Altitude Profile: Focus on cold and thin air performance
          return []
      elif profile_name == 'hot_weather':
          # Hot-Weather Profile: High ambient temperature, demanding performance
          return []
      elif profile_name == 'aggressive':
          # Aggressive Profile: Rapid throttle changes, high stress
          return []
      else:
          raise ValueError(f"Unknown mission profile: {profile_name}")

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

    def simulate_mission(self, profile_name: str, profile_overrides: dict = None) -> str:
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
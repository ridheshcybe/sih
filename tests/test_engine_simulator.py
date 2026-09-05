import pandas as pd
import numpy as np
import pytest
from backend.simulator.EngineSimulator import EngineSimulator

@pytest.fixture
def simulator():
    """Fixture to provide a fresh EngineSimulator instance for each test."""
    return EngineSimulator()

def test_simulator_data_structure(simulator: EngineSimulator):
    """Tests the basic structure and CSV output format."""
    # Simple mission profile: Idle -> Takeoff
    mission_steps = [
    # Standard ISR Profile: Idle -> Takeoff
    # Use the profile name and the structure verification is now done by checking specific transitions
    profile_name = 'standard_isr'
    # We use a small number of steps here for quick, structural testing
    mission_steps = simulator.simulate_mission(profile_name, profile_overrides={})
    csv_output = mission_steps
    
    # Read the generated CSV string into a DataFrame for easy validation
    df = pd.read_csv(pd.io.common.StringIO(csv_output))
    
    # 1. Check the number of rows (should match the profile's total steps)
    # We check if the dataframe size is substantial, implying all phases were executed.
    assert len(df) > 100
    
    # 2. Check for required columns
    expected_columns = [
        'rpm', 'cht', 'egt', 'oil_pressure', 'oil_temperature', 'fuel_flow', 
        'vibration_rms', 'battery_voltage', 'alternator_current', 'injection_timing', 
        'throttle', 'altitude', 'ambient_temperature', 'mission_phase', 'compute', 'fault_label'
def test_simulation_plausibility_and_plains(simulator: EngineSimulator):
    """Tests that key values are generally within expected scientific ranges and vary logically across phases."""
    
    # Test the complex, multi-phase standard profile
    profile_name = 'standard_isr'
    csv_output = simulator.simulate_mission(profile_name)
    df = pd.read_csv(pd.io.common.StringIO(csv_output))
    
    # Check 1: Data Integrity and Transitions
    # Ensure all phases are represented and have sufficient data points
    required_phases = ['Startup', 'Takeoff', 'Cruise', 'Descent', 'Landing']
    for phase in required_phases:
        phase_data = df[df['mission_phase'] == phase]
        assert not phase_data.empty, f"Required phase '{phase}' was not generated."
        # Check that data points are stable within a phase
        assert phase_data['throttle'].std() < 10.0 * (1 - (phase == 'Startup') * 0.1)
    
    # Check 2: Scientific trends (e.g., performance metrics)
    
    # Cruise Phase (Steady, High Altitude)
    cruise_row = df[df['mission_phase'] == 'Cruise'].sample(min(5, len(df[df['mission_phase'] == 'Cruise']))).iloc[0]
    # Should be operating efficiently
    assert cruise_row['egt'] > 700.0 and cruise_row['egt'] < 1100.0
    
    # Takeoff Phase (High Power, Low Altitude)
    takeoff_row = df[df['mission_phase'] == 'Takeoff'].sample(min(5, len(df[df['mission_phase'] == 'Takeoff']))).iloc[0]
    # EGT should be high
    assert takeoff_row['egt'] > 800.0
    
    # Idle Phase (Low Power, Ground Level)
    idle_row = df[df['mission_phase'] == 'Landing'].sample(min(5, len(df[df['mission_phase'] == 'Landing']))).iloc[0]
    # EGT should be lowest
    assert idle_row['egt'] < 600.0
    
    # Check 3: Throttle trend (Start low, peak high, end low)
def test_fault_label_integrity(simulator: EngineSimulator):
    """Ensures the fault label remains 'none' when no faults are simulated."""
    
    # Use the standard ISR profile to ensure we are testing a full, valid cycle
    profile_name = 'standard_isr'
    csv_output = simulator.simulate_mission(profile_name)
    df = pd.read_csv(pd.io.common.StringIO(csv_output))
    
    # Verify the fault_label is consistently 'none'
    assert all(df['fault_label'] == 'none'), "Fault label was unexpectedly changed during simulation."
    min_throttle = df['throttle'].min()
    max_throttle = df['throttle'].max()
    
    assert min_throttle < 10.0 and max_throttle > 70.0, "Throttle range indicates faulty profile definition."
    ]
    assert all(col in df.columns for col in expected_columns)
    
    # 3. Check for phase transitions
    # Verify that a phase change occurred (e.g., 'Startup' and 'Cruise' must exist)
    assert 'Startup' in df['mission_phase'].unique()
    assert 'Cruise' in df['mission_phase'].unique()
    
    # Check for a major characteristic change (e.g., altitude must exceed 10000 ft during Cruise)
    cruise_altitude_check = df[df['mission_phase'] == 'Cruise']['altitude'].max()
    assert cruise_altitude_check >= 10000.0
    
    # Check that the simulation ran through a full range of physical states
    assert df['throttle'].min() < 10.0 and df['throttle'].max() > 60.0
    
    return df
        {'throttle': 10.0, 'altitude': 0.0, 'ambient_temperature': 25.0, 'mission_phase': 'Idle', 'compute': 10.0},
        {'throttle': 80.0, 'altitude': 100.0, 'ambient_temperature': 25.0, 'mission_phase': 'Takeoff', 'compute': 50.0}
    ]
    csv_output = simulator.simulate_mission(mission_steps)
    
    # Read the generated CSV string into a DataFrame for easy validation
    df = pd.read_csv(pd.io.common.StringIO(csv_output))
    
    # 1. Check the number of rows (should match the steps)
    assert len(df) == 2
    
    # 2. Check for required columns
    expected_columns = [
        'rpm', 'cht', 'egt', 'oil_pressure', 'oil_temperature', 'fuel_flow', 
        'vibration_rms', 'battery_voltage', 'alternator_current', 'injection_timing', 
        'throttle', 'altitude', 'ambient_temperature', 'mission_phase', 'compute', 'fault_label'
    ]
    assert all(col in df.columns for col in expected_columns)

def test_simulation_plausibility_and_plains(simulator: EngineSimulator):
    """Tests that key values are generally within expected scientific ranges and vary logically."""
    
    # Mission Profile: Full cycle (Takeoff -> Cruise -> Descent -> Idle)
    mission_steps = [
        {'throttle': 95.0, 'altitude': 50.0, 'ambient_temperature': 25.0, 'mission_phase': 'Takeoff', 'compute': 80.0},
        {'throttle': 50.0, 'altitude': 15000.0, 'ambient_temperature': 10.0, 'mission_phase': 'Cruise', 'compute': 20.0},
        {'throttle': 20.0, 'altitude': 800.0, 'ambient_temperature': 20.0, 'mission_phase': 'Descent', 'compute': 5.0},
        {'throttle': 5.0, 'altitude': 0.0, 'ambient_temperature': 25.0, 'mission_phase': 'Idle', 'compute': 1.0},
    ]
    csv_output = simulator.simulate_mission(mission_steps)
    df = pd.read_csv(pd.io.common.StringIO(csv_output))
    
    # We only check the last row (Idle) and the first row (Takeoff) for representative checks
    takeoff_row = df.iloc[0]
    idle_row = df.iloc[-1]

    # Check 1: Takeoff vs Idle for Throttle (Should be high vs low)
    assert takeoff_row['throttle'] > idle_row['throttle'] * 3
    
    # Check 2: EGT and RPM - High at takeoff, lower at idle
    assert takeoff_row['egt'] > idle_row['egt'] * 2
    assert takeoff_row['rpm'] > idle_row['rpm'] * 3
    
    # Check 3: Altitude influence (Should be minimized in Cruise/Descent)
    # Compare altitude (10000) vs ground (0) for a constant throttle (50.0)
    # This requires comparing two specific points, let's manually grab the Cruise and Idle row.
    cruise_row = df[df['mission_phase'] == 'Cruise'].iloc[0]
    idle_row = df[df['mission_phase'] == 'Idle'].iloc[0]
    
    # Check if EGT/CHT/RPM are higher at cruise altitude than at idle altitude (at similar throttle percentage)
    assert cruise_row['egt'] > idle_row['egt']
    
def test_fault_label_integrity(simulator: EngineSimulator):
    """Ensures the fault label remains 'none' when no faults are simulated."""
    mission_steps = [
        {'throttle': 50.0, 'altitude': 10000.0, 'ambient_temperature': 10.0, 'mission_phase': 'Cruise', 'compute': 20.0}
    ]
    csv_output = simulator.simulate_mission(mission_steps)
    df = pd.read_csv(pd.io.common.StringIO(csv_output))
    
    # Verify the fault_label is consistently 'none'
    assert all(df['fault_label'] == 'none')

# Note: To simulate a fault, the simulator would need an additional input/parameter, 
# but for now, we verify the baseline 'none' state as per requirements.
import time
import json
import random
import numpy as np

# --- Constants and Parameters ---
# Nominal Operating Points (Cruise Condition)
NOMINAL_RPM = 3000
NOMINAL_OIL_PRESSURE_PSI = 80
NOMINAL_EGT_C = 650
NOMINAL_FUEL_FLOW_KG = 150
NOMINAL_VIBRATION_RMS = 1.5

# Safety Thresholds
MAX_OIL_PRESSURE = 40
MIN_OIL_PRESSURE = 30
MAX_EGT = 900
MIN_RPM = 1000

# Initial State Tracking
ENGINE_STATE = {
    'rpm': NOMINAL_RPM,
    'oil_pressure': NOMINAL_OIL_PRESSURE_PSI,
    'egt': NOMINAL_EGT_C,
    'fuel_flow': NOMINAL_FUEL_FLOW_KG,
    'vibration_rms': NOMINAL_VIBRATION_RMS
}

# --- Feature 1: Synthetic Engine Telemetry Generation ---

def generate_telemetry(time_step=1):
    """Generates a single step of realistic, structured engine telemetry."""
    global ENGINE_STATE

    # Simulate gradual random noise (Gaussian noise)
    noise = lambda base, std_dev: np.clip(random.gauss(base, std_dev), base - 3*std_dev, base + 3*std_dev)

    # Update base values with noise
    ENGINE_STATE['rpm'] = noise(NOMINAL_RPM, 50)
    ENGINE_STATE['oil_pressure'] = noise(NOMINAL_OIL_PRESSURE_PSI, 2)
    ENGINE_STATE['egt'] = noise(NOMINAL_EGT_C, 5)
    ENGINE_STATE['fuel_flow'] = noise(NOMINAL_FUEL_FLOW_KG, 5)
    ENGINE_STATE['vibration_rms'] = noise(NOMINAL_VIBRATION_RMS, 0.1)

    # Ensure physical boundaries are maintained (basic sanity check)
    ENGINE_STATE['oil_pressure'] = max(NOMINAL_OIL_PRESSURE_PSI - 5, ENGINE_STATE['oil_pressure'])
    ENGINE_STATE['egt'] = max(NOMINAL_EGT_C - 10, ENGINE_STATE['egt'])

    telemetry = {
        'timestamp': time_step * 1, # Assuming 1 second interval
        'RPM': round(ENGINE_STATE['rpm'], 0),
        'Oil_Pressure_PSI': round(ENGINE_STATE['oil_pressure'], 2),
        'EGT_C': round(ENGINE_STATE['egt'], 1),
        'Fuel_Flow_KG': round(ENGINE_STATE['fuel_flow'], 1),
        'Vibration_RMS': round(ENGINE_STATE['vibration_rms'], 2)
    }
    return telemetry

# --- Feature 4 & 5: Expected Values and Residual Calculation ---

def calculate_expected_values(telemetry):
    """
    Calculates expected values based on simple physics models and the current state.
    Residual = |Actual - Expected|.
    """
    # Example 1: Expected Oil Pressure (Ideal gas law approximation)
    # Expected pressure is mostly determined by RPM and ambient conditions.
    # Simple linear model: Baseline + (RPM/NOMINAL_RPM) * Delta
    expected_oil_pressure = NOMINAL_OIL_PRESSURE_PSI + (telemetry['RPM'] / NOMINAL_RPM) * 5
    residual_oil_pressure = abs(telemetry['Oil_Pressure_PSI'] - expected_oil_pressure)

    # Example 2: Expected EGT (Relatively stable, but depends on load)
    # We use a simplified relationship: higher RPM -> higher expected EGT
    expected_egt = NOMINAL_EGT_C + (telemetry['RPM'] - NOMINAL_RPM) * (1.5 / NOMINAL_RPM)
    residual_egt = abs(telemetry['EGT_C'] - expected_egt)

    # Example 3: Expected Fuel Flow (Tied to RPM and load)
    expected_fuel_flow = NOMINAL_FUEL_FLOW_KG + (telemetry['RPM'] / NOMINAL_RPM) * 10
    residual_fuel_flow = abs(telemetry['Fuel_Flow_KG'] - expected_fuel_flow)

    residuals = {
        'oil_pressure': round(residual_oil_pressure, 2),
        'egt': round(residual_egt, 1),
        'fuel_flow': round(residual_fuel_flow, 1)
    }
    return residuals

# --- Feature 6, 7, 8, 9, 10: Core Diagnosis Logic ---

def check_thresholds(telemetry):
    """Feature 7: Checks for immediate safety boundary violations."""
    alerts = []
    if telemetry['Oil_Pressure_PSI'] < MIN_OIL_PRESSURE:
        alerts.append(f"CRITICAL: Oil Pressure ({telemetry['Oil_Pressure_PSI']} PSI) is below minimum safe limit.")
    elif telemetry['Oil_Pressure_PSI'] > MAX_OIL_PRESSURE:
        alerts.append(f"WARNING: Oil Pressure ({telemetry['Oil_Pressure_PSI']} PSI) exceeds maximum safety limit.")
    
    if telemetry['EGT_C'] > MAX_EGT:
        alerts.append(f"CRITICAL: Exhaust Gas Temp ({telemetry['EGT_C']} C) exceeds maximum operational threshold.")
    
    return alerts

def run_anomaly_detection(telemetry, residuals):
    """Feature 8: Identifies statistical outliers using Z-score approximation."""
    # Simplified Anomaly Detection: Flag if residual or metric is unusually high
    anomaly_score = 0
    anomalies = []

    # Check for high residuals (suggests unexpected system behavior)
    if residuals['egt'] > 5.0 and telemetry['EGT_C'] > NOMINAL_EGT_C * 1.1:
        anomalies.append("EGT Residual is high, indicating a significant unmodeled temperature deviation.")
        anomaly_score += 1.5
    
    # Check for unexpected power deviations (Vibration)
    if telemetry['Vibration_RMS'] > NOMINAL_VIBRATION_RMS * 1.5:
        anomalies.append("Vibration RMS is elevated, suggesting potential mechanical imbalance.")
        anomaly_score += 1.0
    
    return anomaly_score, anomalies

def classify_fault(telemetry, residuals, alerts, anomalies):
    """Feature 9: Pinpoints the most likely root cause based on correlated symptoms."""
    faults = []
    
    # 1. Check for the most severe, hard-stop faults (Oil Pressure)
    if "Oil Pressure" in str(alerts) and "CRITICAL" in str(alerts):
        faults.append("Primary Fault: Severe Oil System Failure. IMMEDIATE SHUTDOWN RECOMMENDED.")
        return faults

    # 2. Check for clear component degradation (Injector/Thermal)
    if residuals['egt'] > 3.0 and "EGT" in str(alerts):
        faults.append("Contributing Fault: Degrading combustion efficiency (High EGT Residual). Check fuel metering and injector cluster.")
    
    # 3. Check for combined symptoms (Mechanical)
    if anomalies and "Vibration" in anomalies[0]:
        faults.append("Potential Mechanical Fault: Turbine or Bearings. Requires borescope inspection.")
        
    if not faults:
        faults.append("System nominal. Continue monitoring for subtle trends.")
    
    return faults

def calculate_health_index(residuals, anomalies, critical_alerts):
    """Feature 6: Weighted average of performance metrics."""
    index = 100
    
    # Penalize based on residuals and anomalies
    index -= min(30, residuals['egt'] * 0.2) # EGT is high priority
    index -= min(20, residuals['oil_pressure'] * 0.5) # Oil is critical
    
    # Heavy penalty for critical alerts
    if critical_alerts:
        index -= 35
    
    # Penalty for anomalies
    if anomalies:
        index -= 15
    
    return max(0, round(index, 1))

# --- Main Simulation Loop ---

def run_simulation_cycle(time_step, inject_fault=None):
    """Runs one cycle of data generation and diagnosis."""
    
    # 1. Generate Base Telemetry
    telemetry = generate_telemetry(time_step)

    # 2. Inject Fault (For demonstration purposes)
    if inject_fault == "OIL_LOSS":
        # Simulate rapid oil pressure drop
        telemetry['Oil_Pressure_PSI'] = max(5, telemetry['Oil_Pressure_PSI'] - (time_step * 8))
        # Stabilize other parameters to focus the alarm
        telemetry['EGT_C'] = NOMINAL_EGT_C
    elif inject_fault == "INJECTOR_DEGRADE":
        # Simulate gradual EGT creep (gradual injector issue)
        telemetry['EGT_C'] = NOMINAL_EGT_C + (time_step * 1.5)
        telemetry['Fuel_Flow_KG'] = NOMINAL_FUEL_FLOW_KG + (time_step * 0.5)
        
    # 3. Diagnosis Pipeline
    residuals = calculate_expected_values(telemetry)
    alerts = check_thresholds(telemetry)
    
    # For the fault sequence, we combine detection and anomaly checks
    anomalies_list = []
    if inject_fault:
        anomalies_list.append(f"Simulated Fault: {inject_fault}")
    
    anomaly_score, detected_anomalies = run_anomaly_detection(telemetry, residuals)
    
    # 4. Final Diagnosis
    faults = classify_fault(telemetry, residuals, alerts, detected_anomalies)
    
    # 5. Health Index Calculation
    health_index = calculate_health_index(residuals, detected_anomalies, alerts)
    
    # 6. Assemble Result Payload
    payload = {
        "time_step": time_step,
        "telemetry": telemetry,
        "residuals": residuals,
        "alerts": alerts,
        "anomalies": detected_anomalies,
        "health_index": health_index,
        "fault_classification": faults,
        "anomaly_score": round(anomaly_score, 1)
    }
    
    return payload

if __name__ == "__main__":
    # Example of running the simulation script to test
    print("--- Starting Simulated Engine Telemetry Loop ---")
    
    # Normal cycle (Steps 1-5)
    for i in range(1, 6):
        data = run_simulation_cycle(i)
        print(f"Time {data['time_step']}s | Health Index: {data['health_index']} | Status: Nominal")

    # Failure cycle (Steps 8-11)
    print("\n--- Injecting Injector Degradation Fault (Steps 8-11) ---")
    for i in range(6, 12):
        data = run_simulation_cycle(i, inject_fault="INJECTOR_DEGRADE")
        print(f"Time {data['time_step']}s | Health Index: {data['health_index']} | Status: {data['fault_classification'][0]}")

    # Critical Failure cycle (Steps 12-15)
    print("\n--- Injecting Critical Oil Loss Fault (Steps 12-15) ---")
    for i in range(12, 17):
        data = run_simulation_cycle(i, inject_fault="OIL_LOSS")
        print(f"Time {data['time_step']}s | Health Index: {data['health_index']} | Status: {data['fault_classification'][0]}")
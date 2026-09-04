from flask import Flask, request, jsonify
from backend.data_simulator import run_simulation_cycle, NOMINAL_RPM, NOMINAL_OIL_PRESSURE_PSI, NOMINAL_EGT_C, NOMINAL_FUEL_FLOW_KG, NOMINAL_VIBRATION_RMS, MIN_OIL_PRESSURE, MAX_EGT, NOMINAL_FUEL_FLOW_KG

app = Flask(__name__)

@app.route('/api/run_simulation', methods=['POST'])
def run_simulation():
    """
    Receives mission parameters (e.g., 'stage', 'time_steps') and runs
    the full diagnostic simulation cycle.
    """
    data = request.get_json()
    
    # Determine how many steps to run
    steps_to_run = data.get('time_steps', 10)
    
    # Determine if a specific fault sequence should be run
    # Use simple steps for simulation: 1-5 (Cruise), 6-10 (Degradation), 11-15 (Failure)
    
    # We will simulate a simple degradation profile for demonstration
    fault_sequence = None
    if steps_to_run > 15:
        # Simulate failure mode
        fault_sequence = "OIL_LOSS"
        
    results = []
    
    for i in range(1, steps_to_run + 1):
        inject_fault = None
        
        if i > 5 and i < 12:
            # Injector Degradation (Steps 8-11)
            inject_fault = "INJECTOR_DEGRADE"
        elif i >= 12 and i <= 17:
            # Critical Failure (Steps 12-15)
            inject_fault = "OIL_LOSS"
        
        # Run the core simulation logic
        data_point = run_simulation_cycle(i, inject_fault=inject_fault)
        
        results.append({
            "time_step": data_point['time_step'],
            "telemetry": data_point['telemetry'],
            "health_index": data_point['health_index'],
            "alerts": data_point['alerts'],
            "anomalies": data_point['anomalies'],
            "fault_classification": data_point['fault_classification']
        })
        
    return jsonify(results)

if __name__ == '__main__':
    # Use a specific port to avoid conflicts
    app.run(debug=True, port=5000)
# Synthetic Telemetry Simulator Specification: Aero Piston Engine Digital Twin

This document outlines the requirements, data schema, and example data for a synthetic telemetry simulator designed for an aero piston engine, supporting digital twin capabilities for MALE UAV missions.

## 🚀 PART A — Simulator Requirements

The simulator must adhere to the following functional and technical requirements:

1.  **Telemetry Generation:** Must generate time-series data representing key performance indicators (KPIs) and physical measurements of the aero piston engine.
2.  **Mission Phase Support:** Must support modeling multiple distinct mission phases, including:
    *   Startup (Engine run-up, pre-flight checks)
    *   Takeoff (High thrust, high RPM)
    *   Climb (Increasing altitude and airspeed)
    *   Cruise (Sustained, efficient flight)
    *   Endurance (Low power, long duration)
    *   Descent (Controlled descent)
    *   Landing (Approach, low power)
3.  **Fault Simulation:** Must generate both healthy (nominal) and faulty engine behavior profiles.
4.  **Fault Injection:** Must allow dynamic injection of specific, time-limited faults during a simulated mission run.
5.  **Sampling Rate:** Data must be produced at a configurable sampling rate, supporting ranges from 1 Hz to 10 Hz.
6.  **Reproducibility:** The simulation must be deterministic, requiring the ability to run multiple simulations with the same random seed.
7.  **Output Formats:** Output data must be consumable by the backend system, supporting both:
    *   CSV format (for batch processing/storage)
    *   In-memory format (e.g., message queue feed for real-time processing)
8.  **Computational Constraints:** The simulation must run reliably on standard laptop hardware without requiring specialized hardware accelerators.

## 📋 PART B — Telemetry Schema Definition

The following schema defines the expected fields for each telemetry data point. All ranges are approximations and subject to refinement based on specific engine models.

| Field | Data Type | Unit | Typical Healthy Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `timestamp` | ISO 8601 or Unix Epoch | Seconds/Milliseconds | N/A | Required for sequence analysis. |
| `engine_id` | String | N/A | `ENG-001` | Unique identifier for the specific engine unit. |
| `mission_id` | String | N/A | UUID format | Unique identifier for the overall flight mission. |
| `mission_phase` | Enum/String | N/A | `cruise`, `climb`, `takeoff`, etc. | Current operational phase of the UAV. |
| `throttle` | Float | % (0-100) | 20 - 100 | Engine throttle setting. |
| `rpm` | Float | RPM | 1500 - 3500 | Revolutions per minute. |
| `cht` | Float | °C | 400 - 650 | Cylinder Head Temperature. Critical for thermal management. |
| `egt` | Float | °C | 550 - 850 | Exhaust Gas Temperature. Primary indicator of combustion efficiency. |
| `oil_pressure` | Float | PSI (or bar) | 30 - 70 | Lube oil pressure. Essential for engine health. |
| `oil_temperature` | Float | °C | 60 - 90 | Lube oil temperature. |
| `fuel_flow` | Float | L/s (or kg/h) | 0 - 20 | Rate of fuel consumption. |
| `vibration_rms` | Float | g's (or mm/s) | 0.5 - 3.0 | Root Mean Square acceleration, used for detecting mechanical anomalies. |
| `battery_voltage` | Float | Volts (V) | 24 - 28 | Main power bus voltage. |
| `alternator_current` | Float | Amps (A) | 10 - 80 | Electrical output current. |
| `injection_timing` | Float | Degrees (BTDC) | 10 - 30 | Timing of fuel injector pulse relative to crankshaft. |
| `altitude` | Float | Meters (m) | 0 - 4000 | Current flight altitude. |
| `ambient_temperature` | Float | °C | -10 - 40 | Outside air temperature. |
| `airspeed` | Float | m/s | 10 - 120 | Airspeed. Optional, but highly recommended. |
| `engine_load` | Float | % (0-100) | 20 - 100 | Overall engine mechanical load. Optional/Derived. |
| `fault_label` | String | N/A | `none`, `misfire`, `injector_degradation`, etc. | Qualitative label for the current fault state. |
| `fault_severity` | Float | Scale (0-3) | 0 | Severity index (0 = nominal, 3 = critical failure). |
| `health_index` | Float | Scale (0-1) | 0.8 - 1.0 | Derived measure of overall engine health (1 = perfect). |
| `degradation_level` | Float | % (0-100) | 0 - 100 | Percentage of performance degradation over time. |

## 📊 PART C — Example Synthetic Telemetry Rows

The following examples demonstrate the output structure for three distinct operational scenarios.

### 1. Healthy Cruise Segment
(Stable, optimal operation, low degradation)

| timestamp | engine_id | mission_id | mission_phase | throttle | rpm | cht | egt | oil_pressure | oil_temperature | fuel_flow | vibration_rms | battery_voltage | alternator_current | injection_timing | altitude | ambient_temperature | airspeed | fault_label | fault_severity | health_index | degradation_level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1678886400 | ENG-001 | M-123 | cruise | 75 | 2800 | 580 | 720 | 55 | 75 | 12.5 | 1.8 | 26.1 | 55 | 22 | 2500 | 15 | 70 | none | 0.0 | 0.95 | 15 |

### 2. Mild Injector Degradation Segment
(Slightly increased EGT and reduced Lube Oil Pressure, minor performance loss)

| timestamp | engine_id | mission_id | mission_phase | throttle | rpm | cht | egt | oil_pressure | oil_temperature | fuel_flow | vibration_rms | battery_voltage | alternator_current | injection_timing | altitude | ambient_temperature | airspeed | fault_label | fault_severity | health_index | degradation_level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1678886460 | ENG-001 | M-123 | cruise | 75 | 2750 | 610 | 810 | 45 | 80 | 13.2 | 2.5 | 26.0 | 54 | 23 | 2500 | 16 | 70 | injector_degradation | 1.0 | 0.85 | 35 |

### 3. Overheating Trend Segment
(Rapid rise in CHT and EGT, indicating a potential cooling system issue or high load)

| timestamp | engine_id | mission_id | mission_id | mission_phase | throttle | rpm | cht | egt | oil_pressure | oil_temperature | fuel_flow | vibration_rms | battery_voltage | alternator_current | injection_timing | altitude | ambient_temperature | airspeed | fault_label | fault_severity | health_index | degradation_level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1678886520 | ENG-001 | M-123 | climb | 85 | 3000 | 690 | 950 | 50 | 85 | 18.1 | 3.5 | 25.9 | 52 | 21 | 2450 | 17 | 80 | overheating | 2.5 | 0.75 | 60 |
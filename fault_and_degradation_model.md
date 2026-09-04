# SIH26054 Aero Piston Engine Digital Twin: Fault and Degradation Modeling

This document defines the modeling components for simulating engine faults and component degradation, ensuring a realistic representation of sensor behavior and system physics for the digital twin.

## 🛠️ PART A — Fault Types Analysis

For each fault, the impact on sensor readings, system physics, and time behavior is defined below.

| Fault | Primary Affected Sensors | Secondary Affected Sensors | Typical Residual Patterns | Time Behavior | Severity Scale (0-3) | Lead Time Before "Failure" |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Misfire** | Cylinder pressure/Temp sensors, RPM sensor | Oil Pressure, EGT | Sudden drop in indicated power; correlated drop in specific cylinder readings. | Sudden | 3 | Minutes (if undetected) |
| **Injector Degradation** | Fuel flow sensor, Cylinder pressure/Temp sensors | EGT, Fuel consumption rate | Gradual increase in required fuel flow per cycle; higher-than-expected fuel consumption for target thrust. | Gradual | 2 | Hours to Days |
| **Lubrication Issue** | Oil Pressure sensor, Oil Temperature sensor | Bearing vibration sensors, Oil flow rate | Gradual decline in oil pressure, followed by rapid drop. Increased bearing vibration harmonics. | Gradual to Sudden | 3 | Hours |
| **Overheating** | EGT sensors, Cylinder coolant temperature | Oil Temperature sensor, Exhaust gas flow | Gradual increase in EGT/Coolant Temp beyond steady-state deviation. Potential sudden spikes. | Gradual | 3 | Minutes to Hours |
| **Sensor Drift** | Specific sensor (e.g., EGT, Pressure) | Correlated sensors | Sensor output systematically deviates from physical expectations without system changes (Bias). | Gradual | 1 | Weeks to Months |
| **Sensor Dropout** | Specific sensor | None (Directly affects models relying on it) | Sensor output becomes zero, NaN, or locks at the last value (Stuck-at-value). | Sudden | 2 | N/A |
| **Abnormal Vibration** | Accelerometers (3-axis, multiple points) | Oil Pressure, RPM | Appearance of new frequency harmonics or excessive overall RMS acceleration amplitude. | Gradual | 2 | Hours |
| **Battery/Alternator Degradation**| Voltage/Current sensors | Electronic Load Sensor, Power consumption metrics | Gradual decline in nominal voltage and maximum sustained current output. | Gradual | 2 | Days to Weeks |

***

## 📉 PART B — Degradation Model

The degradation state variable, $D(t)$, is defined as a dimensionless value ranging from $D_{initial}$ (0) to $D_{failure}$ (100).

### State Evolution Equation
The degradation rate is influenced by operational time and cumulative stress. We use a discrete-time update equation:

$$D(t+1) = D(t) + k_{time} \cdot \Delta t + k_{stress} \cdot S_{stress} \cdot \Delta t$$

Where:
*   $D(t+1)$: Degradation state at the next time step.
*   $D(t)$: Degradation state at the current time step.
*   $\Delta t$: Time step (operating interval).
*   $k_{time}$: Base degradation coefficient (accounts for operational hours).
*   $k_{stress}$: Stress sensitivity coefficient.
*   $S_{stress}$: Cumulative stress index for the current time step.

**Stress Index ($S_{stress}$):**
$$S_{stress} = w_{CHT} \cdot \max(0, CHT - CHT_{nom}) + w_{EGT} \cdot \max(0, EGT - EGT_{nom}) + w_{Alt} \cdot \max(0, | \Delta \text{Throttle} |)$$
*   $CHT_{nom}, EGT_{nom}$: Nominal thresholds.
*   $w_{CHT}, w_{EGT}, w_{Alt}$: Weighting factors defining the relative importance of different stresses.

### Degradation Effects
Degradation ($D$) is mapped to core engine parameters as follows:

1.  **Expected Oil Pressure ($P_{oil}$):**
    $$P_{oil}(D) = P_{oil, nom} \cdot \left(1 - \frac{\alpha_P \cdot D}{100}\right)$$
    *   *Effect:* As $D$ increases, the predicted oil pressure declines due to internal seal/bearing wear (e.g., $\alpha_P=0.002$).
2.  **Expected Vibration ($\text{Vib}$):**
    $$\text{Vib}(D) = \text{Vib}_{nom} \cdot \left(1 + \beta_{vib} \cdot \tanh\left(\frac{D}{D_{Vib}}\right)\right)$$
    *   *Effect:* Vibration increases non-linearly and approaches a plateau as $D$ increases.
3.  **Expected Fuel Efficiency ($\eta_{fuel}$):**
    $$\eta_{fuel}(D) = \eta_{fuel, nom} \cdot \left(1 - \frac{\alpha_F \cdot D}{100}\right)$$
    *   *Effect:* Efficiency degrades linearly due to internal leakage/wear.
4.  **Safety Margins ($\text{SM}$):**
    $$\text{SM}(D) = \text{SM}_{nom} \cdot \left(1 - \alpha_{SM} \cdot \frac{D}{100}\right)$$
    *   *Effect:* Safety margins (e.g., $\text{SM}_{CHT}$) are predicted to shrink proportionally to degradation.

***

## ⚙️ PART C — Fault Injection Interface

Fault injection will be managed by defining a set of structured commands and using a small JSON schema for payload delivery.

### Fault Injection Structure
Each fault injection command must specify:
*   **Fault ID:** Unique identifier (e.g., `FAULT_MISFIRE_CYL_3`).
*   **Start Time:** Simulation time of failure initiation.
*   **Duration/End Time:** Time at which the fault is expected to resolve or the simulation ends.
*   **Severity:** Impact magnitude (e.g., `LOW`, `MEDIUM`, `HIGH`).
*   **Affected Sensors:** List of sensors whose output is compromised.
*   **Modification Rule:** The physics/sensor modification equation.

### JSON Schema for Fault Injection Commands

```json
{
  "fault_id": "string",
  "start_time": "float",
  "end_time": "float",
  "severity": "string",
  "affected_sensors": ["string"],
  "modification_rule": {
    "parameter": "string",
    "rule_type": "string",  // e.g., 'multiplier', 'offset', 'time_decay'
    "value": "number",
    "parameters": {
      // Additional parameters based on rule_type (e.g., 'k', 't_half')
    }
  }
}
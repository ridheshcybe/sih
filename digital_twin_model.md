# Aero Piston Engine Digital Twin Model Specification

This document outlines the design and expected-value calculation methods for a simplified, physics-inspired digital twin model of an aero piston engine.

**DISCLAIMER:** This model is intended purely for demonstration, anomaly detection, and educational purposes. It is **NOT** a certified engine model and should not be used for critical operational decision-making.

## Part A — Modeling Assumptions

The following assumptions are made to simplify the complex real-world physics of engine operation, allowing for the creation of a computationally tractable model.

1.  **Steady-state approximations for cruise:** During steady-state flight conditions, major engine variables (e.g., pressure ratio, turbine temperature) are assumed to reach an equilibrium state, allowing simplified algebraic relationships.
2.  **Quasi-steady relationships for climb/descent:** Changes in flight regime (climb or descent) are modeled using simplified first-order or piecewise functions that approximate the rate of change of key variables, rather than full thermodynamic cycle simulations.
3.  **Empirical coefficients tuned for synthetic data:** Many relationships rely on empirically derived coefficients ($\beta$, $\gamma$, etc.) tuned against a synthetic data set representative of typical flight envelopes. These coefficients are constants for the scope of this model.
4.  **Not a certified engine model:** The model intentionally bypasses the complexity and rigor required for certification, focusing solely on functional relationships for real-time anomaly detection and health monitoring.

---

## Part B — Expected-Value Equations (Simulation Equations)

These equations provide simplified, expected relationships for core engine sensors. They are pseudocode/formulas and should be implemented in a language like Python.

### 1. Expected Exhaust Gas Temperature (EGT)
EGT is generally proportional to the turbine inlet temperature and inversely related to flow conditions.

**Simplified Formula:**
$$EGT_{exp} = f(\text{RPM}, \text{Throttle}, \rho, T_{amb}, \text{Load}) = C_1 \cdot \frac{\text{RPM} \cdot \text{Throttle} \cdot \text{Load}}{T_{amb} \cdot \rho} + C_{offset}$$

*   **Terms:**
    *   $\text{RPM}$: Engine speed (proxy for power output).
    *   $\text{Throttle}$: Normalized throttle setting (0 to 1).
    *   $\rho$: Air density at altitude ($\text{Altitude}/\text{air density}$).
    *   $T_{amb}$: Ambient temperature.
    *   $\text{Load}$: Engine load factor (normalized).
    *   $C_1, C_{offset}$: Empirically derived coefficients.

*   **Fault/Degradation:**
    *   *Increased fuel flow or combustion issues:* $C_{offset}$ or $C_1$ may increase, leading to higher predicted EGT at constant operating points.
    *   *Clogging/fouling:* The dependence on $\text{Throttle}$ might become non-linear or exhibit a negative offset, decreasing the expected EGT for a given throttle.

### 2. Expected Cylinder Head Temperature (CHT)
CHT is primarily affected by the cooling airflow and operational history (EGT).

**Simplified Formula (Piecewise):**
$$CHT_{exp} = f(\text{EGT}, \text{RPM}, \text{CoolFlow}, T_{amb}) = \text{max}(\text{base\_CHT}, \text{EGT} \cdot \text{CoolFlow} \cdot \gamma) + \text{correction}(T_{amb})$$

*   **Terms:**
    *   $\text{EGT}$: Expected EGT (input from Eq 1).
    *   $\text{CoolFlow}$: Cooling airflow (function of airspeed and altitude).
    *   $T_{amb}$: Ambient temperature.
    *   $\gamma$: Cooling efficiency coefficient.
    *   $\text{base\_CHT}$: Minimum operating temperature threshold.

*   **Fault/Degradation:**
    *   *Decreased $\text{CoolFlow}$ (clogging):* The $\text{CHT}_{exp}$ increases dramatically for a given set of inputs, predicting a high risk of overheating.
    *   *Increased $\text{EGT}$:* Increases the temperature gradient, leading to higher predicted $\text{CHT}_{exp}$.

### 3. Expected Oil Pressure ($P_{oil}$)
Oil pressure depends on rotational speed and mechanical losses, which scale with speed.

**Simplified Formula:**
$$P_{oil\_exp} = f(\text{RPM}, T_{oil}, \text{Wear}) = P_{base} + K_1 \cdot \text{RPM} - K_2 \cdot (T_{oil} - T_{ref}) - K_3 \cdot \text{Wear}$$

*   **Terms:**
    *   $P_{base}$: Base pressure (at zero RPM).
    *   $\text{RPM}$: Engine speed.
    *   $T_{oil}$: Measured oil temperature.
    *   $\text{Wear}$: Engine degradation/wear factor (0 to 1).
    *   $K_1, K_2, K_3$: Empirical constants.

*   **Fault/Degradation:**
    *   *Seal degradation or increased wear:* $\text{Wear}$ increases, causing $P_{oil\_exp}$ to decrease faster than expected for the given RPM.
    *   *Low oil viscosity/temperature:* If $T_{oil}$ deviates from $T_{ref}$, $P_{oil\_exp}$ will be altered by the temperature correction term.

### 4. Expected Fuel Flow ($\text{FF}$)
Fuel flow is directly tied to engine thrust and efficiency factors.

**Simplified Formula:**
$$\text{FF}_{exp} = f(\text{RPM}, \text{Throttle}, \text{Altitude}, \text{Efficiency}) = C_2 \cdot \text{RPM} \cdot \text{Throttle} \cdot \text{Altitude\_factor} / \text{Efficiency}$$

*   **Terms:**
    *   $C_2$: Overall conversion efficiency constant.
    *   $\text{RPM}$: Engine speed.
    *   $\text{Throttle}$: Normalized throttle setting.
    *   $\text{Altitude\_factor}$: Factor accounting for air density changes.
    *   $\text{Efficiency}$: Engine efficiency factor (0 to 1).

*   **Fault/Degradation:**
    *   *Decreased combustion efficiency:* $\text{Efficiency}$ decreases, requiring a higher $\text{FF}_{exp}$ to maintain the same $\text{RPM}$/$\text{Throttle}$ setting, which may lead to an actual fuel-flow/thrust mismatch.
    *   *Fuel system leak:* The relationship becomes unstable, causing $\text{FF}_{exp}$ to be consistently higher than expected for the observed $\text{RPM}$/$\text{Throttle}$.

### 5. Expected Vibration RMS ($\text{Vib}_{exp}$)
Vibration is sensitive to speed imbalances and combustion quality.

**Simplified Formula:**
$$\text{Vib}_{exp} = f(\text{RPM}, \text{Load}, \text{CombustionQuality}, \text{Degr}) = C_3 \cdot \text{RPM}^{2} \cdot \text{Load} \cdot (1 + D \cdot \text{CombustionQuality}) + \text{Vib\_base}$$

*   **Terms:**
    *   $C_3$: Vibration scaling constant.
    *   $\text{RPM}$: Engine speed (square dependence).
    *   $\text{Load}$: Engine load factor.
    *   $\text{CombustionQuality}$: Indicator derived from stoichiometry or knock sensors.
    *   $\text{Degr}$: Overall engine degradation factor (0 to 1).
    *   $\text{Vib\_base}$: Baseline vibration.

*   **Fault/Degradation:**
    *   *Rotor imbalance/mechanical failure:* The dependence on $\text{RPM}^2$ becomes disproportionately large, showing a sharp, non-linear increase in $\text{Vib}_{exp}$ at operational speeds.
    *   *Poor combustion:* If $\text{CombustionQuality}$ drops, the predicted $\text{Vib}_{exp}$ increases due to increased cyclic stress.

---

## Part C — Residual Calculation and Usage

The digital twin relies on calculating the difference between the observed sensor reading ($\text{Observed}$) and the model's prediction ($\text{Expected}$).

### Definitions:
1.  **Residual ($R$):** The raw difference between the observed reading and the expected reading.
    $$R = \text{Observed} - \text{Expected}$$
2.  **Normalized Residual ($R_{norm}$):** The residual normalized by the expected operating range (the expected range of the sensor during normal operation, $\text{ExpectedRange}$). This allows residuals from different sensors (e.g., EGT in K vs. Oil Pressure in PSI) to be compared dimensionlessly.
    $$R_{norm} = \frac{R}{\text{ExpectedRange}}$$

### Combined Metrics:
A combined health metric, such as the Root Mean Square (RMS) of the key residuals, provides a single, aggregated indicator of engine health.

$$\text{HealthIndex} = \sqrt{\sum_{i=1}^{N} (R_{norm, i})^2 \cdot W_i}$$
Where $N$ is the number of monitored sensors, and $W_i$ are sensor-specific weighting factors (e.g., weighting EGT higher than $P_{oil}$ if EGT is more critical).

### Usage in Anomaly Detection and Fault Diagnosis:

*   **Anomaly Detection:** The system monitors the magnitude and temporal pattern of $R_{norm}$. A sudden, sustained spike in $R_{norm}$ (e.g., $R_{norm} > 3\sigma$ where $\sigma$ is the expected standard deviation) signals an immediate anomaly, indicating a physical state the model cannot explain.
*   **Fault Diagnosis:** Specific residual patterns map to known failure modes:
    *   $\text{High } R_{norm} \text{ for } P_{oil}$ vs. $\text{Low } \text{RPM}$: Suggests a potential seal failure or lubrication issue.
    *   $\text{High } R_{norm} \text{ for } \text{CHT}$ that correlates with $\text{Low CoolFlow}$: Indicates fouling or blockage in the cooling system.
    *   Systematic increase in $\text{HealthIndex}$ over time: Suggests gradual engine degradation (e.g., turbine blade erosion, increased friction).
*   **Health Index Computation:** The $\text{HealthIndex}$ provides a single score that trends over time. A downward trend indicates declining engine health, allowing for proactive maintenance scheduling.

This model provides a comprehensive, simplified framework for digital twin development.
</write_to_file>
<task_progress>
- [x] Set up task structure and initial documentation in digital_twin_model.md
- [ ] Define core functional equations (Part B)
- [ ] Define residual calculation and usage (Part C)
- [ ] Finalize and complete the document
</task_progress>
</task_progress>
<execute_command>
<command>echo "Initial task progress checklist updated."</command>
<requires_approval>false</requires_approval>
</execute_command>
<task_progress>
- [x] Set up task structure and initial documentation in digital_twin_model.md
- [ ] Define core functional equations (Part B)
- [ ] Define residual calculation and usage (Part C)
- [ ] Finalize and complete the document
</task_progress>
# Aero Piston Engine Digital Twin Model Design

This document outlines a simplified, physics-inspired model designed to compute expected sensor values for an aero piston engine. This model is intended *only* for demonstration, anomaly detection, and general health monitoring, and **is not a certified, flight-ready engine model.**

***

## ⚙️ PART A — Modeling Assumptions

To simplify the complexity of a real engine system, the following assumptions are made:

1.  **Steady-State Approximations:** The model assumes that the engine operates at steady-state conditions (e.g., constant altitude cruise) for the calculation of nominal parameters. Transient changes are handled by quasi-steady relationships.
2.  **Quasi-Steady Relationships:** For dynamic phases like climb or descent, relationships are derived from quasi-steady assumptions, meaning the change in a state variable (like EGT) is modeled as a function of the current state and rate of change.
3.  **Empirical Coefficients:** Many relationships rely on simplified, empirical coefficients (e.g., $\text{Coeff}_{EGT}$, $\text{Coeff}_{PF}$) tuned for synthetic data generation and feasibility in a proof-of-concept system.
4.  **Purpose Limitation:** The model is explicitly for demonstration and anomaly detection/fault diagnosis (Digital Twin Lite) and must not be used for certification or critical flight operations.

***

## 📐 PART B — Expected-Value Equations (Pseudocode & Formulas)

The following equations provide simplified, simplified representations for key sensor outputs.

### 1. Expected Exhaust Gas Temperature (EGT)

EGT is fundamentally determined by the efficiency of combustion, which depends on the incoming air mass flow (related to Altitude and $\text{T}_{\text{ambient}}$) and the overall energy input (related to Throttle/Load).

**Formula (Simplified):**
$$\text{EGT}_{\text{expected}} \approx \text{EGT}_{\text{base}} + \text{Coeff}_{\text{RPM}} \cdot \text{RPM} + \text{Coeff}_{\text{Throttle}} \cdot \text{Throttle} + \text{Coeff}_{\text{Altitude}} \cdot \left(1 - \frac{P_{\text{alt}}}{P_{\text{sea}}}\right) + \text{Noise}$$

**Explanation of Terms:**
*   **$\text{EGT}_{\text{base}}$:** Baseline EGT at minimum power/idle (Empirical constant).
*   **$\text{RPM}$:** Rotations per Minute (Directly influences rotational kinetic energy).
*   **$\text{Throttle}$:** Engine load percentage (A primary indicator of commanded power).
*   **$P_{\text{alt}} / P_{\text{sea}}$:** Altitude pressure ratio (Lower pressure increases engine efficiency per unit mass, impacting EGT).
*   **$\text{Noise}$:** Stochastic/Process noise term (Typically Gaussian $\mathcal{N}(0, \sigma^2)$).

**Degradation Impact:**
*   **Failure/Degradation:** Fouling on the turbine blades or reduced fuel efficiency will cause the $\text{Coeff}_{\text{EGT}}$ to increase (or the $\text{EGT}_{\text{base}}$ to shift up) for a given power setting, leading to *higher* expected EGT.

### 2. Expected Cylinder Head Temperature (CHT)

CHT is primarily a function of cooling air flow and the core temperature, which is affected by the EGT and RPM.

**Formula (Pseudocode/Piecewise):**
$$\text{CHT}_{\text{expected}} = \text{CHT}_{\text{base}} + \left( \frac{\text{EGT}_{\text{expected}}}{\text{Coeff}_{\text{CHT\_EGT}}} \right) \cdot \frac{1}{\text{CoolingAirFlow}} + \text{Corr}(\text{AmbientTemp}, \text{AirSpeed})$$

**Explanation of Terms:**
*   **$\text{CHT}_{\text{base}}$:** Baseline CHT (Empirical constant).
*   **$\text{EGT}_{\text{expected}}$:** Expected EGT (Used as a proxy for core temperature).
*   **$\text{CoolingAirFlow}$:** Calculated function of $\text{AirSpeed}$ and $\text{Altitude}$ (Lower airflow increases heat soak).
*   **$\text{Corr}(\dots)$:** Correction factor based on ambient conditions (e.g., lower ambient temperature might increase the temperature gradient).

**Degradation Impact:**
*   **Failure/Degradation:** Partial blockage or reduced cooling airflow ($\text{CoolingAirFlow}$ decreases) due to component wear or debris will cause the expected CHT to *increase* significantly, even if EGT remains stable.

### 3. Expected Oil Pressure ($\text{OP}$)

Oil pressure is dominated by rotational speed (RPM) and component lubrication state.

**Formula (Simplified):**
$$\text{OP}_{\text{expected}} = \text{OP}_{\text{min}} + \text{Coeff}_{\text{RPM}} \cdot \text{RPM} - \text{Coeff}_{\text{OilTemp}} \cdot (\text{OilTemp} - \text{T}_{\text{ref}}) - \text{Coeff}_{\text{Wear}} \cdot \text{WearFactor}$$

**Explanation of Terms:**
*   **$\text{OP}_{\text{min}}$:** Minimum baseline oil pressure at idle.
*   **$\text{RPM}$:** Rotations per Minute (Increases pressure due to higher mechanical load).
*   **$\text{OilTemp}$:** Oil Temperature (Higher temperature lowers oil viscosity, thus lowering pressure).
*   **$\text{WearFactor}$:** An integrated measure of engine wear (e.g., piston ring clearance increase).

**Degradation Impact:**
*   **Failure/Degradation:** Increased wear ($\text{WearFactor}$ increases) will cause the expected $\text{OP}$ to decrease over time, potentially dropping below the minimum safe operating pressure, even at nominal RPMs.

### 4. Expected Fuel Flow ($\text{FF}$)

Fuel flow is primarily driven by the power required, modeled by a relationship with RPM and Throttle, scaled by atmospheric density.

**Formula (Simplified):**
$$\text{FF}_{\text{expected}} \approx \text{FF}_{\text{idle}} + \text{Coeff}_{\text{P}} \cdot \text{Power} \cdot \text{AltitudeDensityFactor}$$
Where $\text{Power} \approx \text{RPM} \cdot \text{Throttle}$.

**Explanation of Terms:**
*   **$\text{FF}_{\text{idle}}$:** Idle fuel flow (Base consumption).
*   **$\text{Power}$:** Proxy for demanded power ($\text{RPM} \cdot \text{Throttle}$).
*   **$\text{AltitudeDensityFactor}$:** Scaling factor based on air density (less dense air requires more fuel energy per unit mass flow, but the overall relationship is complex, modeled simply here).

**Degradation Impact:**
*   **Failure/Degradation:** Reduced combustion efficiency (due to fouling or injectors) will cause the $\text{FF}$ to *increase* relative to the expected power output for a given $\text{RPM}$ and $\text{Throttle}$.

### 5. Expected Vibration RMS

Vibration Root Mean Square (RMS) is highly sensitive to rotational imbalances and combustion irregularities.

**Formula (Pseudocode/Piecewise):**
$$\text{Vibe}_{\text{expected}} = \text{Vibe}_{\text{idle}} + \text{Coeff}_{\text{Load}} \cdot \text{Load}^{2} + \text{Coeff}_{\text{Combustion}} \cdot \text{CombustionQuality}$$

**Explanation of Terms:**
*   **$\text{Vibe}_{\text{idle}}$:** Baseline vibration at idle.
*   **$\text{Load}$:** Engine Load (Vibration scales non-linearly with power output).
*   **$\text{CombustionQuality}$:** Indicator of flame stability and combustion completeness (Poor combustion increases harmonic vibration).

**Degradation Impact:**
*   **Failure/Degradation:** Changes in engine balance (imbalance mass or bearing wear) increase the constant base vibration ($\text{Vibe}_{\text{idle}}$ increase). Decreased combustion quality (e.g., fouled injectors) increases the $\text{CombustionQuality}$ term, leading to higher $\text{Vibe}_{\text{expected}}$.

***

## 📊 PART C — Residual Calculation

### 1. Definitions
*   **Residual ($\text{R}$):** The raw deviation between what was measured and what was expected.
    $$\text{R}_{\text{EGT}} = \text{EGT}_{\text{observed}} - \text{EGT}_{\text{expected}}$$
*   **Normalized Residual ($\text{R}_{\text{norm}}$):** The raw residual normalized by the expected operational range, providing a unitless indicator of magnitude.
    $$\text{R}_{\text{norm}} = \frac{\text{R}_{\text{observed}}}{\text{ExpectedRange}}$$
    (Example: $\text{ExpectedRange}$ for EGT might be $[800^{\circ}\text{C}, 1200^{\circ}\text{C}]$).

### 2. Combined Metrics
A single, comprehensive metric, such as the Root Mean Square (RMS) of the normalized residuals for the key parameters, can be used:

$$\text{HealthIndex} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (\text{R}_{\text{norm}, i})^2}$$
*Where $N$ is the number of key monitored parameters.*

### 3. Usage of Residuals

| Application | Detection Method | Interpretation |
| :--- | :--- | :--- |
| **Anomaly Detection** | Detect sudden, large spikes or dips in $\text{R}_{\text{norm}}$. | Large deviations (outside $\text{Mean} \pm 3\sigma$) suggest an unexpected operational event (e.g., foreign object damage, sudden altitude change). |
| **Fault Diagnosis** | Monitor the *pattern* of elevated residuals across multiple parameters. | A persistently high $\text{R}_{\text{norm}}$ for $\text{OP}$ combined with a high $\text{R}_{\text{norm}}$ for $\text{CHT}$ points toward specific component failure (e.g., degraded lubrication, cooling system fault). |
| **Health Index Computation** | Track the trend of the $\text{HealthIndex}$ over time. | A steadily increasing $\text{HealthIndex}$ indicates systemic degradation (e.g., cumulative engine wear, fouling), signaling preventative maintenance is required before hard failure. |
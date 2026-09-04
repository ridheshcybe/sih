# Aero Piston Engine Digital Twin Architecture

## Objective: Core State Representation Definition

This document defines the core data structures (state vectors, sensor observations, and derived variables) necessary for the digital twin simulation and monitoring system (SIH26054).

---

### PART A — Engine State Vector

The Engine State Vector ($\mathbf{S}_{eng}$) captures the physical and operational state of the engine at any given time.

| Field | Purpose |
| :--- | :--- |
| **Engine ID** | Unique identifier for the physical engine unit. |
| **Mission ID** | Unique identifier for the overall flight mission. |
| **Timestamp** | Time of measurement or calculation (epoch time). |
| **Mission Phase** | Categorical phase of flight (startup, takeoff, climb, cruise, endurance, descent, landing). |
| **Throttle Setting** | Normalized throttle input (0.0 to 1.0). |
| **Engine Load** | Ratio of current power output to maximum rated power (0.0 to 1.0). |
| **Altitude** | Vertical height above sea level (meters/feet). |
| **Ambient Temperature** | Local atmospheric temperature ($\text{^\circ C}$ or $\text{^\circ F}$). |
| **Ambient Pressure** | Local atmospheric pressure (kPa or $\text{inHg}$). |
| **Airspeed** | Aircraft speed relative to the air (m/s or $\text{knots}$). |
| **Control Inputs: Throttle Command** | Commanded normalized throttle value from the flight controller. |
| **Control Inputs: Fuel Mixture** | Ratio of fuel to air supplied to the cylinders (e.g., 0.9 to 1.2). |
| **Control Inputs: Propeller Pitch** | Current fixed or variable pitch of the propeller blades (degrees/radians). |

---

### PART B — Sensor Observation Vector

The Sensor Observation Vector ($\mathbf{O}_{sens}$) aggregates all measured physical parameters.

| Sensor | Unit | Typical Healthy Range | Failure Mode Examples |
| :--- | :--- | :--- | :--- |
| **RPM** | $\text{rpm}$ | $0 - 30000$ (Operational range) | Dropout (zero reading), Stuck Value (constant value), Noise (high frequency jitter). |
| **CHT** | $\text{^\circ C}$ | $450 - 650$ | Drift (slow change over time), Stuck Value (due to sensor failure). |
| **EGT** | $\text{^\circ C}$ | $600 - 900$ | Dropout, Noise, Illegal Value (outside physical bounds). |
| **Oil Pressure** | $\text{kPa}$ | $300 - 600$ | Stuck Value, Drift (slow loss of pressure). |
| **Oil Temperature** | $\text{^\circ C}$ | $50 - 120$ | Dropout, Stuck Value (frozen reading). |
| **Fuel Flow** | $\text{kg/hr}$ | $0 - 500$ (Depends on engine size) | Dropout, Stuck Value (if valve is fully open/closed). |
| **Vibration** | $\text{mm/s}$ (RMS) | $0 - 5$ | Noise, Drift, Stuck Value (due to sensor disconnection). |
| **Battery Voltage** | $\text{V}$ | $24 - 28$ | Dropout, Drift (slow decline due to battery degradation). |
| **Alternator Current** | $\text{A}$ | $50 - 150$ | Dropout, Stuck Value (zero current when running). |
| **Injection Timing** | $\text{degrees BTDC}$ | $5 - 20$ (Engine specific) | Dropout, Stuck Value (e.g., locked to a default value). |
| **Manifold Pressure** | $\text{kPa}$ | $100 - 500$ | Dropout, Stuck Value. |
| **Fuel Remaining** | $\text{liters}$ | $0 - 50$ | Dropout (transient sensor failure). |

---

### PART C — Derived and Latent Variables

These variables are not directly measured but are calculated using physics models and machine learning estimates, providing insight into the engine's health and performance.

| Variable | Description | Use in Physics Layer | Use in ML Layer |
| :--- | :--- | :--- | :--- |
| **Expected CHT** | CHT predicted based on $\mathbf{S}_{eng}$ and mission phase. | Used for real-time constraint checking and identifying immediate overheating risk. | Input feature for predicting Remaining Useful Life (RUL) and correlating with degradation models. |
| **Expected EGT** | EGT predicted based on throttle, fuel, and airspeed. | Used to model thermodynamic efficiency and predict component wear rates. | Used to train models on healthy operating envelope boundaries and detect deviations from optimal performance. |
| **Expected Oil Pressure** | Oil pressure modeled based on RPM and oil temperature. | Used for calculating lubrication efficiency and diagnosing pump/bearing wear. | Acts as a primary feature for fault classification (e.g., pump failure, internal leak). |
| **Expected Fuel Flow** | Fuel flow predicted based on required power and air density. | Used for fuel efficiency monitoring and validating fuel system performance. | Used to detect leaks or inefficiencies (e.g., incorrect mixing ratio). |
| **Expected Vibration Baseline** | Baseline vibration signature (RMS/FFT) expected for current operating conditions. | Used as a dynamic reference point for structural integrity monitoring. | Input feature for condition-based monitoring and identifying changes in component balance/health. |
| **Sensor Residuals** | $(\mathbf{O}_{sens} - \text{Expected Value})$. Measures the deviation of measured data from the physical model's prediction. | Key diagnostic tool. Large residuals pinpoint where the physical model fails (e.g., non-linear component failure). | Input for outlier detection and anomaly scoring. Residual patterns can map directly to fault types. |
| **Health State** | Categorical assessment (Healthy, Degraded, Faulty). | Triggers operational alerts and shifts the control logic to protective modes. | The primary output variable for supervised fault classification models. |
| **Degradation Level** | Quantitative measure (0-100%) of overall engine performance loss relative to factory new. | Used to adjust control gain and limit maximum allowable operating points. | The target variable for Regression models (predicting time-to-failure). |
| **Fault State** | Specific fault classification (none, misfire, injector, lubrication, overheating, sensor fault, etc.). | Determines the severity and recommended mitigation action (e.g., reduce power, shut down). | The primary output for the fault detection module, classifying the source of the deviation. |
| **Sensor Confidence** | Confidence score (0-1) in the raw measurement data, calculated from internal checks. | Used to weight sensor inputs. Low confidence suggests relying more on the physics model. | Used to weight feature vectors in the ML layer, effectively masking unreliable data points. |
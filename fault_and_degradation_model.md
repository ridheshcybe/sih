# Remaining Useful Life (RUL) and Degradation Estimation Approach

This document defines a credible Remaining Useful Life (RUL) and degradation estimation approach for the prototype aero piston engine digital twin, suitable for simulation and synthetic data analysis.

## PART A — RUL Definition

### Definition
For this digital twin prototype, RUL is defined as the **Number of Missions** until a defined failure threshold is reached.

*   **Primary Definition:** Missions (count of engine operating cycles or flights).
*   **Alternative:** Hours of operation (used if mission profiles are highly variable).
*   **Secondary:** Percentage of life consumed (useful for reporting but not predictive).

### Suitability for Synthetic Data
Defining RUL by **Number of Missions** is ideal for synthetic data because degradation is typically modeled as a discrete process. Each mission represents a defined operating cycle (load case, run time) that contributes to cumulative wear. This provides a measurable, integer step that aligns naturally with the run-to-failure simulation methodology, making the RUL estimation process straightforward and deterministic within the model's parameters.

---

## PART B — Estimation Approaches

We describe three potential RUL estimation methods and select the primary and fallback approaches for the hackathon.

### 1. Synthetic Degradation-based RUL (Time-to-Threshold)
This approach models a specific degradation feature (e.g., cylinder bore wear, component temperature deviation) that monotonically increases with usage. The RUL is predicted by extrapolating the current degradation trend until the feature crosses a critical, pre-defined failure threshold.
*   **Mechanism:** $RUL = \text{Threshold} - \text{Current Degradation}$.
*   **Advantage:** Conceptually simple, directly links to a single degradation mechanism, and is highly interpretable.

### 2. Time-to-Threshold Prediction using Sensor Trends
This method uses the time series analysis of multiple critical sensor signals (e.g., Oil Pressure, Vibration, EGT). Instead of waiting for a single component degradation model, it predicts the time when a *combination* of sensor readings crosses a dangerous envelope or trend boundary.
*   **Mechanism:** Requires advanced filtering and trend extrapolation (e.g., Kalman filter) across multiple interdependent channels.
*   **Advantage:** Highly realistic as failure is rarely determined by a single variable; incorporates system-level health assessment.

### 3. Regression or Survival Model (Proportional Hazards Model)
These advanced statistical models are trained on historical run-to-failure datasets (synthetic or real). They estimate the probability of failure over time given a set of operating parameters and degradation states.
*   **Mechanism:** Treats RUL estimation as a survival analysis problem ($\text{Probability of surviving until time } t$).
*   **Advantage:** Statistically robust, provides a full probability distribution of RUL, and can account for varying failure rates.

### Chosen Approach
*   **Primary Approach (Hackathon):** **Synthetic Degradation-based RUL (Time-to-Threshold)**. This approach offers the best balance of fidelity and complexity for a hackathon. It is highly demonstrable, easy to integrate with existing degradation features, and yields a clear, interpretable time-to-failure estimate.
*   **Fallback Approach:** **Time-to-Threshold Prediction using Sensor Trends**. This is chosen because it provides a necessary enhancement to the primary approach by validating the degradation state across multiple, inter-related sensor signals, adding depth without requiring a full survival analysis implementation.

---

## PART C — RUL Computation (Primary Approach: Synthetic Degradation)

### 1. Input Features
The RUL calculation will rely on a combination of the following features:
*   **Primary Degradation Level ($\text{D}_{\text{key}}$):** The core engineered degradation state (e.g., an Index of Wear calculated from component histories).
*   **Key Residuals:** Time-varying residuals of critical sensor measurements (e.g., $Residual_{EGT} = EGT_{measured} - EGT_{baseline}$). High residuals indicate deviation from nominal performance.
*   **Operating Stress History:** A vector summarizing mission severity metrics over the last $N$ missions (e.g., peak torque, total cycles, average temperature deviation).

### 2. Output
*   **RUL Value:** Remaining Useful Life in **Missions** (e.g., "42 missions").
*   **Confidence Level:** A categorical or percentage estimate (e.g., "High Confidence").

### 3. Algorithm (Simple Formula/Rule-Based)
The RUL is calculated by first determining the degradation rate and then extrapolating to the failure threshold ($D_{crit}$).

$$\text{RUL}_{\text{Missions}} = \left\lfloor \frac{D_{crit} - D_{\text{current}}}{\text{Average Degradation Rate}(\bar{D}_{\text{rate}})} \right\rfloor$$

Where:
*   $D_{crit}$: The predefined critical degradation value for the primary component.
*   $D_{\text{current}}$: The current measured degradation value.
*   $\bar{D}_{\text{rate}}$: The empirically calculated average degradation rate, derived from the last 5-10 missions' change in $D_{\text{key}}$.

### 4. Confidence Estimation
Confidence is estimated using a weighted metric combining three factors:
$$\text{Confidence Score} = w_1 \cdot (\text{Data Quality}) + w_2 \cdot (\text{Trend Consistency}) + w_3 \cdot (\text{Component Redundancy})$$

*   **Data Quality:** Based on the completeness and variance of input sensors (penalty if too many sensors are missing data).
*   **Trend Consistency:** Measures the variance of $\bar{D}_{\text{rate}}$ over time. High variance suggests model instability, leading to lower confidence.
*   **Component Redundancy:** A multiplier factor. If the degradation level is supported by multiple correlated sensor trends (i.e., not just one sensor peaking), confidence is increased.

---

## PART D — RUL Display and Uncertainty

RUL must be communicated clearly and non-ambiguously to maintain operational safety and trust in the system.

### Display Components
1.  **Numeric Value:** The explicit RUL estimate (e.g., **42 operating missions**).
2.  **Confidence:** A categorical rating (Low/Medium/High) derived from the Confidence Score.
3.  **Trend:** A descriptor of the projected degradation trend over the coming period (Improving/Stable/Declining).
4.  **Main Evidence:** A concise list of the top 2-3 sensor or degradation metrics contributing most significantly to the RUL estimate (e.g., "rising EGT residual," "falling oil pressure").

### Example Outputs

**Example 1: Stable Decline (High Confidence)**
*   **RUL Estimate:** 110 operating missions
*   **Confidence:** High
*   **Trend:** Declining
*   **Main Evidence:** Degradation index ($\text{D}_{\text{key}}$) rising steadily, Oil Pressure residual remaining stable.
*   **Interpretation:** The engine is expected to fail after approximately 110 missions. The model is highly confident due to a consistent degradation rate across primary indicators.

**Example 2: Rapid Deterioration (Medium Confidence)**
*   **RUL Estimate:** 18 operating missions
*   **Confidence:** Medium
*   **Trend:** Rapidly Declining
*   **Main Evidence:** Sharp increase in EGT residual, coupled with elevated vibration frequency in the tertiary bearing.
*   **Interpretation:** Immediate maintenance is required, as the system detects rapid degradation. Confidence is medium because the vibration data is subject to environmental noise, warranting a physical inspection confirmation.

---

## PART E — Limitations Statement

> RUL estimates are based on synthetic degradation models and simplified physics. They are not validated on real aero piston engines and must not be used for actual maintenance decisions without further testing and domain expert validation.
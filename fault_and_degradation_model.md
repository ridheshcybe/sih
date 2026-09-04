# SIH26054 Aero Piston Engine Digital Twin - Health Index Specification

This document defines the methodology for calculating and interpreting the Engine Health Index (HI), a critical metric designed to provide operational insight into the engine's current condition relative to its expected performance and degradation trajectory. The index operates on a normalized 0–100 scale, where 100 represents perfect health.

---

## ⚙️ Part A — Inputs to Health Index (Data Sources)

The Health Index calculation relies on synthesizing multiple data streams, each weighted by its reliability and significance.

### 1. Sensor Residuals ($\text{Res}_{sensor}$)
*   **Inputs:** Real-time differences between measured sensor values (e.g., Exhaust Gas Temperature - EGT, Oil Pressure, Cylinder Head Temperature - CHT) and the values predicted by the running digital twin model ($\text{Measured} - \text{Predicted}$).
*   **Aggregation:** Individual residuals should be aggregated into a single $\text{Score}_{Residual}$. The Root Mean Square (RMS) deviation across a critical sensor group (EGT, Oil Pressure, etc.) is recommended.
*   **Scaling:** Residuals must be scaled relative to the sensor's operational standard deviation ($\sigma_{history}$) and the Mean Absolute Error (MAE) of the prediction model.

### 2. Anomaly Score ($\text{Score}_{Anomaly}$)
*   **Inputs:** A dedicated Machine Learning model (e.g., Isolation Forest, One-Class SVM) trained on healthy operational data.
*   **Purpose:** Quantifies the overall deviation of the current multi-dimensional sensor vector from the established "normal" operating envelope, irrespective of predefined thresholds.
*   **Scaling:** The output score (e.g., $S \in [-1, 1]$) is normalized to $0-100$.

### 3. Fault Probabilities ($\text{Score}_{Fault}$)
*   **Inputs:** Outputs from specialized ML models diagnosing specific component degradation (e.g., $P_{injector}$ - Injector probability of failure; $P_{bearing}$ - Bearing degradation probability).
*   **Aggregation:** The maximum probability across all monitored critical systems, weighted by criticality.
*   **Scaling:** The highest probability $P_{max}$ from any single component model is used. This score reflects the likelihood of an impending failure.

### 4. Degradation Level ($\text{Score}_{Degradation}$)
*   **Inputs:** A long-term operational trend indicator, often derived from an overall efficiency drop ($\eta$) or rate of change of baseline parameters.
*   **Purpose:** Captures the cumulative wear and tear not yet visible as an immediate residual spike.
*   **Scaling:** The decline rate (e.g., \% drop in Specific Fuel Consumption - SFC) is mapped to a score, ensuring a slow decline results in a higher (worse) penalty.

### 5. Data Quality Penalty ($\text{Penalty}_{DataQuality}$)
*   **Inputs:** Real-time sensor confidence scores (0-1).
*   **Purpose:** Penalizes the HI if multiple critical sensors report low confidence, invalid, or missing data.
*   **Calculation:** This is a multiplicative factor (explained in Part B).

### 6. Operating-Condition-Adjusted Limits (OCAL)
*   **Incorporation:** All residual scoring must be dynamically adjusted by the current operational state (e.g., high throttle vs. idle). The residual must be checked against a dynamic range, not a static one.

---

## 📈 Part B — Health Index Formula and Methodology

### 1. Core Health Index Formula
The proposed formula, designed for simple Python implementation, is:

$$
\text{Health Index} (HI) = \text{MaxScore} - \left( W_R \cdot \text{Score}_{Residual} + W_A \cdot \text{Score}_{Anomaly} + W_F \cdot \text{Score}_{Fault} + W_D \cdot \text{Score}_{Degradation} \right) \times \text{Quality Factor}
$$

*   **$\text{MaxScore}$:** A baseline score (e.g., 100).
*   **$\text{Score}_{X}$:** Sub-scores normalized to $0$ (Perfect) to $100$ (Worst).
*   **$W_X$:** Weights (see below).
*   **$\text{Quality Factor}$:** Derived from $\text{Penalty}_{DataQuality}$ (see below).

### 2. Sub-Score Definition and Scaling (0–100)
Each component score is normalized such that 0 is ideal, and 100 is critically bad.

| Component | Scale (Score) | Ideal Value | Calculation Logic |
| :--- | :--- | :--- | :--- |
| **Residual ($\text{Score}_{Residual}$)** | $0-100$ | 0 | $\text{Score}_{Residual} = 100 \cdot \min\left(1, \frac{\sum (\text{Res}_i / \sigma_{i} / \text{MAL}_i)}{K}\right)$ where $\text{MAL}$ is the Max Allowable Limit. |
| **Anomaly ($\text{Score}_{Anomaly}$)** | $0-100$ | 0 | Normalized output from ML model (e.g., $100 \cdot \text{Sigmoid}(\text{Anomaly\_Value})$). |
| **Fault ($\text{Score}_{Fault}$)** | $0-100$ | 0 | $100 \cdot \max(P_{i})$ where $P_i$ are component probabilities (e.g., $P_{fault} = \max(P_{bearing}, P_{injector})$). |
| **Degradation ($\text{Score}_{Degradation}$)** | $0-100$ | 0 | Exponentially weighted average of the degradation rate over time $t$: $\text{Rate} \cdot 100$. |

### 3. Recommended Weights ($W_X$)
Weights prioritize immediate, measurable faults over latent ones.
*   $W_R$ (Residuals): 0.35
*   $W_A$ (Anomaly): 0.25
*   $W_F$ (Fault): 0.30
*   $W_D$ (Degradation): 0.10
*(Sum of weights: 1.00)*

### 4. Smoothing and Filtering
*   **Method:** Exponential Moving Average (EMA) is recommended for all inputs, particularly $\text{Score}_{Residual}$ and $\text{Score}_{Degradation}$, to prevent rapid, non-physical "jitter" in the HI.
*   **Formula:** $\text{Score}_{smoothed}(t) = \alpha \cdot \text{Score}(t) + (1-\alpha) \cdot \text{Score}_{smoothed}(t-1)$.
*   **Alpha ($\alpha$):** Should be set low (e.g., 0.1 to 0.3) for long-term trends (Degradation) and higher (e.g., 0.4 to 0.6) for immediate residuals that need faster reaction time.

### 5. Handling Missing Sensors/Data Quality
The $\text{Quality Factor}$ is a penalty multiplier (ranging from 0.8 to 1.0) applied to the final HI.
*   **Mechanism:** If a critical sensor (e.g., EGT) confidence drops below $C_{threshold}$ (e.g., 0.7), the penalty is calculated.
*   **Formula:** $\text{Quality Factor} = 1 - \sum_{s \in \text{Critical Sensors}} \max(0, (1 - \text{Confidence}_{s}) \cdot \text{Weight}_{s})$.
*   **Effect:** A low data quality factor reduces the overall HI score, indicating that the result is unreliable.

---

## ⚠️ Part C — Health Categories and Alerts

The final HI score dictates the operational state.

| Category | HI Range | Color Code | Alert Behavior | Recommended Operator Action |
| :--- | :--- | :--- | :--- | :--- |
| **Healthy** | $85 - 100$ | Green | No alerts. Normal monitoring. | Maintain current operation. Log key performance indicators. |
| **Warning** | $70 - 84$ | Yellow | Low-priority alerts. Flag potential sub-system contributors. | Increase monitoring frequency. Review operational parameters against standard guidelines. Schedule preventative maintenance. |
| **Critical** | $50 - 69$ | Orange | Medium-to-high priority alerts. Requires immediate operator attention. | **Reduce operational load** (e.g., reduce max throttle). Plan for service within the next operational window. Investigate contributing factors. |
| **Emergency** | $< 50$ | Red | Critical system shutdown warning. Immediate, automated action required. | **Immediate reduction of power or engine shutdown** if decline continues. Isolate the faulty system component. |

---

## 📝 Part D — Explanation Generation

The system must translate the raw score and underlying contributors into a clear, actionable narrative for the operator.

### 1. Explanation Structure (The 'Why')
The explanation must follow a structured format:
1.  **Headline:** HI Score/Range and Alert Status (e.g., "HI: 71/100 (Warning)").
2.  **Diagnosis:** Identification of the primary contributing factors (the "Main contributors").
3.  **Detail:** Quantifiable metrics (e.g., "Injector fault probability: 0.68," "EGT residual elevated").
4.  **Recommendation:** Specific, prioritized action (e.g., "inspect injector and lubrication system within next maintenance window").

### 2. Example Scenarios

**Scenario 1: Moderate Degradation (Warning)**
*   **Inputs:** $\text{Score}_{Residual}$ (Medium), $\text{Score}_{Anomaly}$ (Low), $\text{Score}_{Fault}$ (Low), $\text{Score}_{Degradation}$ (High).
*   **Explanation:** "Health Index: 78/100 (Warning). Main contributors: Sustained increase in Specific Fuel Consumption (SFC), suggesting overall engine inefficiency. Injector fault probability is currently low (0.15). Recommended action: Monitor SFC trend over the next 10 flight hours and prepare for efficiency-related maintenance."

**Scenario 2: Acute Fault (Critical)**
*   **Inputs:** $\text{Score}_{Residual}$ (High - EGT), $\text{Score}_{Anomaly}$ (High), $\text{Score}_{Fault}$ (High - Bearing), $\text{Score}_{Degradation}$ (Low).
*   **Explanation:** "Health Index: 55/100 (Critical). Main contributors: Significantly elevated Exhaust Gas Temperature (EGT) residual, suggesting potential combustor fouling. Bearing degradation probability is rising rapidly (0.72). Recommended action: Reduce maximum allowable thrust immediately. Perform a full vibration and oil analysis upon landing, and plan for major component inspection."

**Scenario 3: Data Integrity Issue (Warning)**
*   **Inputs:** All scores are low (Good), but $\text{Quality Factor}$ is low due to missing sensor data.
*   **Explanation:** "Health Index: 82/100 (Warning). Warning: Data quality penalty applied due to intermittent Oil Pressure sensor data loss. While modeled components appear healthy, the true status is unverified. Recommended action: Do not rely on the HI score. Schedule a data diagnostic check for the Oil Pressure sensor."
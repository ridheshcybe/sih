# SIH26054 Aero Piston Engine Digital Twin Documentation

This document provides a comprehensive overview of the digital twin architecture and data flow for the SIH26054 aero piston engine.

## Part A: High-Level Architecture Diagram (Mermaid)

The following Mermaid diagram illustrates the components and main data flow of the digital twin system.

```mermaid
graph TD
    subgraph Data Inputs
        T[Telemetry Source Abstraction] -->|Raw Data Stream| I;
        S[Synthetic Telemetry Simulator] -->|Simulated Stream| I;
        C[Future CAN/SocketCAN Adapter] -->|Raw Data Stream| I;
        E[Future ECU/FADEC Adapter] -->|Raw Data Stream| I;
    end

    I[Telemetry Ingestion] -->|Validation/Normalized Data| V;
    V[Validation/Normalization] -->|Clean Data Stream| TSD;

    subgraph Core Processing
        TSD[Time-series Storage] -->|Historical Data| STM;
        STM[Digital Twin State Manager] -->|Current State & History| PM;
        PM[Physics-inspired Model] -->|Calculated Physics States| FE;
        FE[Feature Engineering] -->|Feature Vectors| AD;
        AD[Anomaly Detection] -->|Anomaly Flags & Scores| FC;
        FC[Fault Diagnosis] -->|Fault ID, Confidence, Root Cause| R;
        R[Degradation/RUL] -->|RUL/Degradation Curve| HI;
        HI[Health Index] -->|Health Score| MR;
    end

    subgraph Outputs & Services
        MR[Maintenance Recommendation] -->|Recommendations| API;
        STM -->|State Data| API;
        PM -->|Model Parameters| API;

        API[REST API] -->|HTTP Requests| FD;
        WS[WebSocket Server] -->|Event Stream| FD;
        API -->|Model Metadata| MRG;
        WS -->|Live Stream| WS_DASH;

        FD[Frontend Dashboard]
        WS_DASH[Dashboard Visualization]
        RPT[Report Generator] -->|Generated Report| API;
        MRG[Model Registry]
    end

    % Flow and Dependencies
    V --> TSD;
    TSD --> STM;
    STM --> PM;
    PM --> FE;
    FE --> AD;
    AD --> FC;
    FC --> R;
    R --> HI;
    HI --> MR;
    
    % Outgoing service connections
    API -->|Query/Control| FD;
    WS_DASH -->|Visualization| FD;
    API -->|Model Retrieval| MRG;
    RPT -->|Reporting| API;

    % Final user-facing outputs
    FD -->|User Interaction| RPT;

    % Data Sources (Simplified flow for visual clarity)
    T --> I
    S --> I
    C --> I
    E --> I

```

## Part B: Data Flow Description

The digital twin state undergoes a controlled progression of data refinement, analysis, and prediction across 15 sequential stages.

| Stage | Input | Output | Responsible Module | Failure Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **1. Telemetry Source** | Raw Sensor Data (Engine parameters, I/O) | Raw Data Stream | Telemetry Source Abstraction | Data loss or outdated sensor readings. |
| **2. Ingestion** | Raw Data Stream | Validated Data Stream | Telemetry Ingestion | Failure to parse data format; missing header data. |
| **3. Validation/Normalization** | Validated Data Stream | Clean Data Stream | Validation/Normalization | Out-of-range values detected (requires flagging/interpolation). |
| **4. Digital Twin State Manager** | Clean Data Stream, Historical Data | Current Engine State | Digital Twin State Manager | Failure to synchronize state due to data gaps. |
| **5. Expected Sensor Calculation** | Current Engine State, Physics Models | Expected Readings Set | Physics-inspired Model | Incorrect physics parameters or boundary condition failure. |
| **6. Residual Calculation** | Actual Readings, Expected Readings Set | Residual Vector | Physics-inspired Model | Failure to calculate difference due to data types mismatch. |
| **7. Feature Engineering** | Residual Vector | Feature Vectors | Feature Engineering | Non-stationary data or insufficient feature context. |
| **8. Anomaly Inference** | Feature Vectors | Anomaly Flags & Scores | Anomaly Detection | Model drift or inability to classify deviation type. |
| **9. Fault Classification** | Anomaly Flags & Scores | Fault ID, Confidence | Fault Diagnosis | Ambiguity between related fault modes; low confidence score. |
| **10. Degradation/RUL** | Fault ID, Operating Cycles | Remaining Useful Life (RUL) Estimate | Degradation/RUL Module | Calculation failure due to unknown operational environment. |
| **11. Health Index** | RUL Estimate, Failure Criteria | Health Score (0-100) | Health Index | Lack of critical operational threshold data. |
| **12. Risk Assessment** | Health Score, Operating Context | Risk Level (Low/Medium/High) | Risk Assessment Module | Incomplete contextual information (e.g., environment variables). |
| **13. Maintenance Recommendation**| Risk Level, RUL Estimate, Fault ID | Specific Action Items | Maintenance Recommendation | Overly conservative or vague recommendations. |
| **14. WebSocket Event** | Maintenance Recommendation, State Data | Live Event Event Payload | WebSocket Server | Event serialization failure or rate limiting trigger. |
| **15. Dashboard/Reporting** | Live Event Payload, Report Query | Visualized/Generated Report | Frontend Dashboard | Failure to render due to client-side data format mismatch. |
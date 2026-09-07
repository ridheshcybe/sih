# SIH26054 — Demo and Documentation Pack

## 1. Problem / Solution One-Pager

### Problem statement
Aero piston engine faults in MALE UAV operations can lead to mission aborts, loss of asset value, and unsafe operating conditions. In many cases, current monitoring is reactive and based on threshold alarms, which often trigger only after the engine has already moved into an abnormal regime.

### Target users
- UAV operator
- Maintenance engineer
- Propulsion engineer
- Fleet manager
- Test-rig engineer

### Current gap
- Threshold-based monitoring is reactive rather than predictive
- Limited estimation of Remaining Useful Life
- Weak degradation tracking across mission phases
- No mission-wise behavior simulation or replay for diagnosis

### Our solution
We are building a software demonstrator for an AI-enabled digital twin that monitors engine health in real time, predicts likely faults, estimates Remaining Useful Life, and supports mission replay and maintenance guidance. The system combines live telemetry, a physics-informed engine twin, and ML-based anomaly and fault inference to provide early-warning capability for future integration into operational workflows.

### Key features
- Real-time engine parameter visualization
- Health Index from 0 to 100 with explanatory context
- Anomaly detection and fault classification
- Remaining Useful Life estimation with confidence indicators
- Mission simulation for altitude, throttle, and environmental conditions
- Historical mission replay for root-cause analysis
- Maintenance advisory generation
- Mission-wise health reporting for operators and engineers

### Demo highlights
- Healthy engine mission start
- Live telemetry and twin state view
- Fault injection during mission execution
- Anomaly detection and fault classification
- Health Index decline over time
- RUL reduction as degradation progresses
- Maintenance advisory generation
- Mission replay and mission report output

### Limitations
- Uses synthetic telemetry rather than real engine data
- Not flight-certified
- Not validated on real aero piston engines
- Intended as a physics-informed prototype and research demonstrator for future integration

---

## 2. Slide Deck Outline

### Slide 1 — Title
Title: AI-Enabled Digital Twin for Aero Piston Engines in MALE UAVs

Subtitle:
- Team Name
- SIH26054
- DRDO / iDEX
- Team members

Suggested visual:
- UAV or engine illustration
- project logo if available

### Slide 2 — Problem
- UAV engine faults can disrupt missions and increase operational risk
- MALE UAVs are used in strategic ISR and surveillance missions
- Reliability of the propulsion system is mission-critical
- Reactive monitoring often identifies issues too late

### Slide 3 — Current Gap
- Threshold alarms are reactive and late
- Limited degradation and RUL visibility
- Lack of mission-wise engine behavior simulation
- Weak support for root-cause analysis before failure

### Slide 4 — Our Solution
- AI-enabled digital twin synchronized to live telemetry
- Health monitoring, fault prediction, and RUL estimation
- Physics-informed ML with residual-based explainability
- Mission simulation and historical replay

### Slide 5 — Architecture Overview
- Frontend: React dashboard
- Backend: FastAPI, SQLite, WebSockets
- Simulator: synthetic telemetry and fault injection
- ML layer: anomaly, fault, degradation, and RUL models
- Digital twin: hybrid physics + ML logic

### Slide 6 — Digital Twin and Physics Model
- Virtual engine model tracks live telemetry
- Expected sensor values are computed from physics-inspired logic
- Residuals are estimated as observed minus expected
- Health Index reflects deviation and degradation trend

### Slide 7 — AI/ML Layer
- Anomaly detection using Isolation Forest
- Fault classification using RandomForest or XGBoost
- Degradation estimation based on regression
- RUL estimation with confidence level

### Slide 8 — Live Demo
- Healthy mission start
- Fault injection during operation
- Detection and classification in near real time
- Health decline and RUL trend
- Advisory generation and replay

### Slide 9 — Results and Metrics
- Healthy vs faulty separation for anomaly scores
- Example fault class probabilities
- RUL trend over mission time
- Example synthetic-data metrics
- F1 and MAE examples with realistic wording

### Slide 10 — Innovation Highlights
- Physics-informed anomaly detection
- Hybrid physics + ML reasoning
- Explainable fault diagnosis
- Adaptive Health Index
- Mission-risk assessment

### Slide 11 — Roadmap
- Phase 1: hackathon demonstrator with synthetic data
- Phase 2: integration with engine test-rig telemetry
- Phase 3: fleet-level and GCS deployment
- Future: CAN/ECU integration and secure deployment pathways

### Slide 12 — Limitations
- Synthetic data only
- Not flight-certified
- Requires real engine validation
- Prototype for demonstration and research

### Slide 13 — Impact and Conclusion
- Better mission reliability awareness
- Earlier maintenance planning
- Reduced downtime risk
- Scalable toward fleet-level health monitoring

---

## 3. 5-Minute Demo Script

### Step 1: Healthy Engine Mission Start
Presenter action:
- Click Start Mission
- Select Standard ISR profile

On screen:
- Dashboard initializes
- Telemetry table starts updating
- RPM rises from around 800 to 2200
- CHT rises to around 180°C
- EGT rises toward 600°C

System response:
- Health Index around 95/100
- Anomaly score low, around 0.05

Narration:
- “We start a standard ISR mission with a healthy engine. The telemetry remains within normal operating limits.”

### Step 2: Show Live Telemetry and Twin State
Presenter action:
- Point to telemetry panel
- Point to twin state card

On screen:
- Live telemetry stream
- Expected vs observed sensor comparison
- Stable RPM, CHT, EGT, oil pressure

System response:
- Health Index stays around 92 to 95
- Residuals remain small

Narration:
- “The digital twin continuously synchronizes with live telemetry and computes expected sensor values and residuals in near real time.”

### Step 3: Change Mission Condition
Presenter action:
- Select High-Altitude profile or adjust altitude

On screen:
- Altitude increases from around 2000m to 4000m
- Ambient temperature drops
- EGT and CHT rise slightly

System response:
- Health Index adjusts slightly
- Residuals become more visible

Narration:
- “We simulate a high-altitude mission. The system adapts to changing environmental conditions without losing the relative health context.”

### Step 4: Inject a Fault
Presenter action:
- Click Inject Fault
- Choose Injector Degradation
- Set severity to 0.7

On screen:
- Fault confirmation message
- EGT rises from around 600°C to 680°C
- CHT rises from around 180°C to 210°C
- Fuel flow changes

System response:
- Anomaly score rises from 0.05 to 0.45
- Fault classifier shows injector degradation with high probability

Narration:
- “We inject an injector degradation fault. The system immediately detects abnormal behavior and updates its diagnosis.”

### Step 5: Show Anomaly Detection and Fault Classification
Presenter action:
- Point to anomaly score panel
- Point to fault probability panel

On screen:
- Anomaly graph spikes
- Fault probabilities update
- Injector degradation dominates

System response:
- Fault classification updates in real time

Narration:
- “The anomaly detector flags the abnormal pattern, and the fault classifier identifies injector degradation as the most likely root cause.”

### Step 6: Show Health Index Decline
Presenter action:
- Point to Health Index gauge

On screen:
- Health Index drops from 90 to 75 to 68
- EGT and CHT residuals remain elevated
- Oil pressure begins to drift downward

System response:
- Health state transitions from healthy to warning

Narration:
- “As degradation progresses, the Health Index declines and the engine moves from normal to warning condition.”

### Step 7: Show RUL Reduction
Presenter action:
- Point to RUL panel

On screen:
- RUL estimate moves from 50 hours to 28 hours
- Confidence may be medium
- Downward RUL trend visible

System response:
- RUL trend shows a clear decline

Narration:
- “The system estimates Remaining Useful Life. As the fault progresses, the expected remaining mission support decreases.”

### Step 8: Show Maintenance Advisory
Presenter action:
- Click View Maintenance Advisory

On screen:
- Advisory card appears
- Text recommends inspection of injector system and lubrication review
- Avoid high-throttle operation until inspection

System response:
- Advisory generated from fault type and severity

Narration:
- “Based on the diagnosis, the system produces a maintenance recommendation to guide operator action.”

### Step 9: Show Mission Replay
Presenter action:
- Click Replay Mission
- Select completed mission

On screen:
- Telemetry replays with fault timeline
- Health Index trend and residuals replay
- Mission summary is visible

System response:
- Historical mission playback reveals progression

Narration:
- “We can replay the mission to review the fault evolution and support post-flight analysis.”

### Step 10: Show Final Mission Report
Presenter action:
- Click Generate Report

On screen:
- HTML or PDF report appears
- Mission summary
- Fault events
- Health Index timeline
- RUL trend
- Maintenance advisory

System response:
- Final mission summary generated

Narration:
- “The system compiles the mission into a report that supports maintenance planning and operator review.”

### 2-minute backup demo script
1. Healthy mission start
2. Fault injection
3. Anomaly detection and health decline
4. RUL reduction and advisory
5. Mission replay

---

## 4. Technical Documentation and Model Card

### Architecture overview
- Frontend: React dashboard with real-time WebSocket updates
- Backend: FastAPI REST API and WebSocket server, SQLite database
- Simulator: synthetic telemetry generation with mission profiles and fault injection
- ML layer: anomaly detection, fault classification, degradation, and RUL models
- Digital twin: expected sensor logic, residuals, and Health Index
- Data flow: telemetry → ingest → twin update → ML inference → WebSocket → dashboard

### How to run
Backend:
- Install dependencies
- Start server
- Use FastAPI app from the backend folder

Frontend:
- Install Node packages
- Start dev server
- Connect to the backend API

Simulator:
- Run mission profile generation and dataset generation scripts
- Generate healthy and faulty synthetic mission data

ML training:
- Train anomaly, fault, degradation, and RUL models
- Save model artifacts for inference

### API summary
REST endpoints:
- GET /api/system/health
- POST /api/missions/start
- POST /api/missions/stop
- GET /api/engines/{engine_id}/state
- GET /api/engines/{engine_id}/telemetry
- GET /api/engines/{engine_id}/health
- GET /api/engines/{engine_id}/faults
- GET /api/engines/{engine_id}/rul
- POST /api/simulation/start
- POST /api/simulation/stop
- POST /api/faults/inject
- POST /api/replay/start
- POST /api/replay/stop
- GET /api/reports/{mission_id}

WebSocket events:
- twin_state_update
- anomaly_detected
- fault_prediction
- health_update
- rul_update
- maintenance_advisory

### Data description
- Synthetic telemetry generated from a physics-inspired engine model
- Mission profiles include:
  - ISR
  - high-altitude
  - hot-weather
  - aggressive
- Fault categories include:
  - injector degradation
  - lubrication issue
  - overheating
  - sensor drift
  - abnormal vibration
  - battery and alternator degradation
- Labels include:
  - fault_type
  - fault_severity
  - degradation_level
  - rul_label

### Model card
#### Models used
- Anomaly Detection: Isolation Forest
- Fault Classifier: RandomForest or XGBoost
- Degradation Estimator: regression model
- RUL Estimator: regression model with confidence output

#### Training data
- Synthetic missions with healthy and faulty operating conditions
- Mission profiles:
  - ISR
  - high-altitude
  - hot-weather
  - aggressive
- Fault types include injector degradation, lubrication issues, overheating, sensor drift, abnormal vibration, and others
- Example dataset size: around 200,000 rows, with train, validation, and test splits

#### Metrics
- Anomaly detection: healthy vs faulty separation, example mean score difference
- Fault classifier: example F1 values by class
- Degradation estimator: example MAE on 0 to 1 scale
- RUL estimator: example MAE in hours

Use phrasing like:
- example synthetic-data performance
- indicative metric trend
- not yet validated on real engine telemetry

#### Limitations
- Trained on synthetic data rather than real engine telemetry
- Not validated on real aero piston engines
- Not suitable as a certification-grade system
- Prototype for demonstration and research

#### Intended use
- Smart India Hackathon demonstration
- Research prototype for predictive maintenance
- Future integration with engine test-rig data and fleet monitoring

---

## Summary
This pack keeps the project honest, concise, and demo-ready: it explains the problem, matches the actual MVP architecture, and gives the team a presentation script suitable for a DRDO judge audience.

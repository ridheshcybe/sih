# Synthetic Engine Fault Dataset

This dataset contains synthetic telemetry generated to model aero-piston engine operation in MALE UAV missions.

## Dataset summary
- Number of missions: 12
- Total rows: 21600
- Healthy rows: 18005
- Faulty rows: 3595
- Train missions: 7
- Validation missions: 2
- Test missions: 3

## Profiles used
- standard_isr
- high_altitude
- hot_weather
- aggressive

## Fault labels
- healthy: normal operation
- misfire: transient RPM loss with EGT spike and vibration rise
- injector_degradation: rising EGT and CHT with fuel-flow drift
- lubrication_issue: fall in oil pressure and increase in oil temperature/vibration
- overheating: CHT/EGT exceed normal thermal envelope
- sensor_drift: sensor bias begins to diverge from true value
- sensor_dropout: a sensor returns NaN or unrealistic values
- abnormal_vibration: vibration RMS rises beyond expected runtime levels
- battery_alternator_degradation: voltage drop and alternator current anomalies

## Label descriptions
- fault_type: string label for the active fault condition
- fault_severity: scalar severity in the range [0, 1]
- degradation_level: scalar degradation estimate in [0, 1]
- rul_label: nominal or degraded life-remaining state

## Split policy
The dataset is split by mission ID: 60% train, 20% validation, 20% test. There is no overlap between splits.
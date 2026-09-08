"""SIH26054 simulator package: physics-inspired engine model, mission profiles, fault injection."""

SENSOR_COLUMNS = [
    "rpm",
    "cht",
    "egt",
    "oil_pressure",
    "oil_temperature",
    "fuel_flow",
    "vibration_rms",
    "battery_voltage",
    "alternator_current",
    "injection_timing",
    "altitude",
    "ambient_temperature",
]

LABEL_COLUMNS = [
    "fault_label",
    "fault_severity",
    "degradation_level",
    "rul_label",
]
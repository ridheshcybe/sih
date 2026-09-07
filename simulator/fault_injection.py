from __future__ import annotations

import math
import random
from typing import Any, Dict, Iterable, List


FAULT_LIBRARY: Dict[str, Dict[str, Any]] = {
    "misfire": {
        "effects": {"rpm": -0.12, "egt": 0.18, "vibration_rms": 0.40},
        "pattern": "sudden",
        "sensors": ["rpm", "egt", "vibration_rms"],
    },
    "injector_degradation": {
        "effects": {"egt": 0.12, "cht": 0.10, "fuel_flow": 0.15},
        "pattern": "gradual",
        "sensors": ["egt", "cht", "fuel_flow"],
    },
    "lubrication_issue": {
        "effects": {"oil_pressure": -0.25, "oil_temperature": 0.16, "vibration_rms": 0.30},
        "pattern": "gradual",
        "sensors": ["oil_pressure", "oil_temperature", "vibration_rms"],
    },
    "overheating": {
        "effects": {"cht": 0.18, "egt": 0.22, "fuel_flow": 0.12},
        "pattern": "gradual",
        "sensors": ["cht", "egt", "fuel_flow"],
    },
    "sensor_drift": {
        "effects": {"cht": 0.30},
        "pattern": "gradual",
        "sensors": ["cht"],
    },
    "sensor_dropout": {
        "effects": {"cht": "nan"},
        "pattern": "sudden",
        "sensors": ["cht"],
    },
    "abnormal_vibration": {
        "effects": {"vibration_rms": 0.55},
        "pattern": "gradual",
        "sensors": ["vibration_rms"],
    },
    "battery_alternator_degradation": {
        "effects": {"battery_voltage": -0.18, "alternator_current": 0.25},
        "pattern": "gradual",
        "sensors": ["battery_voltage", "alternator_current"],
    },
}


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def apply_fault(telemetry_row: Dict[str, Any], fault_type: str, severity: float, time_since_fault_start: float) -> Dict[str, Any]:
    row = dict(telemetry_row)
    severity = max(0.0, min(1.0, float(severity)))
    fault_type = fault_type.lower()
    if fault_type not in FAULT_LIBRARY:
        return row

    if fault_type == "misfire":
        row["rpm"] = row.get("rpm", 0.0) * (1.0 - severity * 0.16) - 80.0 * severity
        row["egt"] = row.get("egt", 0.0) * (1.0 + severity * 0.22) + 35.0 * severity
        row["vibration_rms"] = row.get("vibration_rms", 0.0) * (1.0 + severity * 0.56)

    elif fault_type == "injector_degradation":
        row["egt"] = row.get("egt", 0.0) * (1.0 + severity * 0.14) + 18.0 * severity
        row["cht"] = row.get("cht", 0.0) * (1.0 + severity * 0.12) + 12.0 * severity
        row["fuel_flow"] = row.get("fuel_flow", 0.0) * (1.0 + severity * 0.20)

    elif fault_type == "lubrication_issue":
        row["oil_pressure"] = row.get("oil_pressure", 0.0) * (1.0 - severity * 0.30) - 5.0 * severity
        row["oil_temperature"] = row.get("oil_temperature", 0.0) * (1.0 + severity * 0.18) + 8.0 * severity
        row["vibration_rms"] = row.get("vibration_rms", 0.0) * (1.0 + severity * 0.45)

    elif fault_type == "overheating":
        row["cht"] = row.get("cht", 0.0) * (1.0 + severity * 0.20) + 20.0 * severity
        row["egt"] = row.get("egt", 0.0) * (1.0 + severity * 0.25) + 28.0 * severity
        row["fuel_flow"] = row.get("fuel_flow", 0.0) * (1.0 + severity * 0.10)

    elif fault_type == "sensor_drift":
        drift = 5.0 * severity * max(0.0, time_since_fault_start / 60.0)
        row["cht"] = row.get("cht", 0.0) + drift

    elif fault_type == "sensor_dropout":
        row["cht"] = float("nan")

    elif fault_type == "abnormal_vibration":
        row["vibration_rms"] = row.get("vibration_rms", 0.0) * (1.0 + severity * 0.90) + 2.0 * severity

    elif fault_type == "battery_alternator_degradation":
        row["battery_voltage"] = row.get("battery_voltage", 0.0) * (1.0 - severity * 0.22) - 1.5 * severity
        row["alternator_current"] = row.get("alternator_current", 0.0) * (1.0 + severity * 0.32) + 8.0 * severity

    # Clamp impossible values after faults.
    row["rpm"] = max(400.0, float(row.get("rpm", 400.0)))
    row["oil_pressure"] = max(0.0, float(row.get("oil_pressure", 0.0)))
    row["battery_voltage"] = max(8.0, float(row.get("battery_voltage", 8.0)))
    row["alternator_current"] = max(0.0, float(row.get("alternator_current", 0.0)))
    row["vibration_rms"] = max(0.0, float(row.get("vibration_rms", 0.0)))
    row["cht"] = float(row.get("cht", 0.0))
    row["egt"] = float(row.get("egt", 0.0))
    row["fuel_flow"] = max(0.0, float(row.get("fuel_flow", 0.0)))
    row["oil_temperature"] = max(0.0, float(row.get("oil_temperature", 0.0)))
    return row


def generate_faulty_mission(profile_id: str, fault_list: Iterable[Dict[str, Any]], duration_seconds: int = 1800):
    from simulator.mission_profiles import generate_mission_profile

    mission = generate_mission_profile(profile_id, duration_seconds)
    rows = []

    for sample in mission["timeline"]:
        row = {
            "timestamp": sample["timestamp"],
            "mission_id": 0,
            "profile_id": profile_id,
            "phase": sample["phase"],
            "throttle": sample["throttle"],
            "rpm": sample["rpm"],
            "altitude": sample["altitude"],
            "ambient_temperature": sample["ambient_temperature"],
            "cht": 170.0 + (sample["rpm"] / 25.0) + sample["ambient_temperature"] * 0.6,
            "egt": 480.0 + (sample["rpm"] / 20.0) + sample["ambient_temperature"] * 0.9,
            "oil_pressure": 46.0 - (sample["altitude"] / 250.0),
            "oil_temperature": 88.0 + (sample["ambient_temperature"] * 0.7),
            "fuel_flow": 15.0 + (sample["throttle"] / 10.0),
            "vibration_rms": 1.2 + (sample["rpm"] / 3000.0),
            "battery_voltage": 28.5,
            "alternator_current": 16.0,
            "injection_timing": 18.0,
            "fault_type": "healthy",
            "fault_severity": 0.0,
            "degradation_level": 0.0,
            "rul_label": "healthy",
        }

        active_faults = []
        for fault in fault_list:
            start_t = float(fault.get("start_time", 0.0))
            end_t = float(fault.get("end_time", duration_seconds))
            if start_t <= sample["timestamp"] <= end_t:
                active_faults.append(fault)

        if active_faults:
            for fault in active_faults:
                row = apply_fault(
                    row,
                    fault.get("fault_type", "injector_degradation"),
                    float(fault.get("severity", 0.5)),
                    sample["timestamp"] - float(fault.get("start_time", sample["timestamp"])),
                )
                row["fault_type"] = fault.get("fault_type", "injector_degradation")
                row["fault_severity"] = float(fault.get("severity", 0.5))
                row["degradation_level"] = round(min(1.0, 0.25 + float(fault.get("severity", 0.5)) * 0.75), 4)
                row["rul_label"] = "degraded"

        rows.append(row)

    return rows


__all__ = ["FAULT_LIBRARY", "apply_fault", "generate_faulty_mission"]

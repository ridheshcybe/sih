"""Smoke tests for the simulator."""

from __future__ import annotations

import pandas as pd
import pytest

from simulator.engine_model import EngineModel
from simulator.fault_injection import FAULT_TYPES
from simulator.mission_profiles import PROFILES, phase_at
from simulator.simulate import simulate_mission

SENSOR_RANGES = {
    "rpm": (0.0, 5800.0),
    "cht": (20.0, 300.0),
    "egt": (100.0, 900.0),
    "oil_pressure": (0.2, 5.5),
    "oil_temperature": (10.0, 150.0),
    "fuel_flow": (0.5, 26.0),
    "vibration_rms": (0.05, 6.0),
    "battery_voltage": (18.0, 28.5),
    "alternator_current": (0.0, 60.0),
    "injection_timing": (5.0, 40.0),
}


def test_healthy_mission_ranges_and_columns():
    df = simulate_mission(profile_id="standard_isr", duration_s=60, seed=1)
    assert len(df) > 100
    required = ["timestamp", "mission_id", "profile_id", "phase", "throttle",
                "rpm", "cht", "egt", "oil_pressure", "oil_temperature", "fuel_flow",
                "vibration_rms", "battery_voltage", "alternator_current",
                "injection_timing", "altitude", "ambient_temperature",
                "fault_label", "fault_severity", "degradation_level", "rul_label"]
    for col in required:
        assert col in df.columns, f"missing column {col}"
    for sensor, (lo, hi) in SENSOR_RANGES.items():
        assert df[sensor].between(lo, hi).all(), f"{sensor} out of range"
    assert (df["fault_label"] == "none").all()
    assert df.isna().sum().sum() == 0, "NaN values in output"


def test_determinism_with_same_seed():
    a = simulate_mission(profile_id="high_altitude", duration_s=30, seed=7)
    b = simulate_mission(profile_id="high_altitude", duration_s=30, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_phase_sequence():
    name, throttle, _, _ = phase_at(PROFILES["standard_isr"], 0.0)
    assert name == "startup"
    last = PROFILES["standard_isr"][-1]
    name2, _, _, _ = phase_at(PROFILES["standard_isr"], 999999.0)
    assert name2 == last[0]


def test_fault_effects_change_expected_sensors():
    healthy = simulate_mission(profile_id="standard_isr", duration_s=90,
                               seed=3, fault_type=None)
    lub = simulate_mission(profile_id="standard_isr", duration_s=90, seed=3,
                           fault_type="lubrication_issue", severity=0.8,
                           fault_start_s=20, fault_duration_s=40)
    # Compare the fault peak window (t = 35-60 s, env ramps to ~0.3-0.5).
    h = healthy.iloc[350:600]
    l = lub.iloc[350:600]
    assert l["oil_pressure"].mean() < h["oil_pressure"].mean() - 0.2


@pytest.mark.parametrize("fault_type", FAULT_TYPES)
def test_fault_labels_are_present(fault_type):
    df = simulate_mission(profile_id="standard_isr", duration_s=60, seed=5,
                          fault_type=fault_type, severity=0.6,
                          fault_start_s=10, fault_duration_s=30)
    assert (df["fault_label"] == fault_type).any(), f"label {fault_type} never appears"
    assert (df["fault_severity"] > 0).any()
    assert (df["degradation_level"] > 0).any()
    assert (df["rul_label"] < 500.0).any()


def test_engine_model_edges():
    m = EngineModel(seed=0)
    for _ in range(100):
        m.step(throttle=0, altitude=0, ambient_temperature=15, dt=0.1)
    m2 = EngineModel(seed=1)
    for _ in range(100):
        m2.step(throttle=100, altitude=15000, ambient_temperature=-20, dt=0.1)
    assert m2.rpm > m.rpm
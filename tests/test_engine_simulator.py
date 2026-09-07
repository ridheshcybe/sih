from io import StringIO

import pandas as pd
import pytest

from backend.simulator.EngineSimulator import EngineSimulator


@pytest.fixture
def simulator():
    return EngineSimulator(seed=7)


def read_csv(csv_output):
    return pd.read_csv(StringIO(csv_output))


def test_simulator_accepts_explicit_steps(simulator):
    steps = [
        {"throttle": 10, "altitude": 0, "ambient_temperature": 25, "mission_phase": "Idle", "compute": 1},
        {"throttle": 80, "altitude": 100, "ambient_temperature": 25, "mission_phase": "Takeoff", "compute": 50},
    ]
    frame = read_csv(simulator.simulate_mission(steps))
    assert len(frame) == 2
    assert {"rpm", "egt", "oil_pressure", "battery_voltage", "fault_label"} <= set(frame.columns)
    assert frame.iloc[1]["rpm"] > frame.iloc[0]["rpm"]


def test_standard_profile_has_all_phases_and_valid_ranges(simulator):
    frame = read_csv(simulator.simulate_mission("standard_isr"))
    assert len(frame) == 200
    assert {"Startup", "Takeoff", "Cruise", "Descent", "Landing"} <= set(frame["mission_phase"])
    assert frame["throttle"].between(0, 100).all()
    assert (frame["altitude"] >= 0).all()
    assert frame["rpm"].between(1000, 6000).all()
    assert frame["egt"].between(600, 1000).all()
    assert (frame["fault_label"] == "none").all()


def test_all_profiles_generate_rows(simulator):
    for profile in ("standard_isr", "high_altitude", "hot_weather", "aggressive"):
        frame = read_csv(simulator.simulate_mission(profile))
        assert not frame.empty
        assert frame["mission_phase"].notna().all()


def test_unknown_profile_fails_clearly(simulator):
    with pytest.raises(ValueError, match="Unknown mission profile"):
        simulator.simulate_mission("missing_profile")

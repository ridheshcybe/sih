"""Backend smoke tests using FastAPI TestClient.

These exercise the full loop: mission start -> telemetry ingest -> digital twin
-> WebSocket broadcast -> fault injection -> report generation.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from backend.main import app

ENGINE_ID = "ENG-001"
MISSION_DURATION_S = 6.0


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def stop_if_running(client):
    """Stop any running mission so each test starts clean."""
    client.post("/api/v1/simulation/stop", json={"engine_id": ENGINE_ID})
    time.sleep(0.3)


def test_system_health(client):
    res = client.get("/api/system/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_mission_lifecycle(client):
    stop_if_running(client)
    res = client.post("/api/v1/missions", json={
        "mission_name": "Smoke Test",
        "profile_id": "standard_isr",
        "engine_id": ENGINE_ID,
        "duration_s": MISSION_DURATION_S,
    })
    assert res.status_code == 200
    mission_id = res.json()["mission_id"]
    assert res.json()["status"] == "STARTED"

    time.sleep(2.0)

    state = client.get(f"/api/v1/engines/{ENGINE_ID}/state")
    assert state.status_code == 200
    twin = state.json()["twin_state"]
    assert twin is not None
    assert 0 <= twin["health_index"] <= 100
    assert twin["mission_id"] == mission_id

    telemetry = client.get(f"/api/v1/engines/{ENGINE_ID}/telemetry?limit=20")
    rows = telemetry.json()["rows"]
    assert len(rows) > 0
    assert {"rpm", "cht", "egt", "oil_pressure"} <= set(rows[-1].keys())

    health = client.get(f"/api/v1/engines/{ENGINE_ID}/health")
    assert health.json()["health_index"] is not None
    assert len(health.json()["trend"]) > 0


def test_fault_injection(client):
    stop_if_running(client)
    res = client.post("/api/v1/missions", json={
        "mission_name": "Fault Test",
        "profile_id": "standard_isr",
        "engine_id": ENGINE_ID,
        "duration_s": MISSION_DURATION_S,
    })
    assert res.status_code == 200

    # 'sudden' pattern so the residual deviation is immediate and the
    # no-model rule fallback records a detection within the test window.
    inj = client.post("/api/v1/faults/inject", json={
        "engine_id": ENGINE_ID,
        "fault_type": "injector_degradation",
        "severity": 0.7,
        "duration_sec": 4.0,
        "pattern": "sudden",
    })
    assert inj.status_code == 200
    assert inj.json()["success"] is True

    time.sleep(2.5)
    faults = client.get(f"/api/v1/engines/{ENGINE_ID}/faults").json()["faults"]
    assert len(faults) > 0
    assert faults[-1]["fault_type"] == "injector_degradation"


def test_fault_injection_requires_running_mission(client):
    stop_if_running(client)
    inj = client.post("/api/v1/faults/inject", json={
        "engine_id": ENGINE_ID,
        "fault_type": "misfire",
        "severity": 0.5,
        "duration_sec": 10,
    })
    assert inj.status_code == 409


def test_websocket_broadcast(client):
    stop_if_running(client)
    client.post("/api/v1/missions", json={
        "mission_name": "WS Test",
        "profile_id": "standard_isr",
        "engine_id": ENGINE_ID,
        "duration_s": MISSION_DURATION_S,
    })
    with client.websocket_connect(f"/ws/telemetry/{ENGINE_ID}") as ws:
        seen_twin = False
        seen_telemetry = False
        for _ in range(30):
            msg = ws.receive_json()
            if msg["event"] == "twin_state_update":
                seen_twin = True
                assert "health_index" in msg["payload"]
                assert "rul_estimate" in msg["payload"]
            if msg["event"] == "telemetry_update":
                seen_telemetry = True
                assert "rpm" in msg["payload"]
            if seen_twin and seen_telemetry:
                break
        assert seen_twin and seen_telemetry


def test_report_generation(client):
    completed = []
    for _ in range(30):  # wait up to ~15s for a completed mission
        missions = client.get("/api/v1/missions/list").json()
        completed = [m for m in missions if m["status"] == "completed"]
        if completed:
            break
        time.sleep(0.5)
    assert completed, "no completed mission to report on"
    mission_id = completed[0]["mission_id"]

    res = client.post(f"/api/v1/reports/{mission_id}/generate")
    assert res.status_code == 200
    report = res.json()
    assert report["mission_id"] == mission_id
    assert report["telemetry_rows"] > 0
    assert report["health_index"]["average"] is not None

    fetch = client.get(f"/api/v1/reports/{mission_id}")
    assert fetch.status_code == 200
    assert fetch.json()["mission_id"] == mission_id


def test_start_mission_validates_profile_and_engine(client):
    """Unknown profile/engine must be rejected up front, not crash the sim loop."""
    stop_if_running(client)
    r = client.post("/api/v1/missions", json={
        "profile_id": "no_such_profile", "engine_id": ENGINE_ID, "duration_s": 2})
    assert r.status_code == 422

    r = client.post("/api/v1/missions", json={
        "profile_id": "standard_isr", "engine_id": "ENG-GHOST", "duration_s": 2})
    assert r.status_code == 404

    r = client.post("/api/v1/simulation/start", json={
        "profile_id": "no_such_profile", "engine_id": ENGINE_ID})
    assert r.status_code == 422


def test_ingest_accepts_expected_sensor_fields(client):
    """Rows streamed by the standalone simulator carry expected_* columns;
    the twin must use them so residuals cancel transients exactly."""
    from datetime import datetime, timezone
    from uuid import uuid4

    from backend.database import SessionLocal
    from backend.models import Mission

    stop_if_running(client)
    mission_id = f"M-INGEST-{uuid4().hex[:8].upper()}"
    db = SessionLocal()
    try:
        if db.get(Mission, mission_id) is None:
            db.add(Mission(
                id=mission_id, engine_id=ENGINE_ID, profile_id="standard_isr",
                mission_name="Ingest expected-fields test",
                start_time=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                status="completed"))
            db.commit()
    finally:
        db.close()

    row = {
        "mission_id": mission_id,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "profile_id": "standard_isr", "phase": "cruise", "throttle": 55.0,
        "rpm": 2400.0, "cht": 121.0, "egt": 610.0, "oil_pressure": 4.2,
        "oil_temperature": 90.0, "fuel_flow": 12.0, "vibration_rms": 0.5,
        "battery_voltage": 27.5, "alternator_current": 40.0, "injection_timing": 30.0,
        "altitude": 4000.0, "ambient_temperature": 10.0,
        "expected_cht": 111.0, "expected_egt": 600.0, "expected_oil_pressure": 4.2,
        "expected_oil_temperature": 90.0, "expected_fuel_flow": 12.0,
        "expected_vibration_rms": 0.5,
        "fault_label": "none", "fault_severity": 0.0, "degradation_level": 0.0,
    }
    res = client.post("/api/v1/telemetry/ingest", json=row)
    assert res.status_code == 200
    assert res.json()["accepted"] is True

    # Newest mission for the engine is ours, so /state reflects this ingest.
    state = client.get(f"/api/v1/engines/{ENGINE_ID}/state").json()
    assert state["twin_state"]["mission_id"] == mission_id
    # cht - expected_cht = 10.0 proves the provided expected value was used.
    assert state["twin_state"]["residuals"]["cht"] == pytest.approx(10.0, abs=0.01)


def test_failed_mission_finalization(client):
    """A crashed sim loop must mark the mission 'failed', not 'completed'."""
    from datetime import datetime, timezone

    from backend.database import SessionLocal
    from backend.models import Mission
    from backend.services.simulation_runner import runner

    mission_id = "M-FAIL-TEST"
    db = SessionLocal()
    try:
        if db.get(Mission, mission_id) is None:
            db.add(Mission(
                id=mission_id, engine_id=ENGINE_ID, profile_id="standard_isr",
                mission_name="Crash finalization test",
                start_time=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                status="running"))
            db.commit()
    finally:
        db.close()

    runner._finalize_mission(mission_id, status="failed")

    db = SessionLocal()
    try:
        assert db.get(Mission, mission_id).status == "failed"
    finally:
        db.close()
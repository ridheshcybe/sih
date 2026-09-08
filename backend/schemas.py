"""Pydantic schemas for the SIH26054 backend API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.config import DEFAULT_ENGINE_ID, DEFAULT_PROFILE_ID


class TelemetryIn(BaseModel):
    """One raw telemetry row (as produced by the simulator)."""

    model_config = ConfigDict(extra="ignore")

    mission_id: str
    timestamp: Optional[str] = None
    profile_id: Optional[str] = None
    phase: Optional[str] = None
    throttle: Optional[float] = None
    rpm: Optional[float] = None
    cht: Optional[float] = None
    egt: Optional[float] = None
    oil_pressure: Optional[float] = None
    oil_temperature: Optional[float] = None
    fuel_flow: Optional[float] = None
    vibration_rms: Optional[float] = None
    battery_voltage: Optional[float] = None
    alternator_current: Optional[float] = None
    injection_timing: Optional[float] = None
    altitude: Optional[float] = None
    ambient_temperature: Optional[float] = None
    fault_label: Optional[str] = None
    fault_severity: Optional[float] = None
    degradation_level: Optional[float] = None
    # Optional physics-based expected values (healthy-model output). The
    # standalone simulator sends these so the twin can cancel transients.
    expected_cht: Optional[float] = None
    expected_egt: Optional[float] = None
    expected_oil_pressure: Optional[float] = None
    expected_oil_temperature: Optional[float] = None
    expected_fuel_flow: Optional[float] = None
    expected_vibration_rms: Optional[float] = None


class MissionCreate(BaseModel):
    mission_name: str = "Demo Mission"
    profile_id: str = DEFAULT_PROFILE_ID
    engine_id: str = DEFAULT_ENGINE_ID
    duration_s: Optional[float] = Field(default=None, description="Auto-stop after this many seconds (None = until stopped)")


class SimulationStartIn(BaseModel):
    profile_id: str = DEFAULT_PROFILE_ID
    engine_id: str = DEFAULT_ENGINE_ID
    duration_s: Optional[float] = None


class FaultInjectIn(BaseModel):
    engine_id: str = DEFAULT_ENGINE_ID
    fault_type: str
    severity: float = Field(default=0.6, ge=0.05, le=1.0)
    duration_sec: float = Field(default=240.0, gt=0)
    pattern: str = Field(default="gradual", pattern="^(gradual|sudden)$")
    start_offset_sec: Optional[float] = Field(default=None, description="Mission-relative start time; defaults to now")


class ReplayStartIn(BaseModel):
    mission_id: str
    speed: float = Field(default=5.0, gt=0)


class EngineStopIn(BaseModel):
    engine_id: str = DEFAULT_ENGINE_ID


class SystemHealthOut(BaseModel):
    status: str
    timestamp: str
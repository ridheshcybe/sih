"""SQLAlchemy models for the SIH26054 backend (SQLite)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Base(DeclarativeBase):
    pass


class Engine(Base):
    __tablename__ = "engines"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="OPERATIONAL")
    created_at: Mapped[str] = mapped_column(String(32), default=now_iso)


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    engine_id: Mapped[str] = mapped_column(String(32), index=True)
    profile_id: Mapped[str] = mapped_column(String(64))
    mission_name: Mapped[str] = mapped_column(String(128), default="")
    start_time: Mapped[str] = mapped_column(String(32))
    end_time: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running")


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[str] = mapped_column(String(32))
    profile_id: Mapped[str] = mapped_column(String(64), default="")
    phase: Mapped[str] = mapped_column(String(32), default="")
    throttle: Mapped[float] = mapped_column(Float, default=0.0)
    rpm: Mapped[float] = mapped_column(Float, default=0.0)
    cht: Mapped[float] = mapped_column(Float, default=0.0)
    egt: Mapped[float] = mapped_column(Float, default=0.0)
    oil_pressure: Mapped[float] = mapped_column(Float, default=0.0)
    oil_temperature: Mapped[float] = mapped_column(Float, default=0.0)
    fuel_flow: Mapped[float] = mapped_column(Float, default=0.0)
    vibration_rms: Mapped[float] = mapped_column(Float, default=0.0)
    battery_voltage: Mapped[float] = mapped_column(Float, default=0.0)
    alternator_current: Mapped[float] = mapped_column(Float, default=0.0)
    injection_timing: Mapped[float] = mapped_column(Float, default=0.0)
    altitude: Mapped[float] = mapped_column(Float, default=0.0)
    ambient_temperature: Mapped[float] = mapped_column(Float, default=0.0)
    expected_cht: Mapped[float] = mapped_column(Float, default=0.0)
    expected_egt: Mapped[float] = mapped_column(Float, default=0.0)
    expected_oil_pressure: Mapped[float] = mapped_column(Float, default=0.0)
    expected_oil_temperature: Mapped[float] = mapped_column(Float, default=0.0)
    expected_fuel_flow: Mapped[float] = mapped_column(Float, default=0.0)
    expected_vibration_rms: Mapped[float] = mapped_column(Float, default=0.0)
    fault_label: Mapped[str] = mapped_column(String(64), default="none")
    fault_severity: Mapped[float] = mapped_column(Float, default=0.0)
    degradation_level: Mapped[float] = mapped_column(Float, default=0.0)


class TwinState(Base):
    __tablename__ = "twin_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="OPERATIONAL")
    health_index: Mapped[float] = mapped_column(Float, default=100.0)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    degradation_level: Mapped[float] = mapped_column(Float, default=0.0)
    rul_estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rul_confidence: Mapped[str] = mapped_column(String(16), default="low")
    expected_sensors_json: Mapped[str] = mapped_column(Text, default="{}")
    residuals_json: Mapped[str] = mapped_column(Text, default="{}")
    fault_probs_json: Mapped[str] = mapped_column(Text, default="{}")
    latest_sensors_json: Mapped[str] = mapped_column(Text, default="{}")


class FaultPrediction(Base):
    __tablename__ = "fault_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[str] = mapped_column(String(32))
    fault_type: Mapped[str] = mapped_column(String(64))
    probability: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[float] = mapped_column(Float, default=0.0)


class MaintenanceAdvisory(Base):
    __tablename__ = "maintenance_advisories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[str] = mapped_column(String(32))
    advisory_text: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="LOW")


class MissionReport(Base):
    __tablename__ = "mission_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(String(32), index=True, unique=True)
    summary_json: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[str] = mapped_column(String(32), default=now_iso)
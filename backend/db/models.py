from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.db.database import Base


class EngineStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    FAULT = "fault"


class MissionStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABORTED = "aborted"


class Engine(Base):
    __tablename__ = "engines"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    status = Column(String, default=EngineStatus.ONLINE.value)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    missions = relationship("Mission", back_populates="engine")


class Mission(Base):
    __tablename__ = "missions"

    id = Column(String, primary_key=True, index=True)
    engine_id = Column(String, ForeignKey("engines.id"), nullable=False, index=True)
    profile_id = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default=MissionStatus.SCHEDULED.value, index=True)

    engine = relationship("Engine", back_populates="missions")
    telemetry_records = relationship("Telemetry", back_populates="mission")
    twin_states = relationship("TwinState", back_populates="mission")
    fault_predictions = relationship("FaultPrediction", back_populates="mission")
    maintenance_advisories = relationship("MaintenanceAdvisory", back_populates="mission")
    mission_reports = relationship("MissionReport", back_populates="mission")


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    engine_id = Column(String, ForeignKey("engines.id"), nullable=False, index=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    rpm = Column(Float, nullable=False)
    cht = Column(Float, nullable=False)
    egt = Column(Float, nullable=False)
    oil_pressure = Column(Float, nullable=False)
    oil_temperature = Column(Float, nullable=False)
    fuel_flow = Column(Float, nullable=False)
    vibration_rms = Column(Float, nullable=False)
    battery_voltage = Column(Float, nullable=False)
    alternator_current = Column(Float, nullable=False)
    injection_timing = Column(Float, default=0.0)
    altitude = Column(Float, default=0.0)
    ambient_temperature = Column(Float, default=0.0)
    fault_label = Column(String, default="none")
    fault_severity = Column(Float, default=0.0)
    degradation_level = Column(Float, default=0.0)

    mission = relationship("Mission", back_populates="telemetry_records")
    engine = relationship("Engine", foreign_keys=[engine_id])


class TwinState(Base):
    __tablename__ = "twin_states"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    expected_sensors_json = Column(JSON, nullable=False)
    residuals_json = Column(JSON, nullable=False)
    health_index = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    fault_probs_json = Column(JSON, nullable=True)
    rul_estimate = Column(Float)
    rul_confidence = Column(String)

    mission = relationship("Mission", back_populates="twin_states")


class FaultPrediction(Base):
    __tablename__ = "fault_predictions"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    fault_type = Column(String, nullable=False)
    probability = Column(Float, nullable=False)
    severity = Column(Float, nullable=False)

    mission = relationship("Mission", back_populates="fault_predictions")


class MaintenanceAdvisory(Base):
    __tablename__ = "maintenance_advisories"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    advisory_text = Column(String, nullable=False)
    priority = Column(String, nullable=False)

    mission = relationship("Mission", back_populates="maintenance_advisories")


class MissionReport(Base):
    __tablename__ = "mission_reports"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(String, ForeignKey("missions.id"), nullable=False, index=True)
    summary_json = Column(JSON, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)

    mission = relationship("Mission", back_populates="mission_reports")

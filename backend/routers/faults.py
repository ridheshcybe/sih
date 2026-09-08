"""Fault injection endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.schemas import FaultInjectIn
from backend.services.simulation_runner import runner
from simulator.fault_injection import FAULT_TYPES

router = APIRouter(prefix="/api/v1/faults", tags=["faults"])


@router.post("/inject")
def inject_fault(payload: FaultInjectIn) -> dict:
    if payload.fault_type not in FAULT_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown fault type '{payload.fault_type}'. "
                                                    f"Available: {FAULT_TYPES}")
    if not runner.is_running(payload.engine_id):
        raise HTTPException(status_code=409, detail=f"No mission running on engine {payload.engine_id}. "
                                                    "Start a mission first.")
    fault = runner.inject_fault(
        engine_id=payload.engine_id,
        fault_type=payload.fault_type,
        severity=payload.severity,
        duration_sec=payload.duration_sec,
        pattern=payload.pattern,
        start_offset_sec=payload.start_offset_sec,
    )
    return {
        "success": True,
        "message": f"Fault '{payload.fault_type}' injected on {payload.engine_id} "
                   f"at t={runner.elapsed(payload.engine_id):.1f}s",
        "fault_type": fault.fault_type,
        "severity": fault.severity,
        "start_time_sec": round(fault.start_s, 1),
    }
"""Monitoring, demo control, and simulator routes."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Patient
from app.simulator.engine import SCENARIOS, simulator_engine

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class SimulatorControlRequest(BaseModel):
    patient_code: str = "P101"
    scenario: str = "stable"
    speed: float = 1.0


@router.get("")
async def get_monitoring_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get current monitoring status for all active patients."""
    result = await db.execute(
        select(Patient).where(Patient.deleted_at.is_(None), Patient.monitoring_status == "active")
    )
    patients = result.scalars().all()

    return {
        "active_patients": len(patients),
        "simulator_status": simulator_engine.get_status(),
        "patients": [
            {
                "patient_code": p.patient_code,
                "display_name": p.display_name,
                "risk_state": str(p.current_risk_state.value) if p.current_risk_state else None,
                "risk_score": p.current_risk_score,
                "baseline_status": str(p.baseline_status.value) if p.baseline_status else None,
                "last_update": p.last_update.isoformat() if p.last_update else None,
            }
            for p in patients
        ],
    }


@router.post("/demo/start")
async def start_simulator(
    body: SimulatorControlRequest,
    current_user=Depends(get_current_user),
):
    """Start simulator for a patient with specified scenario."""
    if body.scenario not in SCENARIOS:
        raise HTTPException(400, {"error": {"code": "INVALID_SCENARIO", "message": f"Valid scenarios: {list(SCENARIOS.keys())}", "details": {}}})
    if body.speed <= 0 or body.speed > 100:
        raise HTTPException(400, {"error": {"code": "INVALID_SPEED", "message": "Speed must be between 0.1 and 100", "details": {}}})

    # Get auth token for simulator to use when posting vitals
    from fastapi.security import HTTPAuthorizationCredentials
    token = getattr(current_user, "_token", "")

    await simulator_engine.start(body.patient_code, body.scenario, body.speed)
    return {"status": "started", "patient_code": body.patient_code, "scenario": body.scenario, "speed": body.speed}


@router.post("/demo/pause")
async def pause_simulator(
    body: SimulatorControlRequest,
    current_user=Depends(get_current_user),
):
    await simulator_engine.pause(body.patient_code)
    return {"status": "paused", "patient_code": body.patient_code}


@router.post("/demo/resume")
async def resume_simulator(
    body: SimulatorControlRequest,
    current_user=Depends(get_current_user),
):
    await simulator_engine.resume(body.patient_code)
    return {"status": "resumed", "patient_code": body.patient_code}


@router.post("/demo/stop")
async def stop_simulator(
    body: SimulatorControlRequest,
    current_user=Depends(get_current_user),
):
    await simulator_engine.stop(body.patient_code)
    return {"status": "stopped", "patient_code": body.patient_code}


@router.post("/demo/restart")
async def restart_simulator(
    body: SimulatorControlRequest,
    current_user=Depends(get_current_user),
):
    await simulator_engine.restart(body.patient_code, body.scenario, body.speed)
    return {"status": "restarted", "patient_code": body.patient_code}


@router.post("/demo/reset")
async def reset_simulator(
    body: SimulatorControlRequest,
    current_user=Depends(get_current_user),
):
    await simulator_engine.reset(body.patient_code)
    return {"status": "reset", "patient_code": body.patient_code}


@router.get("/demo/status")
async def get_simulator_status(
    patient_code: str = None,
    current_user=Depends(get_current_user),
):
    return {"simulator": simulator_engine.get_status(patient_code), "available_scenarios": list(SCENARIOS.keys())}


@router.get("/devices")
async def get_monitored_devices(
    current_user=Depends(get_current_user),
):
    """Retrieve telemetry status of connected IoT Bed Monitors."""
    return {
        "connected_devices": 6,
        "devices": [
            {"id": "DEV-BM-01", "name": "Bed Monitor 01", "room": "ICU Room 101", "status": "CONNECTED", "battery": 98, "signal": "STRONG", "last_ping": "2s ago"},
            {"id": "DEV-BM-02", "name": "Bed Monitor 02", "room": "ICU Room 102", "status": "CONNECTED", "battery": 94, "signal": "STRONG", "last_ping": "1s ago"},
            {"id": "DEV-BM-03", "name": "Bed Monitor 03", "room": "ICU Room 103", "status": "CONNECTED", "battery": 87, "signal": "GOOD", "last_ping": "3s ago"},
            {"id": "DEV-BM-04", "name": "Bed Monitor 04", "room": "ICU Room 104", "status": "CONNECTED", "battery": 100, "signal": "STRONG", "last_ping": "1s ago"},
            {"id": "DEV-BM-05", "name": "Bed Monitor 05", "room": "Step-Down 201", "status": "STALE", "battery": 45, "signal": "WEAK", "last_ping": "42s ago"},
            {"id": "DEV-BM-06", "name": "Bed Monitor 06", "room": "Step-Down 202", "status": "CONNECTED", "battery": 91, "signal": "STRONG", "last_ping": "2s ago"},
        ]
    }


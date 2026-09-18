"""Patient clinical data routes: risk, vitals, baseline, explanation."""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    DataQualityEvent,
    Patient,
    PatientBaseline,
    RiskPrediction,
    VitalReading,
)
from app.schemas import DataQualityOut, RiskPredictionOut, VitalReadingOut

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/patients", tags=["patient-data"])


async def _get_patient(identifier: str, db: AsyncSession) -> Patient:
    try:
        val_uuid = uuid.UUID(str(identifier))
        query = select(Patient).where(Patient.id == val_uuid, Patient.deleted_at.is_(None))
    except (ValueError, AttributeError):
        query = select(Patient).where(Patient.patient_code.ilike(str(identifier).strip()), Patient.deleted_at.is_(None))

    result = await db.execute(query)
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(404, {"error": {"code": "PATIENT_NOT_FOUND", "message": f"Patient '{identifier}' not found", "details": {}}})
    return p


@router.get("/{patient_id}/vitals", response_model=list[VitalReadingOut])
async def get_patient_vitals(
    patient_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):

    patient = await _get_patient(patient_id, db)
    result = await db.execute(
        select(VitalReading)
        .where(VitalReading.patient_id == patient.id)
        .order_by(desc(VitalReading.recorded_at))
        .limit(limit)
    )
    return [VitalReadingOut.model_validate(v) for v in result.scalars().all()]


@router.get("/{patient_id}/baseline")
async def get_patient_baseline(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient = await _get_patient(patient_id, db)
    result = await db.execute(
        select(PatientBaseline)
        .where(PatientBaseline.patient_id == patient.id)
        .order_by(desc(PatientBaseline.computed_at))
        .limit(1)
    )
    baseline = result.scalar_one_or_none()
    if not baseline:
        return {"status": "collecting", "patient_id": str(patient.id)}

    return {
        "patient_id": str(patient.id),
        "status": baseline.status.value if hasattr(baseline.status, "value") else baseline.status,
        "sample_count": baseline.sample_count,
        "duration_seconds": baseline.duration_seconds,
        "computed_at": baseline.computed_at.isoformat() if baseline.computed_at else None,
        "stats": {
            "heart_rate": {"mean": baseline.hr_mean, "median": baseline.hr_median, "std": baseline.hr_std, "count": baseline.hr_count},
            "spo2": {"mean": baseline.spo2_mean, "median": baseline.spo2_median, "std": baseline.spo2_std, "count": baseline.spo2_count},
            "respiratory_rate": {"mean": baseline.rr_mean, "median": baseline.rr_median, "std": baseline.rr_std, "count": baseline.rr_count},
            "systolic_bp": {"mean": baseline.sbp_mean, "median": baseline.sbp_median, "std": baseline.sbp_std, "count": baseline.sbp_count},
            "diastolic_bp": {"mean": baseline.dbp_mean, "median": baseline.dbp_median, "std": baseline.dbp_std, "count": baseline.dbp_count},
            "temperature": {"mean": baseline.temp_mean, "median": baseline.temp_median, "std": baseline.temp_std, "count": baseline.temp_count},
        },
    }


@router.get("/{patient_id}/risk", response_model=RiskPredictionOut)
async def get_patient_risk(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient = await _get_patient(patient_id, db)
    result = await db.execute(
        select(RiskPrediction)
        .where(RiskPrediction.patient_id == patient.id)
        .order_by(desc(RiskPrediction.computed_at))
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(404, {"error": {"code": "NO_RISK_DATA", "message": "No risk assessment available yet", "details": {}}})
    return RiskPredictionOut.model_validate(pred)


@router.get("/{patient_id}/risk/explanation")
async def get_risk_explanation(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient = await _get_patient(patient_id, db)

    result = await db.execute(
        select(RiskPrediction)
        .where(RiskPrediction.patient_id == patient.id)
        .order_by(desc(RiskPrediction.computed_at))
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(404, {"error": {"code": "NO_RISK_DATA", "message": "No risk assessment available yet", "details": {}}})
    return {"patient_id": str(patient_id), "computed_at": pred.computed_at.isoformat(), "explanation": pred.explanation or {}}


@router.get("/{patient_id}/risk/why-not")
async def get_why_not_alert(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Explain why no alert was triggered — negative evidence."""
    patient = await _get_patient(patient_id, db)
    result = await db.execute(
        select(RiskPrediction)
        .where(RiskPrediction.patient_id == patient.id)
        .order_by(desc(RiskPrediction.computed_at))
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        return {
            "patient_id": str(patient_id),
            "patient_code": patient.patient_code,
            "why_score_is_low": "No risk assessment available yet — awaiting sufficient vital data",
            "stabilizing_factors": ["Awaiting baseline data"],
            "monitoring_note": "Continued monitoring required. Prototype system.",
            "data_confidence": None,
        }

    features = pred.feature_vector or {}
    risk_score = pred.risk_score

    normal_params = []
    for param, val_key, z_key in [
        ("Heart Rate", "hr_current", "hr_z"),
        ("SpO2", "spo2_current", "spo2_z"),
        ("Respiratory Rate", "rr_current", "rr_z"),
    ]:
        val = features.get(val_key)
        z = features.get(z_key)
        if val is not None and (z is None or abs(z) < 1.5):
            normal_params.append(param)

    stabilizing = []
    if risk_score < 25:
        stabilizing.append("Risk score within stable range")
    if features.get("multiparam_score", 0) < 20:
        stabilizing.append("No multi-parameter concordance pattern")
    if features.get("persistence_hr", 0) < 30 and features.get("persistence_spo2", 0) < 30:
        stabilizing.append("No persistent concerning values")

    return {
        "patient_id": str(patient_id),
        "patient_code": patient.patient_code,
        "current_risk_score": round(risk_score, 1),
        "why_score_is_low": f"Normal parameters: {', '.join(normal_params) or 'Assessment in progress'}",
        "stabilizing_factors": stabilizing,
        "monitoring_note": "Continued monitoring is recommended per standard protocol. This prototype system does not guarantee absence of physiological change.",
        "data_confidence": round(pred.data_confidence, 3) if pred.data_confidence is not None else None,
        "model_status": pred.model_status.value if hasattr(pred.model_status, "value") else str(pred.model_status),
        "safety_note": "Prototype — synthetic data — not clinically validated",
    }


@router.get("/{patient_id}/quality", response_model=DataQualityOut)
async def get_patient_quality(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient = await _get_patient(patient_id, db)
    result = await db.execute(
        select(DataQualityEvent)
        .where(DataQualityEvent.patient_id == patient.id)
        .order_by(desc(DataQualityEvent.created_at))
        .limit(1)
    )
    dqe = result.scalar_one_or_none()
    if not dqe:
        raise HTTPException(404, {"error": {"code": "NO_QUALITY_DATA", "message": "No quality data available", "details": {}}})
    return DataQualityOut.model_validate(dqe)


@router.get("/{patient_id}/history")
async def get_patient_history(
    patient_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient = await _get_patient(patient_id, db)
    result = await db.execute(
        select(RiskPrediction)
        .where(RiskPrediction.patient_id == patient.id)
        .order_by(desc(RiskPrediction.computed_at))
        .limit(limit)
    )
    preds = result.scalars().all()
    return {
        "patient_id": str(patient_id),
        "history": [
            {
                "id": str(p.id),
                "computed_at": p.computed_at.isoformat(),
                "risk_score": p.risk_score,
                "risk_state": p.risk_state.value if hasattr(p.risk_state, "value") else str(p.risk_state),
                "rule_score": p.rule_score,
                "ml_score": p.ml_score,
                "model_status": p.model_status.value if hasattr(p.model_status, "value") else str(p.model_status),
            }
            for p in preds
        ],
    }


@router.get("/{patient_id}/dataset-records")
async def get_patient_dataset_records(
    patient_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient = await _get_patient(patient_id, db)
    from app.models import DatasetRecord
    from app.schemas import DatasetRecordOut

    result = await db.execute(
        select(DatasetRecord)
        .where(DatasetRecord.patient_code == patient.patient_code)
        .order_by(desc(DatasetRecord.recorded_at))
        .limit(limit)
    )
    records = result.scalars().all()
    return {
        "patient_id": str(patient_id),
        "patient_code": patient.patient_code,
        "count": len(records),
        "records": [DatasetRecordOut.model_validate(r) for r in records],
    }

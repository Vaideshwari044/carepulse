"""Patient CRUD routes."""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import MonitoringStatus, Patient
from app.schemas import PatientCreate, PatientListResponse, PatientOut, PatientUpdate

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/patients", tags=["patients"])


async def _get_patient_or_404(identifier: str, db: AsyncSession) -> Patient:
    try:
        val_uuid = uuid.UUID(str(identifier))
        query = select(Patient).where(Patient.id == val_uuid, Patient.deleted_at.is_(None))
    except (ValueError, AttributeError):
        query = select(Patient).where(Patient.patient_code.ilike(str(identifier).strip()), Patient.deleted_at.is_(None))

    result = await db.execute(query)
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PATIENT_NOT_FOUND", "message": f"Patient '{identifier}' not found", "details": {}}},
        )
    return patient



async def _next_patient_code(db: AsyncSession) -> str:
    result = await db.execute(
        select(Patient.patient_code).where(Patient.patient_code.like("P%")).order_by(Patient.created_at.desc())
    )
    codes = [r[0] for r in result.all() if re.match(r"^P\d+$", r[0] or "")]
    if not codes:
        return "P101"
    nums = [int(c[1:]) for c in codes if c and re.match(r"^P\d+$", c)]
    return f"P{max(nums) + 1}"


@router.get("", response_model=PatientListResponse)
async def list_patients(
    search: Optional[str] = Query(None, description="Search by name or code"),
    risk_level: Optional[str] = Query(None),
    monitoring_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Patient).where(Patient.deleted_at.is_(None))

    if search:
        like = f"%{search}%"
        query = query.where(
            (Patient.display_name.ilike(like)) | (Patient.patient_code.ilike(like))
        )
    if monitoring_status:
        try:
            ms = MonitoringStatus(monitoring_status)
            query = query.where(Patient.monitoring_status == ms)
        except ValueError:
            pass

    if not search and not monitoring_status:
        total = (await db.scalar(select(func.count(Patient.id)).where(Patient.deleted_at.is_(None)))) or 0
    else:
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0


    query = query.order_by(Patient.patient_code).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    patients = result.scalars().all()

    return PatientListResponse(
        patients=[PatientOut.model_validate(p) for p in patients],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=PatientOut, status_code=201)
async def create_patient(
    body: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    code = body.patient_code
    if code:
        result = await db.execute(select(Patient).where(Patient.patient_code == code))
        if result.scalar_one_or_none():
            raise HTTPException(409, {"error": {"code": "CODE_TAKEN", "message": f"Patient code {code} already exists", "details": {}}})
    else:
        code = await _next_patient_code(db)

    try:
        ms = MonitoringStatus(body.monitoring_status)
    except ValueError:
        ms = MonitoringStatus.active

    patient = Patient(
        id=uuid.uuid4(),
        patient_code=code,
        display_name=body.display_name,
        monitoring_status=ms,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return PatientOut.model_validate(patient)


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return PatientOut.model_validate(await _get_patient_or_404(patient_id, db))


@router.put("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: str,
    body: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    patient = await _get_patient_or_404(patient_id, db)
    if body.display_name is not None:
        patient.display_name = body.display_name
    if body.monitoring_status is not None:
        try:
            patient.monitoring_status = MonitoringStatus(body.monitoring_status)
        except ValueError:
            pass
    patient.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(patient)
    return PatientOut.model_validate(patient)


@router.delete("/{patient_id}", status_code=204)
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    patient = await _get_patient_or_404(patient_id, db)
    patient.deleted_at = datetime.now(UTC)
    await db.commit()


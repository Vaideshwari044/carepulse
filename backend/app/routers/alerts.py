"""Alert management routes."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Alert, AlertAction, AlertStatus, AuditLog
from app.schemas import AlertActionCreate, AlertOut

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])

VALID_ACTIONS = {"acknowledge", "review", "snooze", "escalate", "note", "not-concerning", "resolve"}


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    patient_id: Optional[uuid.UUID] = Query(None),
    alert_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Alert)
    if patient_id:
        query = query.where(Alert.patient_id == patient_id)
    if alert_status:
        try:
            query = query.where(Alert.status == AlertStatus(alert_status))
        except ValueError:
            pass
    query = query.order_by(Alert.priority.desc(), Alert.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    return [AlertOut.model_validate(a) for a in result.scalars().all()]


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, {"error": {"code": "ALERT_NOT_FOUND", "message": "Alert not found", "details": {}}})
    return AlertOut.model_validate(alert)


@router.post("/{alert_id}/actions", status_code=201)
async def create_alert_action(
    alert_id: uuid.UUID,
    body: AlertActionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, {"error": {"code": "ALERT_NOT_FOUND", "message": "Alert not found", "details": {}}})

    now = datetime.now(UTC)
    response_time = (now - alert.created_at.replace(tzinfo=UTC) if alert.created_at.tzinfo is None else now - alert.created_at).total_seconds()

    action = AlertAction(
        id=uuid.uuid4(),
        alert_id=alert_id,
        user_id=current_user.id,
        action=body.action,
        note=body.note,
        response_time_seconds=response_time,
    )
    db.add(action)

    # Update alert status
    action_to_status = {
        "acknowledge": AlertStatus.acknowledged,
        "review": AlertStatus.reviewed,
        "snooze": AlertStatus.snoozed,
        "escalate": AlertStatus.escalated,
        "resolve": AlertStatus.resolved,
        "not-concerning": AlertStatus.resolved,
    }
    if body.action in action_to_status:
        alert.status = action_to_status[body.action]
        if body.action in ("resolve", "not-concerning"):
            alert.resolved_at = now
        elif body.action == "acknowledge":
            alert.acknowledged_at = now

    # Audit log
    db.add(AuditLog(
        id=uuid.uuid4(),
        user_id=current_user.id,
        action=f"alert.{body.action}",
        resource_type="alert",
        resource_id=str(alert_id),
        details={"note": body.note, "response_time_seconds": response_time},
    ))

    await db.commit()
    return {"status": "ok", "alert_id": str(alert_id), "action": body.action}

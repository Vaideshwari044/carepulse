"""Analytics and model info routes."""
from __future__ import annotations

import json
import os
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import Alert, AlertStatus, ModelVersion, RiskPrediction, User, VitalReading

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["analytics"])


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """System-wide analytics summary."""
    total_vitals = await db.scalar(select(func.count(VitalReading.id)))
    total_predictions = await db.scalar(select(func.count(RiskPrediction.id)))
    open_alerts = await db.scalar(select(func.count(Alert.id)).where(Alert.status == AlertStatus.open))
    
    return {
        "total_vital_readings": total_vitals,
        "total_risk_assessments": total_predictions,
        "open_alerts": open_alerts,
        "safety_note": "RESEARCH DATA / SYNTHETIC DEMO — NOT CLINICALLY VALIDATED",
    }



@router.get("/model")
async def get_model_info(current_user=Depends(get_current_user)):
    """Get current ML model status and metadata."""
    from app.ml.inference import ml_inference
    from app.core.config import get_settings
    settings = get_settings()

    model_card = None
    card_path = settings.MODEL_PATH.replace(".joblib", ".json")
    if os.path.exists(card_path):
        try:
            with open(card_path) as f:
                model_card = json.load(f)
        except Exception:
            pass

    return {
        "model_ready": ml_inference.is_ready(),
        "model_version": ml_inference.model_version,
        "model_status": "ready" if ml_inference.is_ready() else "fallback",
        "fallback_message": "AI model unavailable. Rule-based monitoring fallback is active." if not ml_inference.is_ready() else None,
        "model_card": model_card,
        "safety_note": "Model classification confidence — not probability of illness. Prototype only.",
    }


@router.get("/admin/users")
async def admin_list_users(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Admin: list all users. Requires admin role."""
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "display_name": u.display_name, "role": u.role.value, "is_active": u.is_active} for u in users]

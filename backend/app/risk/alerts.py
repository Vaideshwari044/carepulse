"""Alert engine: deduplication, cooldown, priority scoring."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alert, AlertStatus, AlertType

logger = structlog.get_logger(__name__)


def _compute_signature(patient_id: str, alert_type: str, contributing_params: list, risk_level: str) -> str:
    params_str = "|".join(sorted(contributing_params))
    raw = f"{patient_id}|{alert_type}|{params_str}|{risk_level}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]  # Short signature for storage


def _risk_level_for_score(score: float) -> str:
    if score >= 75:
        return "HIGH_PRIORITY"
    elif score >= 50:
        return "DETERIORATION_WARNING"
    elif score >= 25:
        return "EARLY_CHANGE"
    return "STABLE"


def _alert_type_for_state(state: str) -> AlertType:
    if state == "HIGH_PRIORITY":
        return AlertType.high_priority
    elif state in ("DETERIORATION_WARNING", "EARLY_CHANGE"):
        return AlertType.deterioration
    elif state == "RECOVERY":
        return AlertType.recovery
    return AlertType.deterioration


def _compute_priority(risk_score: float, worsening_factor: float, persistence_factor: float, data_confidence: float, created_at: datetime) -> float:
    now = datetime.now(UTC)
    age_seconds = (now - created_at).total_seconds()
    age_factor = 1.0 - min(age_seconds / 3600.0, 1.0)
    priority = (
        0.40 * (risk_score / 100.0)
        + 0.20 * worsening_factor
        + 0.15 * persistence_factor
        + 0.15 * data_confidence
        + 0.10 * age_factor
    )
    return round(priority, 4)


class AlertEngine:
    def __init__(self, settings=None):
        from app.core.config import get_settings
        s = settings or get_settings()
        self.cooldown = s.ALERT_COOLDOWN_SECONDS
        self.dedup_window = s.ALERT_DEDUP_WINDOW_SECONDS
        self.auto_resolve = s.ALERT_AUTO_RESOLVE_STABLE_SECONDS

    async def process(
        self,
        patient,
        risk_result,
        features: dict,
        trends: dict,
        persists: dict,
        multiparam,
        db: AsyncSession,
    ) -> Optional[Alert]:
        """Process alert for patient. Returns alert if created/updated."""
        risk_score = risk_result.risk_score
        risk_state = None

        if hasattr(patient, "current_risk_state") and patient.current_risk_state:
            risk_state = str(patient.current_risk_state.value if hasattr(patient.current_risk_state, "value") else patient.current_risk_state)

        # Auto-resolve if STABLE for long enough
        if risk_state == "STABLE" and risk_score < 25:
            await self._auto_resolve_alerts(patient.id, db)
            return None

        # Skip alert for INSUFFICIENT_DATA or STABLE
        if risk_state in ("INSUFFICIENT_DATA", "STABLE", None) and risk_score < 25:
            return None

        # Determine contributing parameters
        contributing = []
        for param, z_key in [("HR", "hr_z"), ("SpO2", "spo2_z"), ("RR", "rr_z")]:
            z = features.get(z_key)
            if z is not None and abs(z) >= 2:
                contributing.append(param)

        if not contributing:
            for param, val_key in [("HR", "hr_current"), ("SpO2", "spo2_current"), ("RR", "rr_current")]:
                val = features.get(val_key)
                if val is not None:
                    contributing.append(param)
            if not contributing:
                contributing = ["Multi-param"]

        alert_type = _alert_type_for_state(risk_state or "EARLY_CHANGE")
        risk_level = _risk_level_for_score(risk_score)
        signature = _compute_signature(str(patient.id), alert_type.value, contributing, risk_level)

        now = datetime.now(UTC)
        dedup_cutoff = now - timedelta(seconds=self.dedup_window)
        cooldown_cutoff = now - timedelta(seconds=self.cooldown)

        # Check for existing active alert with same signature
        existing_result = await db.execute(
            select(Alert).where(
                and_(
                    Alert.patient_id == patient.id,
                    Alert.signature == signature,
                    Alert.status.in_(["OPEN", "ACKNOWLEDGED", "SNOOZED", "ESCALATED"]),
                    Alert.created_at >= dedup_cutoff,
                )
            ).order_by(Alert.created_at.desc()).limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            # Update existing alert
            existing.risk_score = risk_score
            existing.priority = _compute_priority(risk_score, 0.5, 0.5, risk_result.data_confidence, existing.created_at)
            existing.last_updated_at = now
            logger.info("alert.updated", patient=patient.patient_code, alert_id=str(existing.id))
            return existing

        # Check cooldown: any recent alert for this patient
        cooldown_result = await db.execute(
            select(Alert).where(
                and_(
                    Alert.patient_id == patient.id,
                    Alert.created_at >= cooldown_cutoff,
                    Alert.status != "RESOLVED",
                )
            ).order_by(Alert.created_at.desc()).limit(1)
        )
        recent = cooldown_result.scalar_one_or_none()
        if recent and risk_score < 75:  # High priority overrides cooldown
            logger.debug("alert.cooldown", patient=patient.patient_code)
            return None

        # Create new alert
        priority = _compute_priority(risk_score, 0.4, 0.4, risk_result.data_confidence, now)
        message = f"Possible physiological deterioration pattern detected. Risk score: {risk_score:.0f}. Parameters: {', '.join(contributing)}."

        alert = Alert(
            id=uuid.uuid4(),
            patient_id=patient.id,
            alert_type=alert_type,
            status=AlertStatus.open,
            signature=signature,
            risk_level=risk_level,
            risk_score=risk_score,
            priority=priority,
            contributing_parameters=contributing,
            message=message,
            details={
                "risk_score": risk_score,
                "rule_score": risk_result.rule_score,
                "ml_score": risk_result.ml_score,
                "model_status": risk_result.model_status,
                "contributing_params": contributing,
            },
        )
        db.add(alert)
        logger.info("alert.created", patient=patient.patient_code, risk_score=risk_score, alert_type=alert_type.value)
        return alert

    async def _auto_resolve_alerts(self, patient_id: uuid.UUID, db: AsyncSession) -> None:
        """Auto-resolve open alerts when patient is stable."""
        now = datetime.now(UTC)
        stable_cutoff = now - timedelta(seconds=self.auto_resolve)
        result = await db.execute(
            select(Alert).where(
                and_(
                    Alert.patient_id == patient_id,
                    Alert.status.in_(["OPEN", "ACKNOWLEDGED"]),
                    Alert.last_updated_at <= stable_cutoff,
                )
            )
        )
        for alert in result.scalars().all():
            alert.status = AlertStatus.resolved
            alert.resolved_at = now
            alert.details = {**(alert.details or {}), "auto_resolved": True, "reason": "AUTO_RECOVERY"}

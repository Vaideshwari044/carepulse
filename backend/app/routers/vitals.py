"""Vital ingestion routes: POST /api/v1/vitals and /api/v1/vitals/batch."""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    Alert,
    DataQualityEvent,
    FeatureSnapshot,
    Patient,
    PatientBaseline,
    QualityState,
    RiskPrediction,
    RiskState,
    VitalReading,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/vitals", tags=["vitals"])

# ─── Validation ranges ────────────────────────────────────────────────────────

HARD_INVALID = {
    "heart_rate": (20.0, 250.0),
    "spo2": (50.0, 100.0),
    "respiratory_rate": (4.0, 60.0),
    "systolic_bp": (50.0, 260.0),
    "diastolic_bp": (30.0, 160.0),
    "temperature": (30.0, 43.0),
}

SOURCES = {"simulator", "dataset_replay", "manual", "device"}


def _validate_vital(field: str, value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    lo, hi = HARD_INVALID[field]
    if not (lo <= value <= hi):
        raise ValueError(f"{field} value {value} outside valid range [{lo}, {hi}]")
    return value


class VitalReadingCreate(BaseModel):
    patient_code: str = Field(..., min_length=1, max_length=20)
    recorded_at: datetime
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[float] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    temperature: Optional[float] = None
    source: str = Field(default="manual", pattern="^(simulator|dataset_replay|manual|device)$")

    @field_validator("heart_rate")
    @classmethod
    def validate_hr(cls, v): return _validate_vital("heart_rate", v)

    @field_validator("spo2")
    @classmethod
    def validate_spo2(cls, v): return _validate_vital("spo2", v)

    @field_validator("respiratory_rate")
    @classmethod
    def validate_rr(cls, v): return _validate_vital("respiratory_rate", v)

    @field_validator("systolic_bp")
    @classmethod
    def validate_sbp(cls, v): return _validate_vital("systolic_bp", v)

    @field_validator("diastolic_bp")
    @classmethod
    def validate_dbp(cls, v): return _validate_vital("diastolic_bp", v)

    @field_validator("temperature")
    @classmethod
    def validate_temp(cls, v): return _validate_vital("temperature", v)

    @model_validator(mode="after")
    def at_least_one_vital(self):
        vitals = [self.heart_rate, self.spo2, self.respiratory_rate, self.systolic_bp, self.diastolic_bp, self.temperature]
        if all(v is None for v in vitals):
            raise ValueError("At least one vital sign must be present")
        return self

    def ensure_utc_recorded_at(self):
        """Ensure recorded_at is timezone-aware UTC."""
        if self.recorded_at.tzinfo is None:
            return self.recorded_at.replace(tzinfo=UTC)
        return self.recorded_at.astimezone(UTC)


class VitalReadingOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    recorded_at: datetime
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[float] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    temperature: Optional[float] = None
    source: str

    model_config = {"from_attributes": True}


class IngestResult(BaseModel):
    status: str  # "accepted" | "duplicate"
    vital_id: Optional[uuid.UUID] = None
    message: str = ""


class BatchIngestResult(BaseModel):
    accepted: int
    duplicated: int
    rejected: int
    results: list[dict]


# Per-patient lock to prevent races
_patient_locks: dict[str, asyncio.Lock] = {}


def _get_patient_lock(patient_code: str) -> asyncio.Lock:
    if patient_code not in _patient_locks:
        _patient_locks[patient_code] = asyncio.Lock()
    return _patient_locks[patient_code]


async def _ingest_single(
    reading: VitalReadingCreate,
    db: AsyncSession,
) -> IngestResult:
    """Core ingestion logic. Must be called within patient lock."""
    # Find patient
    result = await db.execute(
        select(Patient).where(
            Patient.patient_code == reading.patient_code,
            Patient.deleted_at.is_(None),
        )
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "PATIENT_NOT_FOUND", "message": f"Patient {reading.patient_code} not found", "details": {}}},
        )

    recorded_at = reading.ensure_utc_recorded_at()

    # Create vital reading
    vital = VitalReading(
        id=uuid.uuid4(),
        patient_id=patient.id,
        recorded_at=recorded_at,
        heart_rate=reading.heart_rate,
        spo2=reading.spo2,
        respiratory_rate=reading.respiratory_rate,
        systolic_bp=reading.systolic_bp,
        diastolic_bp=reading.diastolic_bp,
        temperature=reading.temperature,
        source=reading.source,
    )

    try:
        db.add(vital)
        await db.flush()  # will raise IntegrityError on duplicate
    except IntegrityError:
        await db.rollback()
        return IngestResult(status="duplicate", message="Duplicate reading (idempotent)")

    # Update patient last_update
    patient.last_update = datetime.now(UTC)
    patient.updated_at = datetime.now(UTC)

    # Run analytics pipeline after storing vital
    try:
        await _run_analytics_pipeline(patient, db)
    except Exception as exc:
        logger.error("analytics_pipeline_error", patient_code=reading.patient_code, error=str(exc))
        # Don't fail ingestion if analytics fails

    await db.commit()

    # Broadcast WebSocket after commit
    try:
        from app.ws.manager import ws_manager
        await ws_manager.broadcast(
            "VITAL_UPDATE",
            patient.patient_code,
            {
                "vital_id": str(vital.id),
                "recorded_at": recorded_at.isoformat(),
                "heart_rate": reading.heart_rate,
                "spo2": reading.spo2,
                "respiratory_rate": reading.respiratory_rate,
                "systolic_bp": reading.systolic_bp,
                "diastolic_bp": reading.diastolic_bp,
                "temperature": reading.temperature,
            },
        )
    except Exception as exc:
        logger.warning("ws_broadcast_error", error=str(exc))

    return IngestResult(status="accepted", vital_id=vital.id, message="Vital reading accepted")


async def _run_analytics_pipeline(patient: Patient, db: AsyncSession) -> None:
    """Run the full analytics pipeline for a patient after ingestion."""
    from app.analytics.baseline import BaselineEngine
    from app.analytics.quality import DataQualityEngine
    from app.analytics.trend import TrendEngine
    from app.analytics.rate import RateEngine
    from app.analytics.persistence import PersistenceEngine
    from app.analytics.multiparam import MultiParameterEngine
    from app.core.config import get_settings
    from app.risk.engine import RiskEngine
    from app.risk.state_machine import RiskStateMachine
    from app.risk.explainability import ExplainabilityEngine
    from app.risk.alerts import AlertEngine
    from app.ml.inference import ml_inference

    settings = get_settings()

    # Get recent readings for sliding window (last 200 for baseline, last 10 for window)
    from sqlalchemy import desc
    result = await db.execute(
        select(VitalReading)
        .where(VitalReading.patient_id == patient.id)
        .order_by(desc(VitalReading.recorded_at))
        .limit(settings.BASELINE_ROLLING_WINDOW)
    )
    all_readings = list(reversed(result.scalars().all()))

    if not all_readings:
        return

    # Convert to dicts
    def reading_to_dict(r: VitalReading) -> dict:
        return {
            "id": str(r.id),
            "recorded_at": r.recorded_at,
            "heart_rate": float(r.heart_rate) if r.heart_rate is not None else None,
            "spo2": float(r.spo2) if r.spo2 is not None else None,
            "respiratory_rate": float(r.respiratory_rate) if r.respiratory_rate is not None else None,
            "systolic_bp": float(r.systolic_bp) if r.systolic_bp is not None else None,
            "diastolic_bp": float(r.diastolic_bp) if r.diastolic_bp is not None else None,
            "temperature": float(r.temperature) if r.temperature is not None else None,
            "source": r.source,
        }

    all_dicts = [reading_to_dict(r) for r in all_readings]

    # Window readings (last 10, within 300s)
    now_utc = datetime.now(UTC)
    window_readings = [
        d for d in all_dicts[-settings.WINDOW_SIZE_READINGS:]
        if (now_utc - d["recorded_at"].replace(tzinfo=UTC if d["recorded_at"].tzinfo is None else None)).total_seconds() <= settings.WINDOW_DURATION_SECONDS
    ]
    if not window_readings:
        window_readings = all_dicts[-settings.WINDOW_SIZE_READINGS:]

    # Compute baseline
    baseline_engine = BaselineEngine(settings)
    current_risk = patient.current_risk_score or 0.0
    baseline = baseline_engine.compute_baseline(all_dicts, current_risk)

    # Save baseline
    bl = PatientBaseline(
        id=uuid.uuid4(),
        patient_id=patient.id,
        status=baseline.status,
        hr_mean=baseline.hr_mean, hr_median=baseline.hr_median, hr_std=baseline.hr_std, hr_count=baseline.hr_count,
        spo2_mean=baseline.spo2_mean, spo2_median=baseline.spo2_median, spo2_std=baseline.spo2_std, spo2_count=baseline.spo2_count,
        rr_mean=baseline.rr_mean, rr_median=baseline.rr_median, rr_std=baseline.rr_std, rr_count=baseline.rr_count,
        sbp_mean=baseline.sbp_mean, sbp_median=baseline.sbp_median, sbp_std=baseline.sbp_std, sbp_count=baseline.sbp_count,
        dbp_mean=baseline.dbp_mean, dbp_median=baseline.dbp_median, dbp_std=baseline.dbp_std, dbp_count=baseline.dbp_count,
        temp_mean=baseline.temp_mean, temp_median=baseline.temp_median, temp_std=baseline.temp_std, temp_count=baseline.temp_count,
        sample_count=baseline.sample_count,
        duration_seconds=baseline.duration_seconds,
        frozen=baseline.frozen,
    )
    db.add(bl)
    patient.baseline_status = baseline.status

    # Data quality
    quality_engine = DataQualityEngine(settings)
    quality = quality_engine.compute_quality(window_readings, now_utc)

    # Save quality event
    dqe = DataQualityEvent(
        id=uuid.uuid4(),
        patient_id=patient.id,
        quality_state=QualityState(quality.state),
        quality_score=quality.score,
        details=quality.details,
    )
    db.add(dqe)

    # Trend, rate, persistence, multiparam
    trend_engine = TrendEngine()
    rate_engine = RateEngine()
    persistence_engine = PersistenceEngine(settings)
    multiparam_engine = MultiParameterEngine()

    params = ["heart_rate", "spo2", "respiratory_rate", "systolic_bp", "diastolic_bp", "temperature"]
    trends = {}
    rates = {}
    persists = {}
    for param in params:
        values = [d.get(param) for d in window_readings]
        timestamps = [d["recorded_at"] for d in window_readings]
        trends[param] = trend_engine.compute_trend(values, timestamps, param)
        rates[param] = rate_engine.compute_rate(values, timestamps, param)
        persists[param] = persistence_engine.compute_persistence(values, param, baseline)

    multiparam = multiparam_engine.compute(window_readings, trends, baseline)

    # Build feature vector
    latest = window_readings[-1] if window_readings else {}
    features = _build_features(latest, baseline, trends, rates, persists, multiparam, quality)

    # Risk engine
    risk_engine = RiskEngine(settings)
    risk_result = risk_engine.compute_risk(features, baseline, quality, window_readings, ml_inference)

    # State machine
    state_machine = RiskStateMachine(settings)
    state_result = state_machine.transition(
        current_score=risk_result.risk_score,
        previous_state=patient.current_risk_state,
        primary_trend_directions={
            "heart_rate": trends.get("heart_rate", {}).get("direction", "STABLE") if isinstance(trends.get("heart_rate"), dict) else getattr(trends.get("heart_rate"), "direction", "STABLE"),
            "spo2": trends.get("spo2", {}).get("direction", "STABLE") if isinstance(trends.get("spo2"), dict) else getattr(trends.get("spo2"), "direction", "STABLE"),
            "respiratory_rate": trends.get("respiratory_rate", {}).get("direction", "STABLE") if isinstance(trends.get("respiratory_rate"), dict) else getattr(trends.get("respiratory_rate"), "direction", "STABLE"),
        },
        quality_score=quality.score,
        baseline_status=baseline.status,
    )

    # Explainability
    explain_engine = ExplainabilityEngine()
    explanation = explain_engine.generate(
        patient_code=patient.patient_code,
        risk_result=risk_result,
        features=features,
        trends=trends,
        persists=persists,
        quality=quality,
        baseline=baseline,
    )

    # Save risk prediction
    pred = RiskPrediction(
        id=uuid.uuid4(),
        patient_id=patient.id,
        risk_score=risk_result.risk_score,
        risk_state=RiskState(state_result.new_state),
        rule_score=risk_result.rule_score,
        ml_score=risk_result.ml_score,
        model_status=risk_result.model_status,
        model_confidence=risk_result.model_confidence,
        data_confidence=risk_result.data_confidence,
        overall_confidence=risk_result.overall_confidence,
        feature_version=settings.FEATURE_VERSION,
        feature_vector=features,
        explanation=explanation,
        previous_state=patient.current_risk_state,
    )
    db.add(pred)

    # Update patient
    patient.current_risk_score = risk_result.risk_score
    patient.current_risk_state = RiskState(state_result.new_state)
    patient.current_confidence = risk_result.overall_confidence

    # Feature snapshot
    snap = FeatureSnapshot(
        id=uuid.uuid4(),
        patient_id=patient.id,
        feature_version=settings.FEATURE_VERSION,
        features=features,
        rule_score=risk_result.rule_score,
        ml_score=risk_result.ml_score,
    )
    db.add(snap)

    # Alert engine
    alert_engine = AlertEngine(settings)
    await alert_engine.process(patient, risk_result, features, trends, persists, multiparam, db)


def _build_features(latest: dict, baseline, trends: dict, rates: dict, persists: dict, multiparam, quality) -> dict:
    """Build the feature dictionary for storage and ML."""
    def _get(obj, attr, default=None):
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    return {
        # Current values
        "hr_current": latest.get("heart_rate"),
        "spo2_current": latest.get("spo2"),
        "rr_current": latest.get("respiratory_rate"),
        "sbp_current": latest.get("systolic_bp"),
        "dbp_current": latest.get("diastolic_bp"),
        "temp_current": latest.get("temperature"),
        # Baseline means
        "hr_baseline": baseline.hr_mean,
        "spo2_baseline": baseline.spo2_mean,
        "rr_baseline": baseline.rr_mean,
        "sbp_baseline": baseline.sbp_mean,
        "dbp_baseline": baseline.dbp_mean,
        "temp_baseline": baseline.temp_mean,
        # Deviations
        "hr_dev": (latest.get("heart_rate") - baseline.hr_mean) if (latest.get("heart_rate") is not None and baseline.hr_mean is not None) else None,
        "spo2_dev": (latest.get("spo2") - baseline.spo2_mean) if (latest.get("spo2") is not None and baseline.spo2_mean is not None) else None,
        "rr_dev": (latest.get("respiratory_rate") - baseline.rr_mean) if (latest.get("respiratory_rate") is not None and baseline.rr_mean is not None) else None,
        "sbp_dev": (latest.get("systolic_bp") - baseline.sbp_mean) if (latest.get("systolic_bp") is not None and baseline.sbp_mean is not None) else None,
        "dbp_dev": (latest.get("diastolic_bp") - baseline.dbp_mean) if (latest.get("diastolic_bp") is not None and baseline.dbp_mean is not None) else None,
        "temp_dev": (latest.get("temperature") - baseline.temp_mean) if (latest.get("temperature") is not None and baseline.temp_mean is not None) else None,
        # Z-scores
        "hr_z": _compute_zscore(latest.get("heart_rate"), baseline.hr_mean, baseline.hr_effective_sd),
        "spo2_z": _compute_zscore(latest.get("spo2"), baseline.spo2_mean, baseline.spo2_effective_sd),
        "rr_z": _compute_zscore(latest.get("respiratory_rate"), baseline.rr_mean, baseline.rr_effective_sd),
        "sbp_z": _compute_zscore(latest.get("systolic_bp"), baseline.sbp_mean, baseline.sbp_effective_sd),
        "dbp_z": _compute_zscore(latest.get("diastolic_bp"), baseline.dbp_mean, baseline.dbp_effective_sd),
        "temp_z": _compute_zscore(latest.get("temperature"), baseline.temp_mean, baseline.temp_effective_sd),
        # Trends
        "hr_trend": _get(trends.get("heart_rate"), "strength", 0.0),
        "spo2_trend": _get(trends.get("spo2"), "strength", 0.0),
        "rr_trend": _get(trends.get("respiratory_rate"), "strength", 0.0),
        "sbp_trend": _get(trends.get("systolic_bp"), "strength", 0.0),
        "dbp_trend": _get(trends.get("diastolic_bp"), "strength", 0.0),
        "temp_trend": _get(trends.get("temperature"), "strength", 0.0),
        # Rates
        "hr_rate": _get(rates.get("heart_rate"), "rate", 0.0),
        "spo2_rate": _get(rates.get("spo2"), "rate", 0.0),
        "rr_rate": _get(rates.get("respiratory_rate"), "rate", 0.0),
        "sbp_rate": _get(rates.get("systolic_bp"), "rate", 0.0),
        "dbp_rate": _get(rates.get("diastolic_bp"), "rate", 0.0),
        "temp_rate": _get(rates.get("temperature"), "rate", 0.0),
        # Persistence
        "persistence_hr": _get(persists.get("heart_rate"), "persistence_score", 0.0),
        "persistence_spo2": _get(persists.get("spo2"), "persistence_score", 0.0),
        "persistence_rr": _get(persists.get("respiratory_rate"), "persistence_score", 0.0),
        "persistence_sbp": _get(persists.get("systolic_bp"), "persistence_score", 0.0),
        # Multi-parameter
        "multiparam_score": _get(multiparam, "score", 0.0),
        "abnormal_primary": _get(multiparam, "abnormal_primary", 0),
        "worsening_primary": _get(multiparam, "worsening_primary", 0),
        "concordance": _get(multiparam, "concordance", 0.0),
        # Quality
        "quality_score": quality.score,
        "primary_count": quality.details.get("primary_count", 0),
        "baseline_ready": 1 if baseline.status == "ready" else 0,
        # Rate severities
        "hr_rate_severity": _get(rates.get("heart_rate"), "severity", 0.0),
        "spo2_rate_severity": _get(rates.get("spo2"), "severity", 0.0),
    }


def _compute_zscore(value, mean, effective_sd):
    if value is None or mean is None or effective_sd is None or effective_sd == 0:
        return None
    return (value - mean) / effective_sd


@router.post("", response_model=IngestResult, status_code=status.HTTP_201_CREATED)
async def ingest_vital(
    reading: VitalReadingCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Ingest a single vital reading. Idempotent on patient+recorded_at+source."""
    lock = _get_patient_lock(reading.patient_code)
    async with lock:
        return await _ingest_single(reading, db)


@router.post("/batch", response_model=BatchIngestResult, status_code=status.HTTP_200_OK)
async def ingest_batch(
    readings: list[VitalReadingCreate],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Batch vital ingestion. Max 500 per batch."""
    if len(readings) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "BATCH_TOO_LARGE", "message": "Maximum batch size is 500", "details": {"max": 500, "received": len(readings)}}},
        )

    results = []
    accepted = 0
    duplicated = 0
    rejected = 0

    for reading in readings:
        try:
            lock = _get_patient_lock(reading.patient_code)
            async with lock:
                result = await _ingest_single(reading, db)
            results.append({"patient_code": reading.patient_code, "status": result.status, "vital_id": str(result.vital_id) if result.vital_id else None})
            if result.status == "accepted":
                accepted += 1
            else:
                duplicated += 1
        except HTTPException as exc:
            results.append({"patient_code": reading.patient_code, "status": "rejected", "error": str(exc.detail)})
            rejected += 1
        except Exception as exc:
            results.append({"patient_code": reading.patient_code, "status": "rejected", "error": str(exc)})
            rejected += 1

    return BatchIngestResult(accepted=accepted, duplicated=duplicated, rejected=rejected, results=results)

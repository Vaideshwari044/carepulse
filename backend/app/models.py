"""CarePulse SQLAlchemy ORM Models."""
from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Dialect-agnostic JSON type that compiles as JSONB on PostgreSQL and JSON elsewhere
JSONType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


# ─── Enums ───────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin = "admin"
    clinician = "clinician"


class MonitoringStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    discharged = "discharged"


class BaselineStatus(str, enum.Enum):
    collecting = "collecting"
    ready = "ready"
    frozen = "frozen"


class RiskState(str, enum.Enum):
    STABLE = "STABLE"
    EARLY_CHANGE = "EARLY_CHANGE"
    DETERIORATION_WARNING = "DETERIORATION_WARNING"
    HIGH_PRIORITY = "HIGH_PRIORITY"
    RECOVERY = "RECOVERY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class AlertStatus(str, enum.Enum):
    open = "OPEN"
    acknowledged = "ACKNOWLEDGED"
    reviewed = "REVIEWED"
    snoozed = "SNOOZED"
    escalated = "ESCALATED"
    resolved = "RESOLVED"


class AlertType(str, enum.Enum):
    deterioration = "DETERIORATION"
    high_priority = "HIGH_PRIORITY"
    data_quality = "DATA_QUALITY"
    recovery = "RECOVERY"


class QualityState(str, enum.Enum):
    good = "GOOD"
    degraded = "DEGRADED"
    stale = "STALE"
    missing = "MISSING"
    invalid = "INVALID"


class ModelStatus(str, enum.Enum):
    ready = "ready"
    fallback = "fallback"
    training = "training"
    failed = "failed"


# ─── Table Models ────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.clinician)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    alert_actions = relationship("AlertAction", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    chat_conversations = relationship("ChatConversation", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hashed_token: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="refresh_tokens")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    monitoring_status: Mapped[MonitoringStatus] = mapped_column(Enum(MonitoringStatus), nullable=False, default=MonitoringStatus.active)
    baseline_status: Mapped[BaselineStatus] = mapped_column(Enum(BaselineStatus), nullable=False, default=BaselineStatus.collecting)
    current_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_risk_state: Mapped[Optional[RiskState]] = mapped_column(Enum(RiskState), nullable=True)
    current_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_update: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    vitals = relationship("VitalReading", back_populates="patient", cascade="all, delete-orphan")
    baselines = relationship("PatientBaseline", back_populates="patient", cascade="all, delete-orphan")
    feature_snapshots = relationship("FeatureSnapshot", back_populates="patient", cascade="all, delete-orphan")
    risk_predictions = relationship("RiskPrediction", back_populates="patient", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="patient", cascade="all, delete-orphan")
    quality_events = relationship("DataQualityEvent", back_populates="patient", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_patients_deleted_code", "deleted_at", "patient_code"),
    )


class VitalReading(Base):
    __tablename__ = "vital_readings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    heart_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spo2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    respiratory_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    systolic_bp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diastolic_bp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    patient = relationship("Patient", back_populates="vitals")

    __table_args__ = (
        Index("idx_vital_readings_pt_recorded", "patient_id", "recorded_at"),
    )


    __table_args__ = (
        UniqueConstraint("patient_id", "recorded_at", "source", name="uq_vital_patient_time_source"),
        Index("idx_vital_patient_recorded", "patient_id", "recorded_at"),
    )


class PatientBaseline(Base):
    __tablename__ = "patient_baselines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    status: Mapped[BaselineStatus] = mapped_column(Enum(BaselineStatus), nullable=False, default=BaselineStatus.collecting)
    hr_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hr_median: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hr_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hr_count: Mapped[int] = mapped_column(Integer, default=0)
    spo2_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spo2_median: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spo2_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spo2_count: Mapped[int] = mapped_column(Integer, default=0)
    rr_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rr_median: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rr_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rr_count: Mapped[int] = mapped_column(Integer, default=0)
    sbp_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sbp_median: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sbp_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sbp_count: Mapped[int] = mapped_column(Integer, default=0)
    dbp_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dbp_median: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dbp_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dbp_count: Mapped[int] = mapped_column(Integer, default=0)
    temp_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_median: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_std: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_count: Mapped[int] = mapped_column(Integer, default=0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)

    patient = relationship("Patient", back_populates="baselines")


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    feature_version: Mapped[str] = mapped_column(String(50), nullable=False, default="fv1")
    features: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    rule_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ml_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    patient = relationship("Patient", back_populates="feature_snapshots")


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_state: Mapped[RiskState] = mapped_column(Enum(RiskState), nullable=False)
    rule_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ml_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_status: Mapped[ModelStatus] = mapped_column(Enum(ModelStatus), nullable=False, default=ModelStatus.fallback)
    model_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    data_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    overall_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feature_version: Mapped[str] = mapped_column(String(50), nullable=False, default="fv1")
    feature_vector: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    explanation: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    previous_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    patient = relationship("Patient", back_populates="risk_predictions")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=AlertStatus.open)

    signature: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    contributing_parameters: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    patient = relationship("Patient", back_populates="alerts")
    actions = relationship("AlertAction", back_populates="alert", cascade="all, delete-orphan")


class AlertAction(Base):
    __tablename__ = "alert_actions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    response_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    alert = relationship("Alert", back_populates="actions")
    user = relationship("User", back_populates="alert_actions")


class DataQualityEvent(Base):
    __tablename__ = "data_quality_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    quality_state: Mapped[QualityState] = mapped_column(Enum(QualityState), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)

    patient = relationship("Patient", back_populates="quality_events")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="audit_logs")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    feature_version: Mapped[str] = mapped_column(String(50), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    status: Mapped[ModelStatus] = mapped_column(Enum(ModelStatus), nullable=False, default=ModelStatus.ready)
    model_path: Mapped[str] = mapped_column(String(255), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Health Assistant Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="chat_conversations")
    patient = relationship("Patient")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.created_at", lazy="selectin")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(50), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)

    conversation = relationship("ChatConversation", back_populates="messages")


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(String(50), nullable=False, default="parquet")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    patient_count: Mapped[int] = mapped_column(Integer, default=0)
    meta_info: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    imports = relationship("DatasetImport", back_populates="dataset", cascade="all, delete-orphan")
    records = relationship("DatasetRecord", back_populates="dataset", cascade="all, delete-orphan")


class DatasetImport(Base):
    __tablename__ = "dataset_imports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    imported_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    patient_count: Mapped[int] = mapped_column(Integer, default=0)
    columns_detected: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    column_mappings: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    summary_stats: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    dataset = relationship("Dataset", back_populates="imports")
    user = relationship("User")


class DatasetRecord(Base):
    __tablename__ = "dataset_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    raw_patient_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)
    heart_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spo2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    respiratory_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    systolic_bp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    diastolic_bp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scenario: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)

    dataset = relationship("Dataset", back_populates="records")

    __table_args__ = (
        Index("idx_dataset_record_patient_time", "patient_code", "recorded_at"),
        Index("idx_dataset_record_dataset_patient", "dataset_id", "patient_code"),
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    patient_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    assignee = relationship("User")
    patient = relationship("Patient")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True)

    user = relationship("User")


"""Pydantic v2 schemas for CarePulse API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ─── Error envelope ──────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Patients ────────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    patient_code: Optional[str] = None
    display_name: str = Field(..., min_length=1, max_length=100)
    monitoring_status: str = "active"


class PatientUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    monitoring_status: Optional[str] = None


class PatientOut(BaseModel):
    id: uuid.UUID
    patient_code: str
    display_name: str
    monitoring_status: str
    baseline_status: str
    current_risk_score: Optional[float] = None
    current_risk_state: Optional[str] = None
    current_confidence: Optional[float] = None
    last_update: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    patients: list[PatientOut]
    total: int
    page: int
    size: int


# ─── Vitals ──────────────────────────────────────────────────────────────────

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


# ─── Risk & Alerts ───────────────────────────────────────────────────────────

class RiskPredictionOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    computed_at: datetime
    risk_score: float
    risk_state: str
    rule_score: Optional[float] = None
    ml_score: Optional[float] = None
    model_status: str
    model_confidence: Optional[float] = None
    data_confidence: Optional[float] = None
    overall_confidence: Optional[float] = None
    explanation: Optional[dict] = None

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    alert_type: str
    status: str
    risk_level: str
    risk_score: float
    priority: float
    contributing_parameters: list
    message: str
    details: dict
    created_at: datetime
    last_updated_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AlertActionCreate(BaseModel):
    action: str = Field(..., pattern="^(acknowledge|review|snooze|escalate|note|not-concerning|resolve)$")
    note: Optional[str] = None


class DataQualityOut(BaseModel):
    patient_id: uuid.UUID
    quality_state: str
    quality_score: float
    details: dict
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Pagination ──────────────────────────────────────────────────────────────

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


# ─── Chatbot ─────────────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[uuid.UUID] = None
    patient_id: Optional[uuid.UUID] = None


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    response: str
    timestamp: datetime
    conversation_id: uuid.UUID
    emergency_warning: bool = False
    messages: Optional[list[ChatMessageOut]] = None


class ChatConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageOut] = []

    model_config = {"from_attributes": True}


# ─── Datasets ────────────────────────────────────────────────────────────────

class DatasetValidateRequest(BaseModel):
    file_path: Optional[str] = None
    column_mappings: Optional[dict[str, str]] = None


class DatasetImportRequest(BaseModel):
    name: str = "Clinical Vitals Dataset"
    file_path: str = "data/clinical_vitals_dataset.csv"
    column_mappings: Optional[dict[str, str]] = None


class DatasetRecordOut(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    patient_code: str
    raw_patient_id: Optional[str] = None
    recorded_at: datetime
    heart_rate: Optional[float] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[float] = None
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    temperature: Optional[float] = None
    raw_label: Optional[str] = None
    scenario: Optional[str] = None

    model_config = {"from_attributes": True}


class DatasetOut(BaseModel):
    id: uuid.UUID
    name: str
    filename: str
    file_format: str
    file_path: str
    row_count: int
    patient_count: int
    is_synthetic: bool
    meta_info: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetImportOut(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    valid_rows: int
    invalid_rows: int
    patient_count: int
    columns_detected: list
    column_mappings: dict
    summary_stats: dict
    imported_at: datetime

    model_config = {"from_attributes": True}


# ─── Tasks & Notifications & Audit ──────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: str = "medium"
    patient_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    priority: str
    status: str
    assignee_id: Optional[uuid.UUID] = None
    patient_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: str
    message: str
    category: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: dict
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


"""Initial schema: all CarePulse tables.

Revision ID: 0001_initial
Revises: 
Create Date: 2026-09-18

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role", sa.Enum("admin", "clinician", name="userrole"), nullable=False, server_default="clinician"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hashed_token", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hashed_token"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # patients
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_code", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("monitoring_status", sa.Enum("active", "paused", "discharged", name="monitoringstatus"), nullable=False, server_default="active"),
        sa.Column("baseline_status", sa.Enum("collecting", "ready", "frozen", name="baselinestatus"), nullable=False, server_default="collecting"),
        sa.Column("current_risk_score", sa.Float(), nullable=True),
        sa.Column("current_risk_state", sa.Enum("STABLE", "EARLY_CHANGE", "DETERIORATION_WARNING", "HIGH_PRIORITY", "RECOVERY", "INSUFFICIENT_DATA", name="riskstate"), nullable=True),
        sa.Column("current_confidence", sa.Float(), nullable=True),
        sa.Column("last_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_code"),
    )
    op.create_index("ix_patients_patient_code", "patients", ["patient_code"])

    # vital_readings
    op.create_table(
        "vital_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("heart_rate", sa.Numeric(6, 2), nullable=True),
        sa.Column("spo2", sa.Numeric(5, 2), nullable=True),
        sa.Column("respiratory_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("systolic_bp", sa.Numeric(6, 2), nullable=True),
        sa.Column("diastolic_bp", sa.Numeric(6, 2), nullable=True),
        sa.Column("temperature", sa.Numeric(5, 2), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", "recorded_at", "source", name="uq_vital_patient_time_source"),
    )
    op.create_index("ix_vital_readings_patient_time", "vital_readings", ["patient_id", "recorded_at"])

    # patient_baselines
    op.create_table(
        "patient_baselines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Enum("collecting", "ready", "frozen", name="baselinestatus"), nullable=False),
        sa.Column("hr_mean", sa.Float(), nullable=True),
        sa.Column("hr_median", sa.Float(), nullable=True),
        sa.Column("hr_std", sa.Float(), nullable=True),
        sa.Column("hr_count", sa.Integer(), nullable=True),
        sa.Column("spo2_mean", sa.Float(), nullable=True),
        sa.Column("spo2_median", sa.Float(), nullable=True),
        sa.Column("spo2_std", sa.Float(), nullable=True),
        sa.Column("spo2_count", sa.Integer(), nullable=True),
        sa.Column("rr_mean", sa.Float(), nullable=True),
        sa.Column("rr_median", sa.Float(), nullable=True),
        sa.Column("rr_std", sa.Float(), nullable=True),
        sa.Column("rr_count", sa.Integer(), nullable=True),
        sa.Column("sbp_mean", sa.Float(), nullable=True),
        sa.Column("sbp_median", sa.Float(), nullable=True),
        sa.Column("sbp_std", sa.Float(), nullable=True),
        sa.Column("sbp_count", sa.Integer(), nullable=True),
        sa.Column("dbp_mean", sa.Float(), nullable=True),
        sa.Column("dbp_median", sa.Float(), nullable=True),
        sa.Column("dbp_std", sa.Float(), nullable=True),
        sa.Column("dbp_count", sa.Integer(), nullable=True),
        sa.Column("temp_mean", sa.Float(), nullable=True),
        sa.Column("temp_median", sa.Float(), nullable=True),
        sa.Column("temp_std", sa.Float(), nullable=True),
        sa.Column("temp_count", sa.Integer(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("frozen", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_baselines_patient_id", "patient_baselines", ["patient_id"])

    # feature_snapshots
    op.create_table(
        "feature_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("feature_version", sa.String(20), nullable=False, server_default="fv1"),
        sa.Column("features", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("rule_score", sa.Float(), nullable=True),
        sa.Column("ml_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feature_snapshots_patient_id", "feature_snapshots", ["patient_id"])

    # risk_predictions
    op.create_table(
        "risk_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_state", sa.Enum("STABLE", "EARLY_CHANGE", "DETERIORATION_WARNING", "HIGH_PRIORITY", "RECOVERY", "INSUFFICIENT_DATA", name="riskstate"), nullable=False),
        sa.Column("rule_score", sa.Float(), nullable=True),
        sa.Column("ml_score", sa.Float(), nullable=True),
        sa.Column("model_status", sa.Enum("ready", "fallback", "training", "failed", name="modelstatus"), nullable=False, server_default="fallback"),
        sa.Column("model_confidence", sa.Float(), nullable=True),
        sa.Column("data_confidence", sa.Float(), nullable=True),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("feature_version", sa.String(20), nullable=True),
        sa.Column("feature_vector", postgresql.JSONB(), nullable=True),
        sa.Column("explanation", postgresql.JSONB(), nullable=True),
        sa.Column("previous_state", sa.Enum("STABLE", "EARLY_CHANGE", "DETERIORATION_WARNING", "HIGH_PRIORITY", "RECOVERY", "INSUFFICIENT_DATA", name="riskstate"), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_predictions_patient_time", "risk_predictions", ["patient_id", "computed_at"])

    # alerts
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.Enum("DETERIORATION", "HIGH_PRIORITY", "DATA_QUALITY", "RECOVERY", name="alerttype"), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "ACKNOWLEDGED", "REVIEWED", "SNOOZED", "ESCALATED", "RESOLVED", name="alertstatus"), nullable=False, server_default="OPEN"),
        sa.Column("signature", sa.String(64), nullable=False),
        sa.Column("risk_level", sa.String(30), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("priority", sa.Float(), nullable=False, server_default="0"),
        sa.Column("contributing_parameters", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_status_priority", "alerts", ["status", "priority"])
    op.create_index("ix_alerts_patient_sig", "alerts", ["patient_id", "signature", "status"])

    # alert_actions
    op.create_table(
        "alert_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("response_time_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_actions_alert_id", "alert_actions", ["alert_id"])

    # data_quality_events
    op.create_table(
        "data_quality_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quality_state", sa.Enum("GOOD", "DEGRADED", "STALE", "MISSING", "INVALID", name="qualitystate"), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dqe_patient_time", "data_quality_events", ["patient_id", "created_at"])

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_time", "audit_logs", ["user_id", "created_at"])

    # model_versions
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_tag", sa.String(50), nullable=False),
        sa.Column("feature_version", sa.String(20), nullable=False),
        sa.Column("model_path", sa.String(500), nullable=False),
        sa.Column("status", sa.Enum("ready", "fallback", "training", "failed", name="modelstatus"), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("model_card", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_tag"),
    )

    # system_settings
    op.create_table(
        "system_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("model_versions")
    op.drop_table("audit_logs")
    op.drop_table("data_quality_events")
    op.drop_table("alert_actions")
    op.drop_table("alerts")
    op.drop_table("risk_predictions")
    op.drop_table("feature_snapshots")
    op.drop_table("patient_baselines")
    op.drop_table("vital_readings")
    op.drop_table("patients")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    # Drop enums
    for enum_name in ["userrole", "monitoringstatus", "baselinestatus", "riskstate", "alerttype", "alertstatus", "qualitystate", "modelstatus"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")

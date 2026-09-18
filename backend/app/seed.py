"""Database seed script: 2 demo users, 5 patients with READY baselines."""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)


async def seed_database():
    """Seed initial demo data."""
    from app.core.config import get_settings
    from app.core.security import hash_password
    from app.database import get_session_factory
    from app.models import (
        Alert,
        AlertType,
        BaselineStatus,
        ModelStatus,
        ModelVersion,
        MonitoringStatus,
        Patient,
        PatientBaseline,
        RiskState,
        SystemSetting,
        User,
        UserRole,
    )
    from sqlalchemy import select

    settings = get_settings()
    factory = get_session_factory()

    async with factory() as db:
        # ── Users ──────────────────────────────────────────────────────────────
        for admin_email in ["admin@carepulse.demo", "admin@carepulse.health"]:
            result = await db.execute(select(User).where(User.email == admin_email))
            if result.scalar_one_or_none() is None:
                admin = User(
                    id=uuid.uuid4(),
                    email=admin_email,
                    hashed_password=hash_password(settings.ADMIN_DEMO_PASSWORD),
                    display_name="Demo Administrator",
                    role=UserRole.admin,
                    is_active=True,
                )
                db.add(admin)
                logger.info("seed.created_user", email=admin_email)

        for clinician_email in ["clinician@carepulse.demo", "clinician@carepulse.health"]:
            result = await db.execute(select(User).where(User.email == clinician_email))
            if result.scalar_one_or_none() is None:
                clinician = User(
                    id=uuid.uuid4(),
                    email=clinician_email,
                    hashed_password=hash_password(settings.CLINICIAN_DEMO_PASSWORD),
                    display_name="Dr. Demo Clinician",
                    role=UserRole.clinician,
                    is_active=True,
                )
                db.add(clinician)
                logger.info("seed.created_user", email=clinician_email)

        # ── Patients with READY baselines ──────────────────────────────────────
        demo_patients = [
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000101"),
                "patient_code": "P101",
                "display_name": "Patient 101 — Stable",
                "scenario": "stable",
                # Normal vitals baseline
                "hr": (72.0, 3.5), "spo2": (98.0, 0.8), "rr": (14.0, 1.2),
                "sbp": (120.0, 5.0), "dbp": (78.0, 3.5), "temp": (37.0, 0.2),
                "risk_score": 8.0, "risk_state": "STABLE",
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000102"),
                "patient_code": "P102",
                "display_name": "Patient 102 — Temporary Variation",
                "scenario": "temporary_variation",
                "hr": (75.0, 4.0), "spo2": (97.5, 0.9), "rr": (14.5, 1.3),
                "sbp": (122.0, 5.5), "dbp": (80.0, 4.0), "temp": (37.1, 0.2),
                "risk_score": 18.0, "risk_state": "STABLE",
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000103"),
                "patient_code": "P103",
                "display_name": "Patient 103 — Deterioration Watch",
                "scenario": "gradual_deterioration",
                "hr": (80.0, 3.8), "spo2": (96.0, 0.9), "rr": (15.0, 1.5),
                "sbp": (125.0, 5.5), "dbp": (82.0, 4.0), "temp": (37.2, 0.25),
                "risk_score": 35.0, "risk_state": "EARLY_CHANGE",
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000104"),
                "patient_code": "P104",
                "display_name": "Patient 104 — Recovery",
                "scenario": "recovery",
                "hr": (88.0, 5.0), "spo2": (95.5, 1.0), "rr": (18.0, 2.0),
                "sbp": (135.0, 6.0), "dbp": (85.0, 4.5), "temp": (37.5, 0.3),
                "risk_score": 28.0, "risk_state": "EARLY_CHANGE",
            },
            {
                "id": uuid.UUID("10000000-0000-0000-0000-000000000105"),
                "patient_code": "P105",
                "display_name": "Patient 105 — Monitoring (Missing Data)",
                "scenario": "missing_data",
                "hr": (70.0, 3.2), "spo2": (98.5, 0.7), "rr": (13.5, 1.1),
                "sbp": (118.0, 4.8), "dbp": (76.0, 3.8), "temp": (36.8, 0.2),
                "risk_score": 12.0, "risk_state": "STABLE",
            },
        ]

        now = datetime.now(UTC)

        for p_data in demo_patients:
            result = await db.execute(select(Patient).where(Patient.patient_code == p_data["patient_code"]))
            if result.scalar_one_or_none() is not None:
                continue

            patient = Patient(
                id=p_data["id"],
                patient_code=p_data["patient_code"],
                display_name=p_data["display_name"],
                monitoring_status=MonitoringStatus.active,
                baseline_status=BaselineStatus.ready,
                current_risk_score=p_data["risk_score"],
                current_risk_state=RiskState(p_data["risk_state"]),
                current_confidence=0.70,
                last_update=now,
            )
            db.add(patient)

            # Create READY baseline
            hr_mean, hr_std = p_data["hr"]
            spo2_mean, spo2_std = p_data["spo2"]
            rr_mean, rr_std = p_data["rr"]
            sbp_mean, sbp_std = p_data["sbp"]
            dbp_mean, dbp_std = p_data["dbp"]
            temp_mean, temp_std = p_data["temp"]

            baseline = PatientBaseline(
                id=uuid.uuid4(),
                patient_id=p_data["id"],
                status=BaselineStatus.ready,
                hr_mean=hr_mean, hr_median=hr_mean, hr_std=hr_std, hr_count=50,
                spo2_mean=spo2_mean, spo2_median=spo2_mean, spo2_std=spo2_std, spo2_count=50,
                rr_mean=rr_mean, rr_median=rr_mean, rr_std=rr_std, rr_count=50,
                sbp_mean=sbp_mean, sbp_median=sbp_mean, sbp_std=sbp_std, sbp_count=50,
                dbp_mean=dbp_mean, dbp_median=dbp_mean, dbp_std=dbp_std, dbp_count=50,
                temp_mean=temp_mean, temp_median=temp_mean, temp_std=temp_std, temp_count=50,
                sample_count=50,
                duration_seconds=1200.0,  # 20 minutes
                frozen=False,
            )
            db.add(baseline)
            logger.info("seed.created_patient", patient_code=p_data["patient_code"])

        # ── System settings ────────────────────────────────────────────────────
        settings_to_seed = [
            ("demo_mode", "true", "Demo mode enabled"),
            ("simulator_speed", "1.0", "Default simulator speed multiplier"),
            ("alert_age_horizon_seconds", "3600", "Alert age horizon for priority calculation"),
        ]
        from sqlalchemy import select as sel_
        from app.models import SystemSetting
        for key, value, description in settings_to_seed:
            result = await db.execute(sel_(SystemSetting).where(SystemSetting.key == key))
            if result.scalar_one_or_none() is None:
                db.add(SystemSetting(id=uuid.uuid4(), key=key, value=value, description=description))

        await db.commit()
        logger.info("seed.complete")


if __name__ == "__main__":
    asyncio.run(seed_database())

"""FastAPI Router for Report Generation & Export (/api/v1/reports)."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Alert, DatasetRecord, Patient, RiskPrediction, User, VitalReading

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
async def get_reports_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve summary metadata of available report types."""
    patient_count = await db.scalar(select(func.count(Patient.id))) or 0
    alert_count = await db.scalar(select(func.count(Alert.id))) or 0
    record_count = await db.scalar(select(func.count(DatasetRecord.id))) or 0


    return {
        "reports_available": [
            {
                "id": "patient_monitoring",
                "title": "Patient Monitoring Report",
                "description": "Comprehensive vitals, baselines, and risk scores across all active patients",
                "format": ["CSV", "PDF"],
            },
            {
                "id": "risk_summary",
                "title": "Clinical Risk & Early Warning Summary",
                "description": "Risk distribution, contributing factors, and deterioration timelines",
                "format": ["CSV", "PDF"],
            },
            {
                "id": "alert_history",
                "title": "Alert & Intervention Audit Report",
                "description": "Alert triggers, resolution times, and clinician intervention notes",
                "format": ["CSV", "PDF"],
            },
            {
                "id": "dataset_quality",
                "title": "Dataset & Ingestion Quality Report",
                "description": "Data completeness, physiological bounds validation, and mapping metrics",
                "format": ["CSV", "PDF"],
            },
        ],
        "generated_at": datetime.now(UTC).isoformat(),
        "stats": {
            "patients": patient_count,
            "alerts": alert_count,
            "dataset_records": record_count,
        },
    }


@router.get("/export/csv")
async def export_csv_report(
    report_type: str = Query(..., description="patient_monitoring | risk_summary | alert_history | dataset_records"),
    patient_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export requested report data as CSV file."""
    output = io.StringIO()

    if report_type == "patient_monitoring":
        query = select(Patient)
        if patient_id:
            query = query.where(Patient.id == patient_id)
        result = await db.execute(query)
        patients = result.scalars().all()

        writer = csv.writer(output)
        writer.writerow(["Patient ID", "Patient Code", "Display Name", "Monitoring Status", "Baseline Status", "Risk Score", "Risk State", "Last Update"])
        for p in patients:
            writer.writerow([
                str(p.id),
                p.patient_code,
                p.display_name,
                p.monitoring_status,
                p.baseline_status,
                p.current_risk_score or "",
                p.current_risk_state or "STABLE",
                p.last_update.isoformat() if p.last_update else "",
            ])
        filename = f"carepulse_patients_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"

    elif report_type == "alert_history":
        query = select(Alert).order_by(desc(Alert.created_at))
        if patient_id:
            query = query.where(Alert.patient_id == patient_id)
        result = await db.execute(query)
        alerts = result.scalars().all()

        writer = csv.writer(output)
        writer.writerow(["Alert ID", "Patient ID", "Alert Type", "Status", "Risk Level", "Risk Score", "Message", "Created At", "Acknowledged At", "Resolved At"])
        for a in alerts:
            writer.writerow([
                str(a.id),
                str(a.patient_id),
                a.alert_type,
                a.status,
                a.risk_level,
                a.risk_score,
                a.message,
                a.created_at.isoformat(),
                a.acknowledged_at.isoformat() if a.acknowledged_at else "",
                a.resolved_at.isoformat() if a.resolved_at else "",
            ])
        filename = f"carepulse_alerts_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"

    else:
        # Default: dataset_records
        query = select(DatasetRecord).order_by(desc(DatasetRecord.recorded_at)).limit(1000)
        result = await db.execute(query)
        records = result.scalars().all()

        writer = csv.writer(output)
        writer.writerow(["Record ID", "Patient Code", "Recorded At", "Heart Rate", "SpO2", "Resp Rate", "Systolic BP", "Diastolic BP", "Temperature", "Label", "Scenario"])
        for r in records:
            writer.writerow([
                str(r.id),
                r.patient_code,
                r.recorded_at.isoformat(),
                r.heart_rate or "",
                r.spo2 or "",
                r.respiratory_rate or "",
                r.systolic_bp or "",
                r.diastolic_bp or "",
                r.temperature or "",
                r.raw_label or "",
                r.scenario or "",
            ])
        filename = f"carepulse_records_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

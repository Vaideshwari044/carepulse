"""Dataset Ingestion & Quality Analysis Pipeline for CarePulse.

Provides:
- Auto-detection and configurable column mapping.
- Physiologically grounded validation & missing value analysis.
- De-identification of patient IDs to stable CP-XXXX format.
- Ingestion into dataset_records, patients, and vital_readings tables.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BaselineStatus,
    Dataset,
    DatasetImport,
    DatasetRecord,
    MonitoringStatus,
    Patient,
    PatientBaseline,
    VitalReading,
)

logger = structlog.get_logger(__name__)

# Standard vital field aliases for auto-detection
COLUMN_ALIASES = {
    "heart_rate": ["heart_rate", "hr", "pulse", "bpm", "heartrate", "heart_rate_bpm", "heart rate (bpm)"],
    "spo2": ["spo2", "oximeter", "oxygen", "o2_sat", "o2", "spo2_pct", "sat", "spo2 level (%)"],
    "respiratory_rate": ["respiratory_rate", "rr", "resp_rate", "respiration", "resp"],
    "systolic_bp": ["systolic_bp", "sbp", "sys_bp", "systolic", "bp_sys", "systolic blood pressure (mmHg)"],
    "diastolic_bp": ["diastolic_bp", "dbp", "dia_bp", "diastolic", "bp_dia", "diastolic blood pressure (mmHg)"],
    "temperature": ["temperature", "temp", "body_temp", "temp_c", "body temperature (°c)", "body temperature (c)", "body temperature (c)"],
    "patient_id": ["patient_id", "patient_code", "subject_id", "patient", "pid", "id", "patient number"],
    "recorded_at": ["recorded_at", "timestamp", "time", "date", "datetime", "recorded_time"],
    "raw_label": ["label", "risk", "outcome", "target", "condition", "status", "class", "predicted disease"],
}

# Physiological Hard Validity Bounds
BOUNDS = {
    "heart_rate": (20.0, 250.0),
    "spo2": (50.0, 100.0),
    "respiratory_rate": (4.0, 60.0),
    "systolic_bp": (40.0, 300.0),
    "diastolic_bp": (20.0, 200.0),
    "temperature": (28.0, 43.0),
}


def auto_detect_mappings(columns: list[str]) -> dict[str, str]:
    """Auto-detect mapping between dataset column names and CarePulse standard vital fields."""
    mapping = {}
    used_cols = set()

    for target_field, aliases in COLUMN_ALIASES.items():
        for col in columns:
            clean_col = col.lower().strip()
            if clean_col in aliases and col not in used_cols:
                mapping[target_field] = col
                used_cols.add(col)
                break

    return mapping


def read_dataset_file(file_path: str) -> pd.DataFrame:
    """Read dataset from CSV, Parquet, or JSON file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset file not found at {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".parquet":
        return pd.read_parquet(file_path)
    elif ext in (".csv", ".txt"):
        return pd.read_csv(file_path)
    elif ext == ".json":
        return pd.read_json(file_path)
    else:
        raise ValueError(f"Unsupported dataset format: {ext}")


def validate_and_analyze_dataset(
    df: pd.DataFrame,
    column_mappings: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Validate dataset rows, compute quality metrics and missing value summary."""
    columns = df.columns.tolist()
    mappings = column_mappings or auto_detect_mappings(columns)

    total_rows = len(df)
    missing_summary = {}
    invalid_rows_count = 0

    patient_col = mappings.get("patient_id")
    time_col = mappings.get("recorded_at")

    patient_count = df[patient_col].nunique() if patient_col and patient_col in df.columns else 1

    # Check vital sign missingness & out-of-bounds invalidity
    for field, (lo, hi) in BOUNDS.items():
        src_col = mappings.get(field)
        if src_col and src_col in df.columns:
            series = pd.to_numeric(df[src_col], errors="coerce")
            n_missing = int(series.isnull().sum())
            n_invalid = int(((series < lo) | (series > hi)).sum())
            missing_summary[field] = {
                "detected_column": src_col,
                "missing_count": n_missing,
                "invalid_count": n_invalid,
                "valid_count": int(((series >= lo) & (series <= hi)).sum()),
                "missing_pct": round((n_missing / max(total_rows, 1)) * 100, 1),
            }
            invalid_rows_count += n_invalid
        else:
            missing_summary[field] = {
                "detected_column": None,
                "missing_count": total_rows,
                "invalid_count": 0,
                "valid_count": 0,
                "missing_pct": 100.0,
            }

    valid_rows = max(0, total_rows - invalid_rows_count)

    # Determine Quality Status
    if invalid_rows_count == 0 and valid_rows > 0:
        quality_indicator = "GOOD"
    elif invalid_rows_count < (total_rows * 0.2):
        quality_indicator = "WARNING"
    else:
        quality_indicator = "ERROR"

    return {
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows_count,
        "patient_count": patient_count,
        "columns_detected": columns,
        "column_mappings": mappings,
        "missing_summary": missing_summary,
        "quality_indicator": quality_indicator,
    }


async def ingest_dataset_pipeline(
    dataset_name: str,
    file_path: str,
    column_mappings: Optional[dict[str, str]] = None,
    user_id: Optional[uuid.UUID] = None,
    db: Optional[AsyncSession] = None,
) -> tuple[Dataset, DatasetImport, dict]:
    """Execute complete dataset ingestion pipeline.

    1. Reads dataset file.
    2. Validates columns & maps fields.
    3. Normalizes patient IDs (CP-XXXX de-identified format).
    4. Saves Dataset, DatasetImport, and DatasetRecord entries into DB.
    5. Syncs records into CarePulse Patient and VitalReading entities.
    """
    df = read_dataset_file(file_path)
    analysis = validate_and_analyze_dataset(df, column_mappings)

    mappings = analysis["column_mappings"]
    file_format = os.path.splitext(file_path)[1].replace(".", "").lower()

    if db is None:
        return None, None, analysis  # Return analysis only if no DB provided

    # Check if dataset entry exists
    result = await db.execute(select(Dataset).where(Dataset.file_path == file_path))
    dataset = result.scalar_one_or_none()

    if dataset is None:
        dataset = Dataset(
            id=uuid.uuid4(),
            name=dataset_name,
            filename=os.path.basename(file_path),
            file_format=file_format,
            file_path=file_path,
            row_count=analysis["total_rows"],
            patient_count=analysis["patient_count"],
            meta_info={
                "columns": analysis["columns_detected"],
                "quality": analysis["quality_indicator"],
            },
            is_synthetic="synthetic" in file_path.lower(),
        )
        db.add(dataset)
        await db.flush()
    else:
        dataset.row_count = analysis["total_rows"]
        dataset.patient_count = analysis["patient_count"]

    # Create DatasetImport record
    dataset_import = DatasetImport(
        id=uuid.uuid4(),
        dataset_id=dataset.id,
        status="completed",
        imported_by=user_id,
        valid_rows=analysis["valid_rows"],
        invalid_rows=analysis["invalid_rows"],
        patient_count=analysis["patient_count"],
        columns_detected=analysis["columns_detected"],
        column_mappings=mappings,
        summary_stats=analysis["missing_summary"],
    )
    db.add(dataset_import)
    await db.flush()

    # Process and import records in batches
    patient_col = mappings.get("patient_id")
    time_col = mappings.get("recorded_at")

    # Generate patient code mapping for de-identification (e.g. CP-0001 or P101)
    unique_raw_pts = df[patient_col].unique().tolist() if patient_col and patient_col in df.columns else ["P101"]
    patient_code_map = {}
    for idx, raw_pt in enumerate(unique_raw_pts):
        raw_str = str(raw_pt)
        if raw_str.startswith("P1") and len(raw_str) == 4:
            patient_code_map[raw_pt] = raw_str  # Preserve P101-P105 demo codes
        else:
            patient_code_map[raw_pt] = f"CP-{idx+1:04d}"

    # Sync CarePulse Patient entities
    carepulse_patients = {}
    for raw_pt, code in patient_code_map.items():
        res = await db.execute(select(Patient).where(Patient.patient_code == code))
        p = res.scalar_one_or_none()
        if p is None:
            p = Patient(
                id=uuid.uuid4(),
                patient_code=code,
                display_name=f"Patient {code}",
                monitoring_status=MonitoringStatus.active,
                baseline_status=BaselineStatus.ready,
            )
            db.add(p)
            await db.flush()
        carepulse_patients[code] = p

    # Build DatasetRecord & VitalReading entries
    now = datetime.now(UTC)
    records_to_add = []
    vitals_to_add = []

    for idx, row in df.iterrows():
        raw_pt = row[patient_col] if patient_col and patient_col in df.columns else "P101"
        code = patient_code_map.get(raw_pt, "CP-0001")
        cp_patient = carepulse_patients[code]

        # Parse timestamp
        rec_time = now
        if time_col and time_col in df.columns and pd.notnull(row[time_col]):
            try:
                rec_time = pd.to_datetime(row[time_col]).to_pydatetime()
                if rec_time.tzinfo is None:
                    rec_time = rec_time.replace(tzinfo=UTC)
            except Exception:
                rec_time = now

        def _val(field):
            col_name = mappings.get(field)
            if col_name and col_name in df.columns and pd.notnull(row[col_name]):
                try:
                    v = float(row[col_name])
                    lo, hi = BOUNDS[field]
                    return v if lo <= v <= hi else None
                except Exception:
                    return None
            return None

        hr = _val("heart_rate")
        spo2 = _val("spo2")
        rr = _val("respiratory_rate")
        sbp = _val("systolic_bp")
        dbp = _val("diastolic_bp")
        temp = _val("temperature")
        label = str(row[mappings["raw_label"]]) if mappings.get("raw_label") and mappings["raw_label"] in df.columns and pd.notnull(row[mappings["raw_label"]]) else None
        scenario = str(row["scenario"]) if "scenario" in df.columns and pd.notnull(row["scenario"]) else None

        rec = DatasetRecord(
            id=uuid.uuid4(),
            dataset_id=dataset.id,
            patient_code=code,
            raw_patient_id=str(raw_pt),
            recorded_at=rec_time,
            heart_rate=hr,
            spo2=spo2,
            respiratory_rate=rr,
            systolic_bp=sbp,
            diastolic_bp=dbp,
            temperature=temp,
            raw_label=label,
            scenario=scenario,
            extra_data={"row_idx": idx},
        )
        records_to_add.append(rec)

        # Sync to vital_readings for recent samples
        if idx < 5000:  # Cap sync for fast database ingestion
            v = VitalReading(
                id=uuid.uuid4(),
                patient_id=cp_patient.id,
                recorded_at=rec_time,
                heart_rate=hr,
                spo2=spo2,
                respiratory_rate=rr,
                systolic_bp=sbp,
                diastolic_bp=dbp,
                temperature=temp,
                source="dataset_import",
            )
            vitals_to_add.append(v)

        if len(records_to_add) >= 2000:
            db.add_all(records_to_add)
            if vitals_to_add:
                db.add_all(vitals_to_add)
                vitals_to_add = []
            await db.commit()
            records_to_add = []

    if records_to_add or vitals_to_add:
        if records_to_add:
            db.add_all(records_to_add)
        if vitals_to_add:
            db.add_all(vitals_to_add)
        await db.commit()

    logger.info("dataset.ingestion_complete", dataset_name=dataset_name, rows=len(df))

    return dataset, dataset_import, analysis

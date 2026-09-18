"""FastAPI Router for Dataset Ingestion, Explorer, and Quality Reports (/api/v1/datasets)."""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import Dataset, DatasetImport, DatasetRecord, Patient, User
from app.schemas import (
    DatasetImportOut,
    DatasetImportRequest,
    DatasetOut,
    DatasetRecordOut,
    DatasetValidateRequest,
)
from app.services.dataset_ingestion import (
    auto_detect_mappings,
    ingest_dataset_pipeline,
    read_dataset_file,
    validate_and_analyze_dataset,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/datasets", tags=["datasets"])

DEFAULT_DATASET_PATH = "data/clinical_vitals_dataset.csv"
FALLBACK_PARQUET_PATH = "data/training/synthetic_vitals.parquet"


def _resolve_default_file() -> str:
    if os.path.exists(DEFAULT_DATASET_PATH):
        return DEFAULT_DATASET_PATH
    if os.path.exists(FALLBACK_PARQUET_PATH):
        return FALLBACK_PARQUET_PATH
    return DEFAULT_DATASET_PATH


@router.get("", response_model=list[DatasetOut])
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List registered datasets."""
    result = await db.execute(select(Dataset).order_by(desc(Dataset.created_at)))
    datasets = result.scalars().all()
    return [DatasetOut.model_validate(d) for d in datasets]


@router.post("/validate")
async def validate_dataset(
    body: DatasetValidateRequest,
    current_user: User = Depends(get_current_user),
):
    """Validate dataset file, auto-detect column mappings, and compute data quality report."""
    file_path = body.file_path or _resolve_default_file()

    try:
        df = read_dataset_file(file_path)
        analysis = validate_and_analyze_dataset(df, body.column_mappings)
        return {
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "valid": True,
            "analysis": analysis,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "DATASET_VALIDATION_FAILED", "message": str(exc), "details": {}}},
        )


@router.post("/import", response_model=DatasetOut)
async def import_dataset(
    body: DatasetImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Execute dataset ingestion pipeline. Requires Admin role."""
    file_path = body.file_path or _resolve_default_file()

    try:
        dataset, dataset_import, analysis = await ingest_dataset_pipeline(
            dataset_name=body.name,
            file_path=file_path,
            column_mappings=body.column_mappings,
            user_id=current_user.id,
            db=db,
        )
        return DatasetOut.model_validate(dataset)
    except Exception as exc:
        logger.error("dataset.import_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "DATASET_IMPORT_FAILED", "message": str(exc), "details": {}}},
        )


@router.get("/{dataset_id}", response_model=DatasetOut)
async def get_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed dataset metadata."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DATASET_NOT_FOUND", "message": "Dataset not found", "details": {}}},
        )
    return DatasetOut.model_validate(ds)


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview first N records of dataset."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds = result.scalar_one_or_none()

    if ds and os.path.exists(ds.file_path):
        df = read_dataset_file(ds.file_path)
        preview_df = df.head(limit)
        return {
            "dataset_name": ds.name,
            "total_rows": len(df),
            "columns": df.columns.tolist(),
            "preview_rows": preview_df.to_dict(orient="records"),
        }

    # Fallback to dataset_records table
    rec_result = await db.execute(
        select(DatasetRecord)
        .where(DatasetRecord.dataset_id == dataset_id)
        .order_by(DatasetRecord.recorded_at)
        .limit(limit)
    )
    records = rec_result.scalars().all()
    return {
        "dataset_name": ds.name if ds else "Unknown",
        "total_rows": len(records),
        "preview_rows": [DatasetRecordOut.model_validate(r) for r in records],
    }


@router.get("/{dataset_id}/quality")
async def get_dataset_quality_report(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dataset quality report with missing counts, valid counts, and quality status."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DATASET_NOT_FOUND", "message": "Dataset not found", "details": {}}},
        )

    # Get import summary
    imp_result = await db.execute(
        select(DatasetImport)
        .where(DatasetImport.dataset_id == dataset_id)
        .order_by(desc(DatasetImport.imported_at))
        .limit(1)
    )
    imp = imp_result.scalar_one_or_none()

    if os.path.exists(ds.file_path):
        df = read_dataset_file(ds.file_path)
        mappings = imp.column_mappings if imp else None
        analysis = validate_and_analyze_dataset(df, mappings)
        return {
            "dataset_id": str(ds.id),
            "dataset_name": ds.name,
            "file_format": ds.file_format,
            "quality_indicator": analysis["quality_indicator"],
            "total_rows": analysis["total_rows"],
            "valid_rows": analysis["valid_rows"],
            "invalid_rows": analysis["invalid_rows"],
            "patient_count": analysis["patient_count"],
            "columns_detected": analysis["columns_detected"],
            "column_mappings": analysis["column_mappings"],
            "missing_summary": analysis["missing_summary"],
        }

    return {
        "dataset_id": str(ds.id),
        "dataset_name": ds.name,
        "quality_indicator": ds.meta_info.get("quality", "GOOD"),
        "total_rows": ds.row_count,
        "patient_count": ds.patient_count,
        "column_mappings": imp.column_mappings if imp else {},
        "missing_summary": imp.summary_stats if imp else {},
    }


@router.get("/{dataset_id}/records")
async def list_dataset_records(
    dataset_id: uuid.UUID,
    patient_code: Optional[str] = Query(None),
    raw_label: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List dataset records with filtering and pagination."""
    query = select(DatasetRecord).where(DatasetRecord.dataset_id == dataset_id)
    count_query = select(func.count(DatasetRecord.id)).where(DatasetRecord.dataset_id == dataset_id)

    if patient_code:
        query = query.where(DatasetRecord.patient_code == patient_code)
        count_query = count_query.where(DatasetRecord.patient_code == patient_code)

    if raw_label:
        query = query.where(DatasetRecord.raw_label == raw_label)
        count_query = count_query.where(DatasetRecord.raw_label == raw_label)

    total = await db.scalar(count_query) or 0
    query = query.order_by(DatasetRecord.recorded_at.desc()).offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "records": [DatasetRecordOut.model_validate(r) for r in records],
    }


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete dataset entry and imported records."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    ds = result.scalar_one_or_none()
    if ds:
        await db.delete(ds)
        await db.commit()

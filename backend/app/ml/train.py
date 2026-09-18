"""ML training pipeline for CarePulse Random Forest classifier."""
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline

SEED = 42
TARGET_COL = "label"
CLASSES = ["LOW", "MODERATE", "HIGH"]


def _compute_features_for_training(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features to training data."""
    result = df.copy()

    # Deviations
    result["hr_dev"] = result["heart_rate"] - result["hr_baseline"]
    result["spo2_dev"] = result["spo2"] - result["spo2_baseline"]
    result["rr_dev"] = result["respiratory_rate"] - result["rr_baseline"]
    result["sbp_dev"] = result["systolic_bp"] - result["sbp_baseline"]
    result["dbp_dev"] = result["diastolic_bp"] - result["dbp_baseline"]
    result["temp_dev"] = result["temperature"] - result["temp_baseline"]

    # Z-scores (using simple SD estimates)
    SD_FLOORS = {"hr": 3.0, "spo2": 1.0, "rr": 1.5, "sbp": 5.0, "dbp": 4.0, "temp": 0.2}
    result["hr_z"] = result["hr_dev"] / SD_FLOORS["hr"]
    result["spo2_z"] = result["spo2_dev"] / SD_FLOORS["spo2"]
    result["rr_z"] = result["rr_dev"] / SD_FLOORS["rr"]
    result["sbp_z"] = result["sbp_dev"] / SD_FLOORS["sbp"]
    result["dbp_z"] = result["dbp_dev"] / SD_FLOORS["dbp"]
    result["temp_z"] = result["temp_dev"] / SD_FLOORS["temp"]

    # Per-patient rolling trend (slope over last 10 readings)
    for param in ["heart_rate", "spo2", "respiratory_rate"]:
        col = f"{param}_trend"
        result[col] = result.groupby("patient_id")[param].transform(
            lambda x: x.rolling(10, min_periods=2).apply(
                lambda v: (v[-1] - v[0]) / max(len(v) - 1, 1), raw=True
            )
        )

    # Persistence (consecutive readings outside normal)
    def _concerning(row):
        count = 0
        if pd.notnull(row.get("heart_rate")) and (row["heart_rate"] > 100 or row["heart_rate"] < 50):
            count += 1
        if pd.notnull(row.get("spo2")) and row["spo2"] < 94:
            count += 1
        if pd.notnull(row.get("respiratory_rate")) and (row["respiratory_rate"] > 22 or row["respiratory_rate"] < 10):
            count += 1
        return count

    result["abnormal_primary"] = result.apply(_concerning, axis=1)
    result["multiparam_score"] = result["abnormal_primary"] * 30.0

    # Quality proxy
    result["primary_missing"] = result[["heart_rate", "spo2", "respiratory_rate"]].isnull().sum(axis=1)
    result["quality_score"] = 1.0 - 0.15 * result["primary_missing"]
    result["baseline_ready"] = 1

    return result


TRAINING_FEATURES = [
    "heart_rate", "spo2", "respiratory_rate", "systolic_bp", "diastolic_bp", "temperature",
    "hr_baseline", "spo2_baseline", "rr_baseline", "sbp_baseline", "dbp_baseline", "temp_baseline",
    "hr_dev", "spo2_dev", "rr_dev", "sbp_dev", "dbp_dev", "temp_dev",
    "hr_z", "spo2_z", "rr_z", "sbp_z", "dbp_z", "temp_z",
    "heart_rate_trend", "spo2_trend", "respiratory_rate_trend",
    "abnormal_primary", "multiparam_score", "quality_score", "baseline_ready",
]


def train_model(
    data_path: str = "data/training/synthetic_vitals.parquet",
    model_dir: str = "models",
) -> dict:
    """Train Random Forest classifier and save artifacts."""
    print("Loading training data...")
    df = pd.read_parquet(data_path)
    print(f"Loaded {len(df)} rows from {len(df['patient_id'].unique())} patients")

    # Feature engineering
    df = _compute_features_for_training(df)

    # Split by patient (no leakage)
    patients = df["patient_id"].unique().tolist()
    np.random.seed(SEED)
    np.random.shuffle(patients)
    n = len(patients)
    train_pts = patients[:int(0.6 * n)]
    val_pts = patients[int(0.6 * n):int(0.8 * n)]
    test_pts = patients[int(0.8 * n):]

    train = df[df["patient_id"].isin(train_pts)]
    val = df[df["patient_id"].isin(val_pts)]
    test = df[df["patient_id"].isin(test_pts)]

    print(f"Train: {len(train)} rows | Val: {len(val)} rows | Test: {len(test)} rows")

    # Prepare feature matrices
    def _get_xy(split):
        available = [f for f in TRAINING_FEATURES if f in split.columns]
        X = split[available].values.astype(np.float32)
        y = split[TARGET_COL].values
        return X, y, available

    X_train, y_train, feat_cols = _get_xy(train)
    X_val, y_val, _ = _get_xy(val)
    X_test, y_test, _ = _get_xy(test)

    # Pipeline: imputer + RF
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            min_samples_leaf=20,
            class_weight="balanced",
            random_state=SEED,
            n_jobs=-1,
        )),
    ])

    print("Training Random Forest...")
    pipeline.fit(X_train, y_train)

    # Evaluate on test set
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)
    classes = pipeline.classes_

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
    rec = recall_score(y_test, y_pred, average="macro", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=list(classes)).tolist()

    # ROC-AUC OVR
    try:
        roc_auc = roc_auc_score(y_test, y_prob, multi_class="ovr", average="macro")
    except Exception:
        roc_auc = None

    # HIGH recall
    high_recall = report.get("HIGH", {}).get("recall", 0.0)

    # False positive rate for HIGH
    high_idx = list(classes).index("HIGH") if "HIGH" in classes else None
    if high_idx is not None:
        fp = sum(1 for t, p in zip(y_test, y_pred) if p == "HIGH" and t != "HIGH")
        tn_fp = sum(1 for t in y_test if t != "HIGH")
        fpr = fp / max(tn_fp, 1)
    else:
        fpr = None

    metrics = {
        "accuracy": round(acc, 4),
        "macro_precision": round(prec, 4),
        "macro_recall": round(rec, 4),
        "macro_f1": round(f1, 4),
        "roc_auc_ovr": round(roc_auc, 4) if roc_auc is not None else None,
        "high_recall": round(high_recall, 4),
        "high_fpr": round(fpr, 4) if fpr is not None else None,
        "confusion_matrix": cm,
        "classes": list(classes),
        "per_class": {k: {m: round(v, 4) for m, v in v2.items() if isinstance(v2, dict)} for k, v2 in report.items() if isinstance(v2, dict)},
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_test": len(X_test),
    }

    print(f"\nTest Metrics:")
    print(f"  Accuracy:      {acc:.4f}")
    print(f"  Macro F1:      {f1:.4f}")
    print(f"  HIGH Recall:   {high_recall:.4f}")
    print(f"  ROC-AUC (OVR): {roc_auc:.4f}" if roc_auc else "  ROC-AUC: N/A")

    # Save model
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "rf_v1.joblib")
    joblib.dump(pipeline, model_path)
    print(f"\nModel saved to {model_path}")

    # Model card
    model_card = {
        "version": "rf_v1",
        "feature_version": "fv1",
        "algorithm": "RandomForestClassifier",
        "n_estimators": 300,
        "max_depth": 12,
        "min_samples_leaf": 20,
        "class_weight": "balanced",
        "random_state": SEED,
        "n_features": len(feat_cols),
        "feature_names": feat_cols,
        "classes": list(classes),
        "label_description": "prototype engineering labels (simulator-generated, not clinician-annotated)",
        "trained_at": datetime.now(UTC).isoformat(),
        "train_patients": len(train_pts),
        "val_patients": len(val_pts),
        "test_patients": len(test_pts),
        "metrics": metrics,
        "safety_note": "Not clinically validated. For prototype demonstration only. Not for patient care.",
        "data_note": "Trained on synthetic/simulated data only. No real patient data.",
    }

    card_path = os.path.join(model_dir, "rf_v1.json")
    with open(card_path, "w") as f:
        json.dump(model_card, f, indent=2)
    print(f"Model card saved to {card_path}")

    return model_card


if __name__ == "__main__":
    from app.ml.generator import generate_synthetic_dataset
    import os

    data_path = "data/training/synthetic_vitals.parquet"
    if not os.path.exists(data_path):
        print("Generating synthetic dataset...")
        generate_synthetic_dataset(data_path)

    train_model(data_path=data_path, model_dir="models")

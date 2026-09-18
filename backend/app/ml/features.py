"""Feature names and extraction for CarePulse ML pipeline."""
from __future__ import annotations

from typing import Any, Optional
import numpy as np

# 49 features in order
FEATURE_NAMES = [
    # Current values (6)
    "hr_current", "spo2_current", "rr_current", "sbp_current", "dbp_current", "temp_current",
    # Baseline values (6)
    "hr_baseline", "spo2_baseline", "rr_baseline", "sbp_baseline", "dbp_baseline", "temp_baseline",
    # Deviations (6)
    "hr_dev", "spo2_dev", "rr_dev", "sbp_dev", "dbp_dev", "temp_dev",
    # Z-scores (6)
    "hr_z", "spo2_z", "rr_z", "sbp_z", "dbp_z", "temp_z",
    # Trends (6)
    "hr_trend", "spo2_trend", "rr_trend", "sbp_trend", "dbp_trend", "temp_trend",
    # Rates (6)
    "hr_rate", "spo2_rate", "rr_rate", "sbp_rate", "dbp_rate", "temp_rate",
    # Persistence (4)
    "persistence_hr", "persistence_spo2", "persistence_rr", "persistence_sbp",
    # Multi-parameter (4)
    "multiparam_score", "abnormal_primary", "worsening_primary", "concordance",
    # Quality (3)
    "quality_score", "primary_count", "baseline_ready",
    # Rate severities (2)
    "hr_rate_severity", "spo2_rate_severity",
]

assert len(FEATURE_NAMES) == 49, f"Expected 49 features, got {len(FEATURE_NAMES)}"


def features_to_array(features: dict) -> np.ndarray:
    """Convert feature dict to ordered numpy array."""
    return np.array([features.get(k, 0.0) or 0.0 for k in FEATURE_NAMES], dtype=np.float32)

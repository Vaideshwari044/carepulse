"""Baseline engine for CarePulse."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


SD_FLOORS = {
    "heart_rate": 3.0,
    "spo2": 1.0,
    "respiratory_rate": 1.5,
    "systolic_bp": 5.0,
    "diastolic_bp": 4.0,
    "temperature": 0.2,
}


@dataclass
class BaselineResult:
    status: str  # collecting | ready | frozen
    frozen: bool = False
    sample_count: int = 0
    duration_seconds: float = 0.0

    hr_mean: Optional[float] = None
    hr_median: Optional[float] = None
    hr_std: Optional[float] = None
    hr_effective_sd: Optional[float] = None
    hr_count: int = 0

    spo2_mean: Optional[float] = None
    spo2_median: Optional[float] = None
    spo2_std: Optional[float] = None
    spo2_effective_sd: Optional[float] = None
    spo2_count: int = 0

    rr_mean: Optional[float] = None
    rr_median: Optional[float] = None
    rr_std: Optional[float] = None
    rr_effective_sd: Optional[float] = None
    rr_count: int = 0

    sbp_mean: Optional[float] = None
    sbp_median: Optional[float] = None
    sbp_std: Optional[float] = None
    sbp_effective_sd: Optional[float] = None
    sbp_count: int = 0

    dbp_mean: Optional[float] = None
    dbp_median: Optional[float] = None
    dbp_std: Optional[float] = None
    dbp_effective_sd: Optional[float] = None
    dbp_count: int = 0

    temp_mean: Optional[float] = None
    temp_median: Optional[float] = None
    temp_std: Optional[float] = None
    temp_effective_sd: Optional[float] = None
    temp_count: int = 0


def _stats(values: list[float], sd_floor: float) -> tuple:
    """Returns (mean, median, std, effective_sd, count) or (None,None,None,None,0)."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None, None, None, None, 0
    mean = statistics.mean(clean)
    median = statistics.median(clean)
    std = statistics.pstdev(clean) if len(clean) > 1 else 0.0
    effective_sd = max(std, sd_floor)
    return mean, median, std, effective_sd, len(clean)


class BaselineEngine:
    def __init__(self, settings=None):
        from app.core.config import get_settings
        s = settings or get_settings()
        self.min_samples = s.BASELINE_MIN_SAMPLES
        self.min_duration = s.BASELINE_MIN_DURATION_SEC
        self.rolling_window = s.BASELINE_ROLLING_WINDOW
        self.freeze_above = s.BASELINE_FREEZE_ABOVE_RISK

    def compute_baseline(
        self,
        readings: list[dict],
        current_risk_score: float = 0.0,
    ) -> BaselineResult:
        """Compute baseline from list of readings (dicts with vital keys and recorded_at)."""
        if not readings:
            return BaselineResult(status="collecting")

        # Use last rolling_window readings
        window = readings[-self.rolling_window:]

        # Duration check
        times = [r["recorded_at"] for r in window if r.get("recorded_at") is not None]
        if len(times) >= 2:
            t_min = min(times)
            t_max = max(times)
            if t_min.tzinfo is None:
                from datetime import UTC
                t_min = t_min.replace(tzinfo=UTC)
            if t_max.tzinfo is None:
                from datetime import UTC
                t_max = t_max.replace(tzinfo=UTC)
            duration = (t_max - t_min).total_seconds()
        else:
            duration = 0.0

        valid_count = len(window)

        # Check if frozen (risk too high to update baseline)
        if current_risk_score >= self.freeze_above:
            # Still return what we have but mark frozen
            status = "frozen"
        elif valid_count < self.min_samples or duration < self.min_duration:
            status = "collecting"
        else:
            status = "ready"

        # Compute stats
        hr_vals = [r.get("heart_rate") for r in window]
        spo2_vals = [r.get("spo2") for r in window]
        rr_vals = [r.get("respiratory_rate") for r in window]
        sbp_vals = [r.get("systolic_bp") for r in window]
        dbp_vals = [r.get("diastolic_bp") for r in window]
        temp_vals = [r.get("temperature") for r in window]

        hr_mean, hr_med, hr_std, hr_esd, hr_cnt = _stats(hr_vals, SD_FLOORS["heart_rate"])
        spo2_mean, spo2_med, spo2_std, spo2_esd, spo2_cnt = _stats(spo2_vals, SD_FLOORS["spo2"])
        rr_mean, rr_med, rr_std, rr_esd, rr_cnt = _stats(rr_vals, SD_FLOORS["respiratory_rate"])
        sbp_mean, sbp_med, sbp_std, sbp_esd, sbp_cnt = _stats(sbp_vals, SD_FLOORS["systolic_bp"])
        dbp_mean, dbp_med, dbp_std, dbp_esd, dbp_cnt = _stats(dbp_vals, SD_FLOORS["diastolic_bp"])
        temp_mean, temp_med, temp_std, temp_esd, temp_cnt = _stats(temp_vals, SD_FLOORS["temperature"])

        return BaselineResult(
            status=status,
            frozen=(status == "frozen"),
            sample_count=valid_count,
            duration_seconds=duration,
            hr_mean=hr_mean, hr_median=hr_med, hr_std=hr_std, hr_effective_sd=hr_esd, hr_count=hr_cnt,
            spo2_mean=spo2_mean, spo2_median=spo2_med, spo2_std=spo2_std, spo2_effective_sd=spo2_esd, spo2_count=spo2_cnt,
            rr_mean=rr_mean, rr_median=rr_med, rr_std=rr_std, rr_effective_sd=rr_esd, rr_count=rr_cnt,
            sbp_mean=sbp_mean, sbp_median=sbp_med, sbp_std=sbp_std, sbp_effective_sd=sbp_esd, sbp_count=sbp_cnt,
            dbp_mean=dbp_mean, dbp_median=dbp_med, dbp_std=dbp_std, dbp_effective_sd=dbp_esd, dbp_count=dbp_cnt,
            temp_mean=temp_mean, temp_median=temp_med, temp_std=temp_std, temp_effective_sd=temp_esd, temp_count=temp_cnt,
        )

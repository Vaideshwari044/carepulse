"""Data quality engine for CarePulse."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional


@dataclass
class QualityResult:
    score: float  # 0.0 to 1.0
    state: str  # GOOD | DEGRADED | STALE | MISSING | INVALID | INSUFFICIENT_DATA
    details: dict = field(default_factory=dict)


PRIMARY_PARAMS = ["heart_rate", "spo2", "respiratory_rate"]
SECONDARY_PARAMS = ["systolic_bp", "diastolic_bp", "temperature"]


class DataQualityEngine:
    def __init__(self, settings=None):
        from app.core.config import get_settings
        s = settings or get_settings()
        self.stale_after = s.STALE_AFTER_SECONDS
        self.missing_after = s.MISSING_AFTER_SECONDS
        self.degraded_below = s.QUALITY_DEGRADED_BELOW
        self.insufficient_below = s.INSUFFICIENT_DATA_BELOW

    def compute_quality(
        self,
        window_readings: list[dict],
        now: Optional[datetime] = None,
        invalid_count: int = 0,
    ) -> QualityResult:
        """Compute data quality score from the current window."""
        if now is None:
            now = datetime.now(UTC)

        if not window_readings:
            return QualityResult(score=0.0, state="MISSING", details={"reason": "no readings"})

        score = 1.0
        penalties = []
        per_param = {}

        latest = window_readings[-1]
        latest_time = latest.get("recorded_at")
        if latest_time is not None and latest_time.tzinfo is None:
            latest_time = latest_time.replace(tzinfo=UTC)

        primary_count = 0

        for param in PRIMARY_PARAMS:
            # Find most recent non-null reading for this param
            last_val = None
            last_time = None
            for r in reversed(window_readings):
                if r.get(param) is not None:
                    last_val = r.get(param)
                    last_time = r.get("recorded_at")
                    break

            if last_time is not None and last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=UTC)

            if last_val is None or last_time is None:
                # Missing entirely
                age = (now - (latest_time or now)).total_seconds() if latest_time else 999
                if age >= self.missing_after or last_val is None:
                    score -= 0.50
                    penalties.append(f"{param}_missing_gt_90s")
                    per_param[param] = "MISSING"
                else:
                    score -= 0.15
                    penalties.append(f"{param}_missing_current_window")
                    per_param[param] = "MISSING"
            else:
                age = (now - last_time).total_seconds()
                primary_count += 1
                if age > self.missing_after:
                    score -= 0.50
                    penalties.append(f"{param}_missing_gt_90s")
                    per_param[param] = "MISSING"
                elif age > self.stale_after:
                    score -= 0.30
                    penalties.append(f"{param}_stale_gt_30s")
                    per_param[param] = "STALE"
                else:
                    per_param[param] = "GOOD"

        # Invalid/duplicate penalty
        if invalid_count > 0:
            score -= 0.10 * invalid_count
            penalties.append(f"invalid_or_duplicate_{invalid_count}")

        score = max(0.0, min(1.0, score))

        # Determine state
        if score < self.insufficient_below:
            state = "MISSING"
        elif score < self.degraded_below:
            state = "DEGRADED"
        else:
            state = "GOOD"

        return QualityResult(
            score=score,
            state=state,
            details={
                "penalties": penalties,
                "per_param": per_param,
                "primary_count": primary_count,
                "latest_reading_age_seconds": (now - latest_time).total_seconds() if latest_time else None,
            },
        )

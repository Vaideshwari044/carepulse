"""Rate of change engine for CarePulse."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.analytics.trend import SIGNIFICANCE_THRESHOLDS


@dataclass
class RateResult:
    rate: float  # change per minute
    severity: float  # 0-1
    direction: str  # INCREASING | DECREASING | STABLE
    parameter: str = ""


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class RateEngine:
    def compute_rate(
        self,
        values: list[Optional[float]],
        timestamps: list[datetime],
        parameter: str = "heart_rate",
    ) -> RateResult:
        """Compute rate of change using median of last 3 pairwise rates."""
        pairs = [
            (t, v) for t, v in zip(timestamps, values)
            if v is not None and t is not None
        ]

        if len(pairs) < 2:
            return RateResult(rate=0.0, severity=0.0, direction="STABLE", parameter=parameter)

        # Compute pairwise rates (most recent last)
        pairwise = []
        for i in range(1, len(pairs)):
            t_prev, v_prev = pairs[i - 1]
            t_curr, v_curr = pairs[i]
            if t_prev.tzinfo is None:
                from datetime import UTC
                t_prev = t_prev.replace(tzinfo=UTC)
            if t_curr.tzinfo is None:
                from datetime import UTC
                t_curr = t_curr.replace(tzinfo=UTC)
            minutes = (t_curr - t_prev).total_seconds() / 60.0
            minutes = max(minutes, 0.1)
            rate = (v_curr - v_prev) / minutes
            pairwise.append(rate)

        # Use last 3 pairwise rates
        recent = pairwise[-3:]
        median_rate = statistics.median(recent) if recent else 0.0

        S = SIGNIFICANCE_THRESHOLDS.get(parameter, 1.0)
        severity = _clamp(abs(median_rate) / (2 * S), 0.0, 1.0)

        if median_rate > 0.1 * S:
            direction = "INCREASING"
        elif median_rate < -0.1 * S:
            direction = "DECREASING"
        else:
            direction = "STABLE"

        return RateResult(rate=median_rate, severity=severity, direction=direction, parameter=parameter)

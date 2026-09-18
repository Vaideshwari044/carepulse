"""Trend engine: OLS-based trend analysis per vital parameter."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Significance thresholds S per parameter
SIGNIFICANCE_THRESHOLDS = {
    "heart_rate": 2.0,
    "spo2": 0.4,
    "respiratory_rate": 0.8,
    "systolic_bp": 3.0,
    "diastolic_bp": 2.0,
    "temperature": 0.08,
}


@dataclass
class TrendResult:
    direction: str  # INCREASING | DECREASING | STABLE | UNKNOWN
    strength: float  # clamped -3 to 3
    slope: float  # units per minute
    r_squared: float
    parameter: str = ""


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _ols_slope_rsq(x: list[float], y: list[float]) -> tuple[float, float]:
    """Simple OLS regression, returns (slope, r_squared)."""
    n = len(x)
    if n < 2:
        return 0.0, 0.0
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    ss_yy = sum((yi - y_mean) ** 2 for yi in y)
    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    if ss_xx == 0:
        return 0.0, 0.0
    slope = ss_xy / ss_xx
    if ss_yy == 0:
        return slope, 1.0
    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy)
    return slope, r_squared


class TrendEngine:
    def compute_trend(
        self,
        values: list[Optional[float]],
        timestamps: list[datetime],
        parameter: str = "heart_rate",
    ) -> TrendResult:
        """Compute OLS trend for a parameter series."""
        # Filter non-null paired points
        pairs = [
            (t, v) for t, v in zip(timestamps, values)
            if v is not None and t is not None
        ]

        if len(pairs) < 4:
            return TrendResult(direction="UNKNOWN", strength=0.0, slope=0.0, r_squared=0.0, parameter=parameter)

        # X = minutes since first point
        t0 = pairs[0][0]
        if t0.tzinfo is None:
            from datetime import UTC
            t0 = t0.replace(tzinfo=UTC)

        x_vals = []
        y_vals = []
        for t, v in pairs:
            if t.tzinfo is None:
                from datetime import UTC
                t = t.replace(tzinfo=UTC)
            x_vals.append((t - t0).total_seconds() / 60.0)
            y_vals.append(v)

        slope, r_squared = _ols_slope_rsq(x_vals, y_vals)
        S = SIGNIFICANCE_THRESHOLDS.get(parameter, 1.0)
        strength = _clamp(slope / S, -3.0, 3.0)

        if strength > 0.5:
            direction = "INCREASING"
        elif strength < -0.5:
            direction = "DECREASING"
        else:
            direction = "STABLE"

        return TrendResult(direction=direction, strength=strength, slope=slope, r_squared=r_squared, parameter=parameter)

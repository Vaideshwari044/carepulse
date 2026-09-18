"""Persistence engine: consecutive concerning readings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Concerning ranges per parameter
CONCERNING_RANGES = {
    "heart_rate":       {"low": 50.0, "high": 100.0},
    "spo2":             {"low": 94.0, "high": None},
    "respiratory_rate": {"low": 10.0, "high": 22.0},
    "systolic_bp":      {"low": 100.0, "high": 160.0},
    "diastolic_bp":     {"low": 60.0, "high": 100.0},
    "temperature":      {"low": 36.0, "high": 38.0},
}


@dataclass
class PersistenceResult:
    consecutive_concerning: int
    persistence_score: float  # 0-100
    is_persistent: bool
    parameter: str = ""


def _is_concerning(value: Optional[float], parameter: str, z_score: Optional[float] = None) -> bool:
    """A reading is concerning if outside band OR abs(z)>=2 in concerning direction."""
    if value is None:
        return False
    rng = CONCERNING_RANGES.get(parameter)
    if rng is None:
        return False

    low = rng.get("low")
    high = rng.get("high")

    outside_band = False
    if low is not None and value < low:
        outside_band = True
    if high is not None and value > high:
        outside_band = True

    if outside_band:
        return True

    # Check z-score in concerning direction
    if z_score is not None and abs(z_score) >= 2:
        # Concerning direction: check if z is in the direction of concern
        if low is not None and z_score < -2:  # Below normal
            return True
        if high is not None and z_score > 2:   # Above normal
            return True

    return False


class PersistenceEngine:
    def __init__(self, settings=None):
        from app.core.config import get_settings
        s = settings or get_settings()
        self.lookback = s.PERSISTENCE_LOOKBACK
        self.alert_min = s.PERSISTENCE_ALERT_MIN

    def compute_persistence(
        self,
        values: list[Optional[float]],
        parameter: str,
        baseline=None,
        z_scores: Optional[list[Optional[float]]] = None,
    ) -> PersistenceResult:
        """Count consecutive concerning readings from most recent."""
        # Use last lookback readings
        recent = list(zip(values[-self.lookback:], (z_scores[-self.lookback:] if z_scores else [None] * self.lookback)))

        # Count consecutive concerning from end (most recent)
        consecutive = 0
        for v, z in reversed(recent):
            if _is_concerning(v, parameter, z):
                consecutive += 1
            else:
                break

        score = min(100.0 * consecutive / self.alert_min, 100.0)
        is_persistent = consecutive >= self.alert_min

        return PersistenceResult(
            consecutive_concerning=consecutive,
            persistence_score=score,
            is_persistent=is_persistent,
            parameter=parameter,
        )

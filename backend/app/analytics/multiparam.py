"""Multi-parameter concordance scoring."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.analytics.persistence import CONCERNING_RANGES


@dataclass
class MultiParamResult:
    score: float  # 0-100
    abnormal_primary: int
    worsening_primary: int
    abnormal_secondary: int
    concordance: float
    details: dict


def _is_abnormal(value: Optional[float], parameter: str) -> bool:
    if value is None:
        return False
    rng = CONCERNING_RANGES.get(parameter, {})
    low, high = rng.get("low"), rng.get("high")
    if low is not None and value < low:
        return True
    if high is not None and value > high:
        return True
    return False


class MultiParameterEngine:
    def compute(
        self,
        window_readings: list[dict],
        trends: dict,
        baseline,
    ) -> MultiParamResult:
        """Compute multi-parameter concordance score."""
        if not window_readings:
            return MultiParamResult(score=0.0, abnormal_primary=0, worsening_primary=0, abnormal_secondary=0, concordance=0.0, details={})

        latest = window_readings[-1]

        hr = latest.get("heart_rate")
        spo2 = latest.get("spo2")
        rr = latest.get("respiratory_rate")
        sbp = latest.get("systolic_bp")
        dbp = latest.get("diastolic_bp")
        temp = latest.get("temperature")

        # Primary: HR, SpO2, RR
        primary_abnormal = [
            _is_abnormal(hr, "heart_rate"),
            _is_abnormal(spo2, "spo2"),
            _is_abnormal(rr, "respiratory_rate"),
        ]
        abnormal_primary = sum(primary_abnormal)

        # Secondary: SBP, DBP, Temp
        secondary_abnormal = [
            _is_abnormal(sbp, "systolic_bp"),
            _is_abnormal(dbp, "diastolic_bp"),
            _is_abnormal(temp, "temperature"),
        ]
        abnormal_secondary = sum(secondary_abnormal)

        # Trend directions
        def _dir(param):
            t = trends.get(param)
            if t is None:
                return "STABLE"
            return getattr(t, "direction", t.get("direction", "STABLE") if isinstance(t, dict) else "STABLE")

        hr_dir = _dir("heart_rate")
        spo2_dir = _dir("spo2")
        rr_dir = _dir("respiratory_rate")

        # Worsening primary = trending in concerning direction
        def _worsening_primary(param, direction, value):
            if value is None:
                return False
            rng = CONCERNING_RANGES.get(param, {})
            low, high = rng.get("low"), rng.get("high")
            if high is not None and direction == "INCREASING" and (value is None or value >= (high - (high - low) / 2 if low else high * 0.9)):
                return True
            if low is not None and direction == "DECREASING" and (value is None or value <= low * 1.1):
                return True
            return direction == "INCREASING" and high is not None and value > high * 0.8
        
        # Simpler: primary param worsening means trending AWAY from normal
        def _is_worsening(param, direction):
            rng = CONCERNING_RANGES.get(param, {})
            # For HR/RR: worsening = INCREASING (going higher is bad when already high)
            # For SpO2: worsening = DECREASING
            if param == "spo2":
                return direction == "DECREASING"
            return direction == "INCREASING"

        worsening = [
            _is_worsening("heart_rate", hr_dir),
            _is_worsening("spo2", spo2_dir),
            _is_worsening("respiratory_rate", rr_dir),
        ]
        worsening_primary = sum(worsening)

        # Score components (cap at 100)
        score = 0.0
        score += 30 * (abnormal_primary / 3)
        score += 10 * (worsening_primary / 3)
        score += 10 * (abnormal_secondary / 3) * 0.5  # secondary half weight

        # Concordance bonuses
        concordance = 0.0
        hr_inc = hr_dir == "INCREASING"
        spo2_dec = spo2_dir == "DECREASING"
        rr_inc = rr_dir == "INCREASING"

        if hr_inc and spo2_dec:
            concordance += 25
        if spo2_dec and rr_inc:
            concordance += 25
        if hr_inc and rr_inc:
            concordance += 20
        if abnormal_primary >= 2:
            concordance += 15
        if abnormal_primary == 3:
            concordance += 15

        score += concordance
        score = min(100.0, score)

        return MultiParamResult(
            score=score,
            abnormal_primary=abnormal_primary,
            worsening_primary=worsening_primary,
            abnormal_secondary=abnormal_secondary,
            concordance=concordance,
            details={
                "hr_direction": hr_dir,
                "spo2_direction": spo2_dir,
                "rr_direction": rr_dir,
                "primary_abnormal_flags": primary_abnormal,
                "secondary_abnormal_flags": secondary_abnormal,
            },
        )

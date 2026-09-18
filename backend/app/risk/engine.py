"""Hybrid risk engine: rule-based + ML fusion."""
from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RiskResult:
    risk_score: float
    rule_score: float
    ml_score: Optional[float]
    model_status: str  # "ready" | "fallback"
    model_confidence: float
    data_confidence: float
    overall_confidence: float
    deviation_score: float = 0.0
    trend_score: float = 0.0
    rate_score: float = 0.0
    persistence_score: float = 0.0
    multiparam_score: float = 0.0
    ml_probabilities: dict = field(default_factory=dict)
    component_weights: dict = field(default_factory=dict)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# Concerning thresholds for deviation scoring
CONCERNING_HIGH = {
    "heart_rate": 100.0,
    "spo2": None,  # Only low is bad for SpO2
    "respiratory_rate": 22.0,
    "systolic_bp": 160.0,
    "diastolic_bp": 100.0,
    "temperature": 38.0,
}
CONCERNING_LOW = {
    "heart_rate": 50.0,
    "spo2": 94.0,
    "respiratory_rate": 10.0,
    "systolic_bp": 100.0,
    "diastolic_bp": 60.0,
    "temperature": 36.0,
}
# Primary params get full weight, secondary get 0.5
PARAM_WEIGHT = {
    "heart_rate": 1.0, "spo2": 1.0, "respiratory_rate": 1.0,
    "systolic_bp": 0.5, "diastolic_bp": 0.5, "temperature": 0.5,
}
PARAM_KEYS = {
    "heart_rate": ("hr_z", "hr_current"),
    "spo2": ("spo2_z", "spo2_current"),
    "respiratory_rate": ("rr_z", "rr_current"),
    "systolic_bp": ("sbp_z", "sbp_current"),
    "diastolic_bp": ("dbp_z", "dbp_current"),
    "temperature": ("temp_z", "temp_current"),
}
TREND_KEYS = {
    "heart_rate": "hr_trend", "spo2": "spo2_trend", "respiratory_rate": "rr_trend",
    "systolic_bp": "sbp_trend", "diastolic_bp": "dbp_trend", "temperature": "temp_trend",
}
RATE_KEYS = {
    "heart_rate": "hr_rate_severity", "spo2": "spo2_rate_severity",
}
PERSIST_KEYS = {
    "heart_rate": "persistence_hr", "spo2": "persistence_spo2",
    "respiratory_rate": "persistence_rr", "systolic_bp": "persistence_sbp",
}


class RiskEngine:
    def __init__(self, settings=None):
        from app.core.config import get_settings
        s = settings or get_settings()
        self.W_ML = s.W_ML
        self.W_RULE = s.W_RULE
        self.W_DEV = s.W_DEVIATION
        self.W_TREND = s.W_TREND
        self.W_RATE = s.W_RATE
        self.W_PERSIST = s.W_PERSISTENCE
        self.W_MULTI = s.W_MULTIPARAM

    def _compute_deviation_score(self, features: dict) -> float:
        """Compute deviation component score 0-100."""
        total = 0.0
        max_possible = sum(PARAM_WEIGHT.values())  # 4.5

        for param, (z_key, val_key) in PARAM_KEYS.items():
            z = features.get(z_key)
            value = features.get(val_key)
            w = PARAM_WEIGHT[param]

            if z is None or value is None:
                continue

            low = CONCERNING_LOW.get(param)
            high = CONCERNING_HIGH.get(param)

            # Only score in concerning direction
            concerning = False
            if low is not None and value < low:
                concerning = True
            if high is not None and value > high:
                concerning = True

            if concerning:
                contribution = _clamp(abs(z) * 20, 0, 100) * w
                total += contribution

        if max_possible == 0:
            return 0.0
        return _clamp(total / max_possible, 0, 100)

    def _compute_trend_score(self, features: dict) -> float:
        """Trend contributes when trending in concerning direction."""
        primary_contributions = []
        for param in ["heart_rate", "spo2", "respiratory_rate"]:
            trend_strength = features.get(TREND_KEYS.get(param, ""), 0.0) or 0.0
            # SpO2 - concerning is DECREASING (negative strength)
            # Others - concerning is INCREASING (positive strength)
            if param == "spo2":
                concerning_strength = max(0, -trend_strength)
            else:
                concerning_strength = max(0, trend_strength)
            primary_contributions.append(concerning_strength)

        if not primary_contributions:
            return 0.0
        avg = sum(primary_contributions) / len(primary_contributions)
        return _clamp(avg / 3.0 * 100, 0, 100)

    def _compute_rate_score(self, features: dict) -> float:
        """Rate severity for primary params."""
        hr_sev = features.get("hr_rate_severity", 0.0) or 0.0
        spo2_sev = features.get("spo2_rate_severity", 0.0) or 0.0
        return _clamp((hr_sev + spo2_sev) / 2 * 100, 0, 100)

    def _compute_persistence_score(self, features: dict) -> float:
        """Persistence scores across primary params."""
        scores = [
            features.get("persistence_hr", 0.0) or 0.0,
            features.get("persistence_spo2", 0.0) or 0.0,
            features.get("persistence_rr", 0.0) or 0.0,
        ]
        return _clamp(sum(scores) / len(scores), 0, 100)

    def _compute_multiparam_score(self, features: dict) -> float:
        return _clamp(features.get("multiparam_score", 0.0) or 0.0, 0, 100)

    def compute_risk(
        self,
        features: dict,
        baseline,
        quality,
        window_readings: list,
        ml_model=None,
    ) -> RiskResult:
        """Compute hybrid risk score."""
        # Rule-based components
        dev_score = self._compute_deviation_score(features)
        trend_score = self._compute_trend_score(features)
        rate_score = self._compute_rate_score(features)
        persist_score = self._compute_persistence_score(features)
        multi_score = self._compute_multiparam_score(features)

        rule_score = _clamp(
            self.W_DEV * dev_score
            + self.W_TREND * trend_score
            + self.W_RATE * rate_score
            + self.W_PERSIST * persist_score
            + self.W_MULTI * multi_score,
            0, 100,
        )

        # ML inference
        ml_score = None
        model_status = "fallback"
        model_confidence = 0.50
        ml_probs = {}

        if ml_model is not None and getattr(ml_model, "is_ready", lambda: False)():
            try:
                import numpy as np
                from app.ml.features import FEATURE_NAMES
                feat_vec = [features.get(k) for k in FEATURE_NAMES]
                # Replace None with 0.0 for inference
                feat_vec = [v if v is not None else 0.0 for v in feat_vec]
                feat_arr = np.array(feat_vec).reshape(1, -1)
                result = ml_model.predict(feat_arr)
                if result and "probabilities" in result:
                    probs = result["probabilities"]
                    ml_score = 100 * probs.get("HIGH", 0.0) + 50 * probs.get("MODERATE", 0.0)
                    model_confidence = result.get("confidence", 0.50)
                    model_status = "ready"
                    ml_probs = probs
            except Exception as exc:
                import structlog
                structlog.get_logger(__name__).warning("ml_inference_failed", error=str(exc))
                ml_score = None
                model_status = "fallback"
                model_confidence = 0.50

        # Fusion
        if ml_score is not None and model_status == "ready":
            risk_score = _clamp(self.W_ML * ml_score + self.W_RULE * rule_score, 0, 100)
        else:
            risk_score = rule_score

        # Confidence
        data_confidence = quality.score if hasattr(quality, "score") else 0.5
        overall_confidence = 0.4 * model_confidence + 0.6 * data_confidence

        return RiskResult(
            risk_score=risk_score,
            rule_score=rule_score,
            ml_score=ml_score,
            model_status=model_status,
            model_confidence=model_confidence,
            data_confidence=data_confidence,
            overall_confidence=overall_confidence,
            deviation_score=dev_score,
            trend_score=trend_score,
            rate_score=rate_score,
            persistence_score=persist_score,
            multiparam_score=multi_score,
            ml_probabilities=ml_probs,
            component_weights={
                "deviation": self.W_DEV,
                "trend": self.W_TREND,
                "rate": self.W_RATE,
                "persistence": self.W_PERSIST,
                "multiparam": self.W_MULTI,
            },
        )

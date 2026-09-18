"""Deterministic explainability engine. No LLM. Template-based."""
from __future__ import annotations

from typing import Any, Optional

RECOMMENDATIONS = {
    "HIGH_PRIORITY": "Possible physiological deterioration pattern detected. Clinical review recommended per unit protocol. This is a prototype decision-support tool — not a diagnostic device.",
    "DETERIORATION_WARNING": "Possible early physiological change detected. Review vital trend data per clinical protocol. Prototype decision-support only.",
    "EARLY_CHANGE": "Early physiological variation noted. Continue monitoring per standard protocol. Prototype decision-support only.",
    "STABLE": "Vital signs within reference range. Continue routine monitoring. Prototype decision-support only.",
    "RECOVERY": "Physiological trends improving. Continue monitoring for sustained recovery. Prototype decision-support only.",
    "INSUFFICIENT_DATA": "Data insufficient for assessment. Check sensor connections and data completeness. Prototype decision-support only.",
}

PARAM_LABELS = {
    "heart_rate": "Heart Rate",
    "spo2": "SpO2",
    "respiratory_rate": "Respiratory Rate",
    "systolic_bp": "Systolic BP",
    "diastolic_bp": "Diastolic BP",
    "temperature": "Temperature",
}


class ExplainabilityEngine:
    def generate(
        self,
        patient_code: str,
        risk_result,
        features: dict,
        trends: dict,
        persists: dict,
        quality,
        baseline,
    ) -> dict:
        """Generate deterministic explanation for a risk assessment."""
        risk_score = risk_result.risk_score
        rule_score = risk_result.rule_score
        ml_score = risk_result.ml_score
        model_status = risk_result.model_status
        model_confidence = risk_result.model_confidence
        data_confidence = risk_result.data_confidence

        # Determine display state for headline
        if risk_score >= 75:
            state_label = "HIGH_PRIORITY"
        elif risk_score >= 50:
            state_label = "DETERIORATION_WARNING"
        elif risk_score >= 25:
            state_label = "EARLY_CHANGE"
        else:
            state_label = "STABLE"

        # Headline
        if state_label == "HIGH_PRIORITY":
            headline = f"Possible physiological deterioration pattern detected — high priority monitoring recommended"
        elif state_label == "DETERIORATION_WARNING":
            headline = f"Possible physiological change pattern detected — enhanced monitoring recommended"
        elif state_label == "EARLY_CHANGE":
            headline = f"Early physiological variation noted — continued monitoring recommended"
        else:
            headline = f"Vital signs within reference range — routine monitoring continued"

        # What happened
        abnormal_params = []
        for param, (z_key, val_key) in {
            "heart_rate": ("hr_z", "hr_current"),
            "spo2": ("spo2_z", "spo2_current"),
            "respiratory_rate": ("rr_z", "rr_current"),
            "systolic_bp": ("sbp_z", "sbp_current"),
            "diastolic_bp": ("dbp_z", "dbp_current"),
            "temperature": ("temp_z", "temp_current"),
        }.items():
            val = features.get(val_key)
            z = features.get(z_key)
            if val is not None and z is not None and abs(z) >= 1.5:
                abnormal_params.append(PARAM_LABELS.get(param, param))

        if abnormal_params:
            what_happened = f"Physiological variation detected in: {', '.join(abnormal_params)}."
        else:
            what_happened = "Vital signs within or near reference ranges."

        # Why detected
        why_parts = []
        if risk_result.deviation_score > 20:
            why_parts.append(f"deviation from baseline (score: {risk_result.deviation_score:.0f}/100)")
        if risk_result.trend_score > 20:
            why_parts.append(f"worsening trend pattern (score: {risk_result.trend_score:.0f}/100)")
        if risk_result.persistence_score > 20:
            why_parts.append(f"persistent concerning values (score: {risk_result.persistence_score:.0f}/100)")
        if risk_result.multiparam_score > 15:
            why_parts.append(f"multi-parameter concordance (score: {risk_result.multiparam_score:.0f}/100)")
        why_detected = "Triggered by: " + "; ".join(why_parts) + "." if why_parts else "No significant deviation detected."

        # Contributors
        total_rule = max(rule_score, 1)
        contributors = [
            {"component": "Deviation from baseline", "score": risk_result.deviation_score, "contribution_pct": round(risk_result.deviation_score * risk_result.component_weights.get("deviation", 0.30) / total_rule * 100, 1)},
            {"component": "Trend analysis", "score": risk_result.trend_score, "contribution_pct": round(risk_result.trend_score * risk_result.component_weights.get("trend", 0.20) / total_rule * 100, 1)},
            {"component": "Rate of change", "score": risk_result.rate_score, "contribution_pct": round(risk_result.rate_score * risk_result.component_weights.get("rate", 0.15) / total_rule * 100, 1)},
            {"component": "Persistence", "score": risk_result.persistence_score, "contribution_pct": round(risk_result.persistence_score * risk_result.component_weights.get("persistence", 0.20) / total_rule * 100, 1)},
            {"component": "Multi-parameter", "score": risk_result.multiparam_score, "contribution_pct": round(risk_result.multiparam_score * risk_result.component_weights.get("multiparam", 0.15) / total_rule * 100, 1)},
        ]

        # Baseline delta
        baseline_delta = {}
        for param, z_key, val_key, mean_attr in [
            ("heart_rate", "hr_z", "hr_current", "hr_mean"),
            ("spo2", "spo2_z", "spo2_current", "spo2_mean"),
            ("respiratory_rate", "rr_z", "rr_current", "rr_mean"),
        ]:
            val = features.get(val_key)
            z = features.get(z_key)
            mean = getattr(baseline, mean_attr, None)
            if val is not None and mean is not None:
                baseline_delta[param] = {
                    "current": round(val, 1),
                    "baseline_mean": round(mean, 1),
                    "deviation": round(val - mean, 2),
                    "z_score": round(z, 2) if z is not None else None,
                }

        # Persistence info
        persistence_info = {}
        for param in ["heart_rate", "spo2", "respiratory_rate"]:
            p = persists.get(param)
            if p is not None:
                persistence_info[param] = {
                    "consecutive": getattr(p, "consecutive_concerning", 0),
                    "score": round(getattr(p, "persistence_score", 0.0), 1),
                    "is_persistent": getattr(p, "is_persistent", False),
                }

        # Trend info
        trend_info = {}
        for param in ["heart_rate", "spo2", "respiratory_rate"]:
            t = trends.get(param)
            if t is not None:
                trend_info[param] = {
                    "direction": getattr(t, "direction", "UNKNOWN"),
                    "strength": round(getattr(t, "strength", 0.0), 2),
                }

        # ML contribution
        ml_info = {
            "model_status": model_status,
            "model_classification_confidence": round(model_confidence, 3),
            "rule_weight_pct": round(100 * risk_result.component_weights.get("rule", 0.55) if model_status == "ready" else 100, 1),
            "ml_weight_pct": round(100 * 0.45 if model_status == "ready" else 0, 1),
            "note": "Model classification confidence — not probability of illness",
        }
        if model_status == "fallback":
            ml_info["fallback_message"] = "AI model unavailable. Rule-based monitoring fallback is active."

        recommendation = RECOMMENDATIONS.get(state_label, RECOMMENDATIONS["STABLE"])

        return {
            "headline": headline,
            "what_happened": what_happened,
            "why_detected": why_detected,
            "contributors": contributors,
            "baseline_delta": baseline_delta,
            "persistence": persistence_info,
            "trend": trend_info,
            "data_quality": {
                "score": round(quality.score, 3) if hasattr(quality, "score") else None,
                "state": quality.state if hasattr(quality, "state") else "UNKNOWN",
                "data_confidence": round(data_confidence, 3),
            },
            "ml_contribution": ml_info,
            "recommendation": recommendation,
        }

    def generate_why_not(
        self,
        patient_code: str,
        risk_result,
        features: dict,
        baseline,
    ) -> dict:
        """Generate 'why not alert' explanation using negative evidence."""
        normal_params = []
        for param, val_key, z_key in [
            ("Heart Rate", "hr_current", "hr_z"),
            ("SpO2", "spo2_current", "spo2_z"),
            ("Respiratory Rate", "rr_current", "rr_z"),
        ]:
            val = features.get(val_key)
            z = features.get(z_key)
            if val is not None and (z is None or abs(z) < 1.5):
                normal_params.append(param)

        stabilizing = []
        if risk_result.deviation_score < 20:
            stabilizing.append("Vital signs within reference ranges")
        if risk_result.trend_score < 20:
            stabilizing.append("No significant worsening trends detected")
        if risk_result.persistence_score < 30:
            stabilizing.append("Concerning values not persistent")
        if risk_result.multiparam_score < 20:
            stabilizing.append("No multi-parameter concordance pattern")

        return {
            "patient_code": patient_code,
            "current_risk_score": round(risk_result.risk_score, 1),
            "why_score_is_low": f"Normal parameters: {', '.join(normal_params) or 'Assessment in progress'}",
            "stabilizing_factors": stabilizing,
            "monitoring_note": "Continued monitoring is recommended per standard protocol. This prototype system does not guarantee absence of physiological change.",
            "data_confidence": round(risk_result.data_confidence, 3),
            "model_status": risk_result.model_status,
        }

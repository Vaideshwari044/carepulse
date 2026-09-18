import pytest
from datetime import datetime, timedelta, UTC

from app.analytics.baseline import BaselineEngine, BaselineResult
from app.analytics.trend import TrendEngine
from app.analytics.rate import RateEngine
from app.analytics.persistence import PersistenceEngine
from app.analytics.multiparam import MultiParameterEngine
from app.analytics.quality import DataQualityEngine
from app.risk.engine import RiskEngine
from app.risk.state_machine import RiskStateMachine
from app.risk.explainability import ExplainabilityEngine


def test_baseline_engine_collecting():
    engine = BaselineEngine()
    readings = [{"heart_rate": 70, "recorded_at": datetime.now(UTC)}]
    res = engine.compute_baseline(readings)
    assert res.status == "collecting"
    assert res.frozen is False


def test_baseline_engine_ready():
    engine = BaselineEngine()
    now = datetime.now(UTC)
    readings = []
    for i in range(25):
        t = now - timedelta(seconds=700 - i * 25)
        readings.append({"heart_rate": 75 + (i % 3), "spo2": 98, "recorded_at": t})
    res = engine.compute_baseline(readings)
    assert res.status == "ready"
    assert res.hr_mean is not None
    assert 74.0 <= res.hr_mean <= 77.0


def test_trend_engine_increasing():
    engine = TrendEngine()
    now = datetime.now(UTC)
    values = [70, 75, 80, 85, 90, 95]
    timestamps = [now - timedelta(minutes=5 - i) for i in range(6)]
    res = engine.compute_trend(values, timestamps, "heart_rate")
    assert res.direction == "INCREASING"
    assert res.strength > 0.5


def test_rate_engine():
    engine = RateEngine()
    now = datetime.now(UTC)
    values = [70, 75, 80, 85]
    timestamps = [now - timedelta(minutes=3 - i) for i in range(4)]
    res = engine.compute_rate(values, timestamps, "heart_rate")
    assert res.rate > 0
    assert res.severity > 0


def test_persistence_engine():
    engine = PersistenceEngine()
    values = [60, 62, 110, 115, 120]  # last 3 concerning (>100)
    res = engine.compute_persistence(values, "heart_rate")
    assert res.consecutive_concerning == 3
    assert res.is_persistent is True


def test_quality_engine():
    engine = DataQualityEngine()
    now = datetime.now(UTC)
    window = [
        {"heart_rate": 72, "spo2": 98, "respiratory_rate": 14, "recorded_at": now}
    ]
    res = engine.compute_quality(window, now)
    assert res.state == "GOOD"
    assert res.score == 1.0


def test_risk_state_machine():
    machine = RiskStateMachine()
    res = machine.transition(
        current_score=80.0,
        previous_state="STABLE",
        primary_trend_directions={"heart_rate": "INCREASING"},
        quality_score=1.0,
        baseline_status="ready",
        consecutive_above=1,  # Second consecutive above threshold
    )
    assert res.new_state == "HIGH_PRIORITY"


def test_explainability_engine():
    engine = ExplainabilityEngine()
    class DummyRiskResult:
        risk_score = 80.0
        rule_score = 75.0
        ml_score = 85.0
        model_status = "ready"
        model_confidence = 0.90
        data_confidence = 0.95
        deviation_score = 30.0
        trend_score = 25.0
        rate_score = 20.0
        persistence_score = 20.0
        multiparam_score = 25.0
        component_weights = {"deviation": 0.3, "trend": 0.2, "rate": 0.15, "persistence": 0.2, "multiparam": 0.15}

    class DummyQuality:
        score = 0.95
        state = "GOOD"

    class DummyBaseline:
        hr_mean = 72.0
        spo2_mean = 98.0
        rr_mean = 14.0

    features = {"hr_current": 115.0, "hr_z": 3.2, "spo2_current": 92.0, "spo2_z": -2.5}
    exp = engine.generate("P101", DummyRiskResult(), features, {}, {}, DummyQuality(), DummyBaseline())
    assert "headline" in exp
    assert "recommendation" in exp
    assert "prototype" in exp["recommendation"].lower() or "prototype" in exp["headline"].lower()

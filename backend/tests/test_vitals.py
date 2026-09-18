import pytest
from app.routers.vitals import VitalReadingCreate


def test_vital_validation_invalid_hr():
    with pytest.raises(ValueError):
        VitalReadingCreate(
            patient_code="P101",
            recorded_at="2026-01-01T00:00:00Z",
            heart_rate=15.0,  # Below 20
        )


def test_vital_validation_invalid_spo2():
    with pytest.raises(ValueError):
        VitalReadingCreate(
            patient_code="P101",
            recorded_at="2026-01-01T00:00:00Z",
            spo2=45.0,  # Below 50
        )


def test_vital_validation_valid():
    v = VitalReadingCreate(
        patient_code="P101",
        recorded_at="2026-01-01T00:00:00Z",
        heart_rate=75.0,
        spo2=98.0,
        respiratory_rate=14.0,
        systolic_bp=120.0,
        diastolic_bp=80.0,
        temperature=37.0,
    )
    assert v.heart_rate == 75.0
    assert v.spo2 == 98.0

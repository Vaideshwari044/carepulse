"""Synthetic data generator for ML training. 60+ patients, 500+ readings each."""
from __future__ import annotations

import math
import os
import random
from datetime import UTC, datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

# Scenarios
SCENARIOS = ["stable", "temporary_variation", "gradual_deterioration", "multi_parameter", "missing_data", "recovery"]

SEED = 42
N_PATIENTS = 70
N_READINGS = 600


def _noise(rng, scale):
    return rng.gauss(0, scale)


def _clamp(v, lo, hi):
    if v is None:
        return None
    return max(lo, min(hi, v))


def generate_patient_readings(patient_id: int, scenario: str, rng: random.Random) -> pd.DataFrame:
    """Generate readings for a single synthetic patient."""
    # Randomized baseline
    hr_base = rng.uniform(60, 85)
    spo2_base = rng.uniform(96, 99)
    rr_base = rng.uniform(12, 18)
    sbp_base = rng.uniform(110, 135)
    dbp_base = rng.uniform(70, 90)
    temp_base = rng.uniform(36.5, 37.2)

    onset = rng.randint(80, 200)  # Step at which deterioration starts
    start_time = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=patient_id)

    rows = []
    for i in range(N_READINGS):
        t = start_time + timedelta(seconds=i * 5)
        prog = max(0, (i - onset) / 120.0)
        prog = min(prog, 1.0)

        if scenario == "stable":
            hr = hr_base + _noise(rng, 2.0)
            spo2 = spo2_base + _noise(rng, 0.3)
            rr = rr_base + _noise(rng, 0.8)
            sbp = sbp_base + _noise(rng, 3.0)
            dbp = dbp_base + _noise(rng, 2.0)
            temp = temp_base + _noise(rng, 0.05)
            label = "LOW"

        elif scenario == "temporary_variation":
            in_variation = 80 <= i <= 120
            t_var = (i - 80) / 40.0 if in_variation else 0
            bump = 15 * math.sin(math.pi * t_var) if in_variation else 0
            hr = hr_base + bump + _noise(rng, 2.0)
            spo2 = spo2_base - 2 * math.sin(math.pi * t_var) * (1 if in_variation else 0) + _noise(rng, 0.3)
            rr = rr_base + 4 * math.sin(math.pi * t_var) * (1 if in_variation else 0) + _noise(rng, 0.8)
            sbp = sbp_base + _noise(rng, 3.0)
            dbp = dbp_base + _noise(rng, 2.0)
            temp = temp_base + _noise(rng, 0.05)
            label = "MODERATE" if in_variation and t_var > 0.3 else "LOW"

        elif scenario == "gradual_deterioration":
            hr = hr_base + 35 * prog + _noise(rng, 3.0)
            spo2 = spo2_base - 6 * prog + _noise(rng, 0.5)
            rr = rr_base + 12 * prog + _noise(rng, 1.0)
            sbp = sbp_base + _noise(rng, 5.0)
            dbp = dbp_base + _noise(rng, 3.0)
            temp = temp_base + 0.9 * prog + _noise(rng, 0.1)
            if prog > 0.7:
                label = "HIGH"
            elif prog > 0.3:
                label = "MODERATE"
            else:
                label = "LOW"

        elif scenario == "multi_parameter":
            hr = hr_base + 40 * prog + _noise(rng, 3.0)
            spo2 = spo2_base - 7 * prog + _noise(rng, 0.5)
            rr = rr_base + 14 * prog + _noise(rng, 1.0)
            sbp = sbp_base - 25 * prog + _noise(rng, 5.0)
            dbp = dbp_base - 12 * prog + _noise(rng, 3.0)
            temp = temp_base + 1.2 * prog + _noise(rng, 0.1)
            if prog > 0.5:
                label = "HIGH"
            elif prog > 0.2:
                label = "MODERATE"
            else:
                label = "LOW"

        elif scenario == "missing_data":
            hr = hr_base + _noise(rng, 2.0) if rng.random() > 0.15 else None
            spo2 = spo2_base + _noise(rng, 0.3) if rng.random() > 0.25 else None
            rr = rr_base + _noise(rng, 0.8) if rng.random() > 0.2 else None
            sbp = sbp_base + _noise(rng, 3.0)
            dbp = dbp_base + _noise(rng, 2.0)
            temp = temp_base + _noise(rng, 0.05)
            label = "MODERATE" if (hr is None or spo2 is None or rr is None) else "LOW"

        elif scenario == "recovery":
            prog_r = 1.0 - min(i / 150.0, 1.0)
            hr = hr_base + 30 * prog_r + _noise(rng, 3.0)
            spo2 = spo2_base - 5 * prog_r + _noise(rng, 0.5)
            rr = rr_base + 10 * prog_r + _noise(rng, 1.0)
            sbp = sbp_base + _noise(rng, 5.0)
            dbp = dbp_base + _noise(rng, 3.0)
            temp = temp_base + 0.6 * prog_r + _noise(rng, 0.1)
            if prog_r > 0.6:
                label = "HIGH"
            elif prog_r > 0.3:
                label = "MODERATE"
            else:
                label = "LOW"
        else:
            hr, spo2, rr, sbp, dbp, temp = hr_base, spo2_base, rr_base, sbp_base, dbp_base, temp_base
            label = "LOW"

        # Clamp to valid ranges
        row = {
            "patient_id": f"SYN{patient_id:04d}",
            "scenario": scenario,
            "reading_idx": i,
            "recorded_at": t,
            "heart_rate": _clamp(hr, 25, 240),
            "spo2": _clamp(spo2, 55, 100),
            "respiratory_rate": _clamp(rr, 5, 55),
            "systolic_bp": _clamp(sbp, 55, 255),
            "diastolic_bp": _clamp(dbp, 35, 155),
            "temperature": _clamp(temp, 30.5, 42.5),
            "hr_baseline": hr_base,
            "spo2_baseline": spo2_base,
            "rr_baseline": rr_base,
            "sbp_baseline": sbp_base,
            "dbp_baseline": dbp_base,
            "temp_baseline": temp_base,
            # Label based on future 15-min simulator state (not rule_score)
            "label": label,
            "label_description": "prototype engineering label (simulator-generated, not clinician-annotated)",
        }
        rows.append(row)

    return pd.DataFrame(rows)


def generate_synthetic_dataset(output_path: str) -> pd.DataFrame:
    """Generate complete synthetic dataset."""
    rng = random.Random(SEED)
    np.random.seed(SEED)

    all_dfs = []
    for i in range(N_PATIENTS):
        scenario = SCENARIOS[i % len(SCENARIOS)]
        df = generate_patient_readings(i, scenario, rng)
        all_dfs.append(df)

    combined = pd.concat(all_dfs, ignore_index=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined.to_parquet(output_path, index=False)
    print(f"Generated {len(combined)} rows for {N_PATIENTS} patients at {output_path}")
    return combined


if __name__ == "__main__":
    generate_synthetic_dataset("data/training/synthetic_vitals.parquet")

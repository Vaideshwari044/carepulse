"""Synthetic patient vital sign simulator for CarePulse demo."""
from __future__ import annotations

import asyncio
import math
import random
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Six scenarios as required by SPEC
SCENARIOS = {
    "stable": "Stable physiological variation around baseline",
    "temporary_variation": "Brief excursion then return to baseline",
    "gradual_deterioration": "Slow worsening over 10-20 minutes",
    "multi_parameter": "Multiple parameters deteriorate together",
    "missing_data": "Intermittent missing vital signs",
    "recovery": "Patient recovering, trends improving",
}

# Patient baseline ranges (randomized per patient)
BASELINE_RANGES = {
    "heart_rate": (60, 85),
    "spo2": (96, 99),
    "respiratory_rate": (12, 18),
    "systolic_bp": (110, 135),
    "diastolic_bp": (70, 90),
    "temperature": (36.5, 37.2),
}


def _noise(rng: random.Random, scale: float) -> float:
    return rng.gauss(0, scale)


class PatientSimulator:
    """Per-patient simulation state and logic."""

    def __init__(self, patient_code: str, scenario: str, seed: int = 42):
        self.patient_code = patient_code
        self.scenario = scenario
        self.rng = random.Random(seed)
        self.running = False
        self.paused = False
        self.speed = 1.0
        self.simulated_time = datetime.now(UTC)
        self.elapsed_sim_seconds = 0.0
        self.step = 0
        self.task: Optional[asyncio.Task] = None

        # Randomized baseline per patient
        self.baseline = {
            "heart_rate": self.rng.uniform(*BASELINE_RANGES["heart_rate"]),
            "spo2": self.rng.uniform(*BASELINE_RANGES["spo2"]),
            "respiratory_rate": self.rng.uniform(*BASELINE_RANGES["respiratory_rate"]),
            "systolic_bp": self.rng.uniform(*BASELINE_RANGES["systolic_bp"]),
            "diastolic_bp": self.rng.uniform(*BASELINE_RANGES["diastolic_bp"]),
            "temperature": self.rng.uniform(*BASELINE_RANGES["temperature"]),
        }

        # Onset randomization
        self.onset_step = self.rng.randint(20, 60)  # Steps before deterioration starts

        # API token for posting vitals
        self._auth_token: Optional[str] = None

    def set_auth_token(self, token: str):
        self._auth_token = token

    def _generate_reading(self) -> dict:
        """Generate a vital reading based on scenario and elapsed time."""
        s = self.step
        baseline = self.baseline
        rng = self.rng

        if self.scenario == "stable":
            return {
                "heart_rate": baseline["heart_rate"] + _noise(rng, 2.0),
                "spo2": min(100, baseline["spo2"] + _noise(rng, 0.3)),
                "respiratory_rate": baseline["respiratory_rate"] + _noise(rng, 0.8),
                "systolic_bp": baseline["systolic_bp"] + _noise(rng, 3.0),
                "diastolic_bp": baseline["diastolic_bp"] + _noise(rng, 2.0),
                "temperature": baseline["temperature"] + _noise(rng, 0.05),
            }

        elif self.scenario == "temporary_variation":
            # Normal for 30 steps, variation for 20, then returns
            if s < 30 or s > 50:
                return {
                    "heart_rate": baseline["heart_rate"] + _noise(rng, 2.0),
                    "spo2": min(100, baseline["spo2"] + _noise(rng, 0.3)),
                    "respiratory_rate": baseline["respiratory_rate"] + _noise(rng, 0.8),
                    "systolic_bp": baseline["systolic_bp"] + _noise(rng, 3.0),
                    "diastolic_bp": baseline["diastolic_bp"] + _noise(rng, 2.0),
                    "temperature": baseline["temperature"] + _noise(rng, 0.05),
                }
            else:
                t = (s - 30) / 20
                hr_bump = 20 * math.sin(math.pi * t)
                return {
                    "heart_rate": baseline["heart_rate"] + hr_bump + _noise(rng, 2.0),
                    "spo2": min(100, baseline["spo2"] - 2 * math.sin(math.pi * t) + _noise(rng, 0.3)),
                    "respiratory_rate": baseline["respiratory_rate"] + 4 * math.sin(math.pi * t) + _noise(rng, 0.8),
                    "systolic_bp": baseline["systolic_bp"] + 15 * math.sin(math.pi * t) + _noise(rng, 3.0),
                    "diastolic_bp": baseline["diastolic_bp"] + _noise(rng, 2.0),
                    "temperature": baseline["temperature"] + _noise(rng, 0.05),
                }

        elif self.scenario == "gradual_deterioration":
            # Gradual worsening after onset
            prog = max(0, (s - self.onset_step) / 60.0)  # 0 to 1 over ~60 steps
            prog = min(prog, 1.0)
            return {
                "heart_rate": baseline["heart_rate"] + 30 * prog + _noise(rng, 3.0),
                "spo2": min(100, baseline["spo2"] - 5 * prog + _noise(rng, 0.5)),
                "respiratory_rate": baseline["respiratory_rate"] + 10 * prog + _noise(rng, 1.0),
                "systolic_bp": baseline["systolic_bp"] + _noise(rng, 5.0),
                "diastolic_bp": baseline["diastolic_bp"] + _noise(rng, 3.0),
                "temperature": baseline["temperature"] + 0.8 * prog + _noise(rng, 0.1),
            }

        elif self.scenario == "multi_parameter":
            # Multiple params deteriorate together after onset
            prog = max(0, (s - self.onset_step) / 40.0)
            prog = min(prog, 1.0)
            return {
                "heart_rate": baseline["heart_rate"] + 35 * prog + _noise(rng, 3.0),
                "spo2": min(100, baseline["spo2"] - 6 * prog + _noise(rng, 0.5)),
                "respiratory_rate": baseline["respiratory_rate"] + 12 * prog + _noise(rng, 1.0),
                "systolic_bp": baseline["systolic_bp"] - 20 * prog + _noise(rng, 5.0),
                "diastolic_bp": baseline["diastolic_bp"] - 10 * prog + _noise(rng, 3.0),
                "temperature": baseline["temperature"] + 1.0 * prog + _noise(rng, 0.1),
            }

        elif self.scenario == "missing_data":
            # Normal vitals but sometimes None
            reading = {
                "heart_rate": baseline["heart_rate"] + _noise(rng, 2.0),
                "spo2": min(100, baseline["spo2"] + _noise(rng, 0.3)),
                "respiratory_rate": baseline["respiratory_rate"] + _noise(rng, 0.8),
                "systolic_bp": baseline["systolic_bp"] + _noise(rng, 3.0),
                "diastolic_bp": baseline["diastolic_bp"] + _noise(rng, 2.0),
                "temperature": baseline["temperature"] + _noise(rng, 0.05),
            }
            # Randomly drop some vitals
            if rng.random() < 0.3:
                reading["spo2"] = None
            if rng.random() < 0.2:
                reading["respiratory_rate"] = None
            return reading

        elif self.scenario == "recovery":
            # Starts deteriorated, recovers over time
            prog = 1.0 - min((s / 80.0), 1.0)  # Starts at 1 (bad), goes to 0 (good)
            return {
                "heart_rate": baseline["heart_rate"] + 25 * prog + _noise(rng, 3.0),
                "spo2": min(100, baseline["spo2"] - 4 * prog + _noise(rng, 0.5)),
                "respiratory_rate": baseline["respiratory_rate"] + 8 * prog + _noise(rng, 1.0),
                "systolic_bp": baseline["systolic_bp"] + _noise(rng, 5.0),
                "diastolic_bp": baseline["diastolic_bp"] + _noise(rng, 3.0),
                "temperature": baseline["temperature"] + 0.5 * prog + _noise(rng, 0.1),
            }

        # Default stable
        return {
            "heart_rate": baseline["heart_rate"] + _noise(rng, 2.0),
            "spo2": min(100, baseline["spo2"] + _noise(rng, 0.3)),
            "respiratory_rate": baseline["respiratory_rate"] + _noise(rng, 0.8),
            "systolic_bp": baseline["systolic_bp"] + _noise(rng, 3.0),
            "diastolic_bp": baseline["diastolic_bp"] + _noise(rng, 2.0),
            "temperature": baseline["temperature"] + _noise(rng, 0.05),
        }

    def _clamp_vitals(self, vitals: dict) -> dict:
        """Clamp vitals to hard-valid ranges."""
        def _clamp(v, lo, hi):
            if v is None:
                return None
            return max(lo, min(hi, v))

        return {
            "heart_rate": _clamp(vitals.get("heart_rate"), 25, 240),
            "spo2": _clamp(vitals.get("spo2"), 55, 100),
            "respiratory_rate": _clamp(vitals.get("respiratory_rate"), 5, 55),
            "systolic_bp": _clamp(vitals.get("systolic_bp"), 55, 255),
            "diastolic_bp": _clamp(vitals.get("diastolic_bp"), 35, 155),
            "temperature": _clamp(vitals.get("temperature"), 30.5, 42.5),
        }

    async def run_loop(self, api_base_url: str):
        """Main simulation loop. Posts readings through POST /api/v1/vitals."""
        from app.core.config import get_settings
        settings = get_settings()
        ingest_interval = settings.INGEST_INTERVAL_SECONDS

        async with httpx.AsyncClient(base_url=api_base_url, timeout=10.0) as client:
            while self.running:
                if self.paused:
                    await asyncio.sleep(0.1)
                    continue

                # Generate and post reading
                vitals = self._generate_reading()
                vitals = self._clamp_vitals(vitals)

                # At 10x: 5 simulated seconds every 0.5 wall-clock seconds
                sim_step = ingest_interval * self.speed

                body = {
                    "patient_code": self.patient_code,
                    "recorded_at": self.simulated_time.isoformat(),
                    "source": "simulator",
                    **{k: round(v, 2) if v is not None else None for k, v in vitals.items()},
                }

                try:
                    headers = {}
                    if self._auth_token:
                        headers["Authorization"] = f"Bearer {self._auth_token}"
                    response = await client.post("/api/v1/vitals", json=body, headers=headers)
                    if response.status_code not in (200, 201):
                        logger.debug("simulator.post_error", status=response.status_code, body=response.text[:200])
                except Exception as exc:
                    logger.warning("simulator.post_failed", error=str(exc))

                self.step += 1
                self.simulated_time += timedelta(seconds=ingest_interval)
                self.elapsed_sim_seconds += ingest_interval

                # Wall-clock sleep (adjusted for speed)
                wall_sleep = 0.5 if self.speed >= 10 else (ingest_interval / self.speed)
                await asyncio.sleep(max(0.1, wall_sleep))


class SimulatorEngine:
    """Manages multiple per-patient simulators."""

    def __init__(self):
        self._simulators: dict[str, PatientSimulator] = {}
        self._api_base_url = "http://localhost:8000"

    def set_api_base(self, url: str):
        self._api_base_url = url

    async def start(self, patient_code: str, scenario: str, speed: float = 1.0, auth_token: str = "") -> None:
        await self.stop(patient_code)
        sim = PatientSimulator(patient_code, scenario, seed=hash(patient_code) % 10000)
        sim.speed = speed
        sim.running = True
        if auth_token:
            sim.set_auth_token(auth_token)
        self._simulators[patient_code] = sim
        task = asyncio.create_task(sim.run_loop(self._api_base_url))
        sim.task = task
        logger.info("simulator.started", patient=patient_code, scenario=scenario, speed=speed)

    async def pause(self, patient_code: str) -> None:
        if patient_code in self._simulators:
            self._simulators[patient_code].paused = True

    async def resume(self, patient_code: str) -> None:
        if patient_code in self._simulators:
            self._simulators[patient_code].paused = False

    async def stop(self, patient_code: str) -> None:
        if patient_code in self._simulators:
            sim = self._simulators.pop(patient_code)
            sim.running = False
            if sim.task and not sim.task.done():
                sim.task.cancel()
                try:
                    await sim.task
                except (asyncio.CancelledError, Exception):
                    pass

    async def restart(self, patient_code: str, scenario: Optional[str] = None, speed: float = 1.0, auth_token: str = "") -> None:
        old_scenario = scenario
        if patient_code in self._simulators and old_scenario is None:
            old_scenario = self._simulators[patient_code].scenario
        await self.stop(patient_code)
        await self.start(patient_code, old_scenario or "stable", speed, auth_token)

    async def reset(self, patient_code: str) -> None:
        await self.stop(patient_code)

    def get_status(self, patient_code: Optional[str] = None) -> dict:
        if patient_code:
            sim = self._simulators.get(patient_code)
            if sim is None:
                return {"patient_code": patient_code, "running": False}
            return {
                "patient_code": patient_code,
                "scenario": sim.scenario,
                "running": sim.running,
                "paused": sim.paused,
                "speed": sim.speed,
                "step": sim.step,
                "elapsed_sim_seconds": sim.elapsed_sim_seconds,
                "simulated_time": sim.simulated_time.isoformat(),
            }
        return {
            pc: {"scenario": s.scenario, "running": s.running, "paused": s.paused, "speed": s.speed, "step": s.step}
            for pc, s in self._simulators.items()
        }


# Singleton
simulator_engine = SimulatorEngine()

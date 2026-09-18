"""Risk state machine for CarePulse."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional


@dataclass
class StateMachineResult:
    new_state: str
    transitioned: bool
    consecutive_above: int
    consecutive_below: int


class RiskStateMachine:
    def __init__(self, settings=None):
        from app.core.config import get_settings
        s = settings or get_settings()
        self.stable_max = s.RISK_STABLE_MAX
        self.early_max = s.RISK_EARLY_CHANGE_MAX
        self.warning_max = s.RISK_WARNING_MAX
        self.escalate_n = s.ESCALATE_CONSECUTIVE
        self.deescalate_n = s.DEESCALATE_CONSECUTIVE
        self.deescalate_margin = s.DEESCALATE_MARGIN
        self.min_dwell = s.MIN_STATE_DWELL_SECONDS

    def _score_to_natural_state(self, score: float) -> str:
        if score <= self.stable_max:
            return "STABLE"
        elif score <= self.early_max:
            return "EARLY_CHANGE"
        elif score <= self.warning_max:
            return "DETERIORATION_WARNING"
        else:
            return "HIGH_PRIORITY"

    def transition(
        self,
        current_score: float,
        previous_state: Optional[str],
        primary_trend_directions: dict,
        quality_score: float,
        baseline_status: str,
        last_state_change: Optional[datetime] = None,
        consecutive_above: int = 0,
        consecutive_below: int = 0,
    ) -> StateMachineResult:
        """Compute next risk state."""
        # INSUFFICIENT_DATA override: display state but still store risk_score
        if quality_score < 0.50 or baseline_status not in ("ready", "frozen"):
            return StateMachineResult(
                new_state="INSUFFICIENT_DATA",
                transitioned=(previous_state != "INSUFFICIENT_DATA"),
                consecutive_above=0,
                consecutive_below=0,
            )

        natural = self._score_to_natural_state(current_score)
        prev_state = previous_state or "STABLE"

        STATE_ORDER = ["STABLE", "EARLY_CHANGE", "DETERIORATION_WARNING", "HIGH_PRIORITY", "RECOVERY", "INSUFFICIENT_DATA"]
        NUMERIC = {"STABLE": 0, "EARLY_CHANGE": 1, "DETERIORATION_WARNING": 2, "HIGH_PRIORITY": 3, "RECOVERY": 1, "INSUFFICIENT_DATA": -1}

        prev_num = NUMERIC.get(prev_state, 0)
        natural_num = NUMERIC.get(natural, 0)

        # Check Recovery condition
        is_descending = natural_num < prev_num
        improving_trends = sum(
            1 for param, direction in primary_trend_directions.items()
            if (param == "spo2" and direction == "INCREASING") or
               (param != "spo2" and direction == "DECREASING")
        )
        can_recover = (
            prev_state in ("DETERIORATION_WARNING", "HIGH_PRIORITY")
            and is_descending
            and improving_trends >= 2
        )

        # Min dwell check
        now = datetime.now(UTC)
        if last_state_change is not None:
            age = (now - last_state_change).total_seconds()
            if age < self.min_dwell:
                # Don't change state if too soon
                return StateMachineResult(
                    new_state=prev_state,
                    transitioned=False,
                    consecutive_above=consecutive_above,
                    consecutive_below=consecutive_below,
                )

        # Escalation logic
        boundary_score = {
            "STABLE": self.stable_max,
            "EARLY_CHANGE": self.early_max,
            "DETERIORATION_WARNING": self.warning_max,
            "HIGH_PRIORITY": 100,
        }.get(prev_state, self.stable_max)

        if natural_num > prev_num:
            # Escalating
            new_above = consecutive_above + 1
            new_below = 0
            if new_above >= self.escalate_n:
                new_state = natural
                transitioned = (new_state != prev_state)
            else:
                new_state = prev_state
                transitioned = False
        elif natural_num < prev_num:
            # De-escalating
            new_below = consecutive_below + 1
            new_above = 0
            deescalate_threshold = boundary_score - self.deescalate_margin
            if current_score <= deescalate_threshold and new_below >= self.deescalate_n:
                if can_recover:
                    new_state = "RECOVERY"
                else:
                    new_state = natural
                transitioned = (new_state != prev_state)
            else:
                new_state = prev_state
                transitioned = False
        else:
            # Same level
            new_above = 0
            new_below = 0
            new_state = prev_state if prev_state != "INSUFFICIENT_DATA" else natural
            transitioned = False

        return StateMachineResult(
            new_state=new_state,
            transitioned=transitioned,
            consecutive_above=new_above if natural_num > prev_num else 0,
            consecutive_below=new_below if natural_num < prev_num else 0,
        )

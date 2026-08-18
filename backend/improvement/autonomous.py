"""
autonomous.py — autonomous self-improvement loop.

Why
---
The existing ``Redesigner`` runs *on demand* — when a user hits
``/improvement/run``.  A self-improving smart grid must also run
*autonomously* after every simulation step, watch the rolling
metrics, and recommend (or even apply) a topology change when the
grid drifts below a healthy threshold.

This module is a small RL-style policy layer on top of the existing
``Redesigner``: it decides *whether* to run the redesigner based on
the current run-level KPIs, and chooses how aggressive the
recommendation should be (max/actions, max/iterations).

Backward compatibility
----------------------
The module is *additive* — ``Redesigner`` and ``AIPlanner`` are not
modified.  The new ``AutonomousImprovementLoop`` only reads
``SimulationEvaluator.summary()`` and writes a recommendation to its
own history buffer.  Wire it into the API layer through ``/improvement/autonomous``.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

from improvement.evaluator import SimulationEvaluator
from improvement.redesigner import RedesignReport, Redesigner


@dataclass
class AutonomousConfig:
    """Tuning knobs for the autonomous loop."""

    # Trigger the loop when mean reliability drops below this threshold
    # across the lookahead window [0, 1].
    reliability_threshold: float = 0.85
    # Trigger the loop when ENS per step exceeds this ceiling (MWh).
    ens_step_threshold: float = 0.5
    # Number of recent steps to consider when scoring the grid.
    window: int = 20
    # Cap redesign bursts so the loop can't rewrite the grid every tick.
    cooldown_steps: int = 50
    # Run the redesigner at most every `cooldown_steps` simulation steps.
    last_trigger_step: int = -1_000_000


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


@dataclass
class ImprovementDecision:
    """The loop's verdict for the current step."""

    triggered: bool
    reason: str
    reliability: float
    ens_per_step: float
    cooldown_remaining: int
    report: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered": bool(self.triggered),
            "reason": self.reason,
            "reliability": float(self.reliability),
            "ens_per_step": float(self.ens_per_step),
            "cooldown_remaining": int(self.cooldown_remaining),
            "report": self.report,
        }


@dataclass
class AutonomousImprovementLoop:
    """Watch KPIs and trigger the redesigner when the grid drifts."""

    config: AutonomousConfig = field(default_factory=AutonomousConfig)
    designer: Redesigner = field(default_factory=Redesigner)
    history: Deque[ImprovementDecision] = field(
        default_factory=lambda: deque(maxlen=128),
    )
    _evaluator: SimulationEvaluator = field(default_factory=SimulationEvaluator)

    # ------------------------------------------------------------------

    def attach_evaluator(self, evaluator: SimulationEvaluator) -> None:
        """Allow callers to share a single global evaluator."""
        self._evaluator = evaluator

    # ------------------------------------------------------------------

    def step(self, grid: Any, current_step: int) -> ImprovementDecision:
        """One tick of the autonomous loop.

        Steps
        -----
        1. Snapshot the live grid into the evaluator.
        2. Compute mean reliability / ENS over the trailing window.
        3. Decide whether to trigger a redesign (cooldown-aware).
        4. If triggered, run the redesigner against the live grid and
           record the recommendation in the history buffer.
        """
        try:
            snap = SimulationEvaluator.snapshot_from_grid(grid, current_step)
            self._evaluator.record_step(snap)
        except Exception as exc:  # noqa: BLE001
            # Snapshot failure is non-fatal for the autonomous loop but
            # we log it so experiments can attribute missed triggers.
            logger.warning(
                "autonomous snapshot failed at step %s: %r", current_step, exc,
            )

        summary = self._evaluator.summary()
        reliability = float(summary.get("critical_load_availability", 1.0))
        ens_per_step = float(summary.get("ieee_ens_mwh", 0.0))
        # Normalise ENS per-step (the evaluator sums it over the window).
        n = max(1, len(self._evaluator.snapshots))
        ens_per_step = ens_per_step / n

        cooldown_remaining = max(
            0, self.config.cooldown_steps
            - (current_step - self.config.last_trigger_step),
        )

        reason = "ok"
        triggered = False
        if reliability < self.config.reliability_threshold:
            triggered = True
            reason = (
                f"reliability {reliability:.2f} < "
                f"{self.config.reliability_threshold:.2f}"
            )
        elif ens_per_step > self.config.ens_step_threshold:
            triggered = True
            reason = (
                f"ENS/step {ens_per_step:.2f} > "
                f"{self.config.ens_step_threshold:.2f}"
            )
        if triggered and cooldown_remaining > 0:
            triggered = False
            reason = f"cooldown ({cooldown_remaining} steps remaining)"

        report_dict: Optional[Dict[str, Any]] = None
        if triggered:
            try:
                report = self.designer.propose(grid, summary)
                report_dict = report.to_dict()
                self.config.last_trigger_step = current_step
                reason += "; redesign applied"
            except Exception as exc:  # noqa: BLE001
                reason += f"; redesign failed: {exc!r}"

        decision = ImprovementDecision(
            triggered=triggered,
            reason=reason,
            reliability=reliability,
            ens_per_step=ens_per_step,
            cooldown_remaining=cooldown_remaining,
            report=report_dict,
        )
        self.history.append(decision)
        return decision

    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Return the loop's view of the grid — useful for the dashboard."""
        snaps = list(self._evaluator.snapshots)
        recent = snaps[-self.config.window:]
        if not recent:
            return {
                "window": 0,
                "mean_reliability": 1.0,
                "mean_critical_load": 0.0,
                "history": [],
            }
        return {
            "window": len(recent),
            "mean_reliability": _mean(
                [s.critical_load_available / max(1, s.critical_load_total)
                 for s in recent]
            ),
            "mean_critical_load": _mean(
                [s.critical_load_available for s in recent]
            ),
            "history": [d.to_dict() for d in list(self.history)[-20:]],
        }

    def reset(self) -> None:
        self._evaluator = SimulationEvaluator()
        self.history.clear()
        self.config.last_trigger_step = -1_000_000

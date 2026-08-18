"""
twin.py — per-asset digital twin.

Why
---
A digital twin is a per-asset digital counterpart that mirrors the
physical state of a real grid device (transformer, line, generator,
battery).  Unlike the live ``GridNode`` — which only holds the
current timestep — a twin accumulates *history*, *health*, and a
*predicted future state*, enabling predictive self-healing.

Each twin stores:

  - ``health``               : remaining life in [0, 1]
  - ``age_hours``            : cumulative operating time
  - ``temperature``          : hot-spot estimate (K)
  - ``loading``              : per-unit loading at last sample
  - ``health_risk_score``    : heuristic in [0, 1] — *not* a
                               calibrated failure probability; see
                               ``_HEALTH_RISK_FORMULA``.
  - ``sensor_history``       : deque of recent physical readings
  - ``maintenance_history``  : deque of maintenance events
  - ``predicted_state``      : dict, sliding-horizon forecast

Naming
------
main.md Stage 10 forbids calling a heuristic "failure probability".
This module therefore exposes the canonical name ``health_risk_score``
and keeps ``failure_probability`` as a deprecated alias for backward
compatibility. New code must use ``health_risk_score``.

The ``tick`` method advances the twin by one simulation step using
the Arrhenius ageing model in ``degradation.py``.
"""
from __future__ import annotations

import math
import warnings
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Optional


# Heuristic risk-score formula.  Risk rises linearly from 0 (at
# health >= 0.4) to 1 (at health <= 0) and is clamped to [0, 1].
# This is a *heuristic* projection, not a calibrated probability —
# see main.md Stage 10 (LIMITATIONS / SIMULATION-VALIDATED).
_HEALTH_RISK_FORMULA = (
    "max(0, min(1, (0.4 - h) / 0.4)) for h < 0.4; else 0.0"
)


def _health_risk_from_health(h: float) -> float:
    """Apply the heuristic risk formula in ``_HEALTH_RISK_FORMULA``."""
    if h >= 0.4:
        return 0.0
    return max(0.0, min(1.0, (0.4 - h) / 0.4))


@dataclass
class DigitalTwin:
    """Per-asset digital twin — mirrors a ``GridNode`` across time."""

    asset_id: str
    asset_type: str = "generic"
    health: float = 1.0
    age_hours: float = 0.0
    temperature: float = 293.0
    loading: float = 0.0
    sensor_history: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=64))
    maintenance_history: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=32))
    predicted_state: Dict[str, Any] = field(default_factory=dict)
    # Stored separately so callers that bypass ``tick`` can still
    # inspect / override the most-recent predicted score.
    _health_risk_score: float = field(default=0.0, init=True, repr=False)

    # ------------------------------------------------------------------
    # Derived property — keeps health_risk_score in lock-step with
    # ``health`` even when callers mutate ``health`` directly (tests,
    # restoration hooks, manual overrides).
    # ------------------------------------------------------------------
    @property
    def health_risk_score(self) -> float:
        """Heuristic risk score in [0, 1].

        NOT a calibrated failure probability. See ``_HEALTH_RISK_FORMULA``
        and main.md Stage 10 (LIMITATIONS).

        Always derived from ``self.health``; the setter is provided
        only for backward compatibility with older code that wrote
        ``twin.failure_probability = ...`` and is a no-op.
        """
        return _health_risk_from_health(self.health)

    @health_risk_score.setter
    def health_risk_score(self, value: float) -> None:
        # No-op: the score is always derived from health. Provided
        # so legacy code that wrote ``twin.failure_probability = x``
        # does not raise AttributeError.
        try:
            _ = max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            pass

    # ------------------------------------------------------------------
    # Deprecated alias — kept for backward compatibility with the
    # dozens of call sites that still read ``twin.failure_probability``.
    # New code must use ``twin.health_risk_score``.
    # ------------------------------------------------------------------
    @property
    def failure_probability(self) -> float:  # noqa: D401
        """DEPRECATED alias for ``health_risk_score``.

        Kept so existing callers (predictor, registry, tests) keep
        working without modification. New code must use
        ``health_risk_score`` — see main.md Stage 10.
        """
        warnings.warn(
            "DigitalTwin.failure_probability is deprecated; "
            "use DigitalTwin.health_risk_score instead. "
            "The value is a heuristic, NOT a calibrated probability.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.health_risk_score

    @failure_probability.setter
    def failure_probability(self, value: float) -> None:
        warnings.warn(
            "DigitalTwin.failure_probability is deprecated; "
            "use DigitalTwin.health_risk_score instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.health_risk_score = value

    # ------------------------------------------------------------------
    # Per-step update
    # ------------------------------------------------------------------

    def tick(
        self,
        *,
        physical_state: Dict[str, Any],
        dt_hours: float = 1.0,
        ambient_k: float = 293.0,
    ) -> Dict[str, Any]:
        """Advance the twin by one step using the current physical state.

        ``physical_state`` may include: ``voltage``, ``frequency``,
        ``load``, ``generation``, ``failed``.  Unknown keys are stored
        in ``sensor_history`` unchanged.

        Returns a small dict summarising what changed — useful for
        tests and the XAI panel.
        """
        # Late import to avoid a circular dep with the simulation package.
        from digital_twin.degradation import thermal_ageing_step

        load = float(physical_state.get("load", 0.0))
        gen = float(physical_state.get("generation", 0.0))
        # Loading is demand relative to nominal — clamp to [0, 2].
        loading = max(0.0, min(2.0, load + 0.3 * gen))
        self.loading = loading
        self.age_hours += dt_hours

        ageing = thermal_ageing_step(
            current_health=self.health,
            loading=loading,
            ambient_k=ambient_k,
            dt_hours=dt_hours,
        )
        self.health = ageing["new_health"]
        self.temperature = ageing["temperature_k"]
        # Heuristic risk score rises sharply as health falls below 0.4.
        # See ``_HEALTH_RISK_FORMULA`` and main.md Stage 10.
        self.health_risk_score = _health_risk_from_health(self.health)

        # Record the sample.
        self.sensor_history.append({
            "age_hours": self.age_hours,
            "load": load,
            "generation": gen,
            "voltage": physical_state.get("voltage"),
            "health": self.health,
            "temperature": self.temperature,
            "loading": loading,
        })

        return {
            "asset_id": self.asset_id,
            "health": self.health,
            "loading": loading,
            "temperature": self.temperature,
            "age_hours": self.age_hours,
            "health_risk_score": self.health_risk_score,
            "delta_health": ageing["delta_health"],
        }

    # ------------------------------------------------------------------
    # Predictive interface
    # ------------------------------------------------------------------

    def predict_failure(self, horizon_steps: int = 24) -> Dict[str, Any]:
        """Project the heuristic risk score forward ``horizon_steps`` steps.

        This is a simple linear-extrapolation model: if the current
        health is H and the average degradation rate over the last 8
        samples is R, then projected health after ``horizon_steps``
        is H + R*horizon_steps. We compute the projected
        ``health_risk_score`` as ``clip((0.4 - H_proj)/0.4)`` when
        H_proj < 0.4, else 0.

        IMPORTANT — this is a *heuristic*, NOT a calibrated probability
        (main.md Stage 10, SIMULATION-VALIDATED).

        Returns a dict with ``horizon_steps``, ``projected_health``,
        ``projected_health_risk_score``, and ``will_fail``.
        """
        if not self.sensor_history:
            return {
                "horizon_steps": horizon_steps,
                "projected_health": self.health,
                "projected_health_risk_score": 0.0,
                "will_fail": False,
            }
        recent = list(self.sensor_history)[-8:]
        if len(recent) >= 2:
            deltas = [
                recent[i]["health"] - recent[i - 1]["health"]
                for i in range(1, len(recent))
                if "health" in recent[i] and "health" in recent[i - 1]
            ]
            avg_rate = sum(deltas) / len(deltas) if deltas else 0.0
        else:
            avg_rate = 0.0
        projected = max(0.0, self.health + avg_rate * horizon_steps)
        proj_risk = _health_risk_from_health(projected)
        self.predicted_state = {
            "horizon_steps": horizon_steps,
            "projected_health": projected,
            "projected_health_risk_score": proj_risk,
            "avg_degradation_rate": avg_rate,
        }
        return self.predicted_state

    # ------------------------------------------------------------------
    # Maintenance tracking
    # ------------------------------------------------------------------

    def record_maintenance(self, event: Dict[str, Any]) -> None:
        """Log a maintenance event and reset health to a specified value if given."""
        self.maintenance_history.append(event)
        if "restore_health_to" in event:
            try:
                self.health = float(event["restore_health_to"])
            except (TypeError, ValueError):
                pass

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "health": self.health,
            "age_hours": self.age_hours,
            "temperature": self.temperature,
            "loading": self.loading,
            "health_risk_score": self.health_risk_score,
            "sensor_history_size": len(self.sensor_history),
            "maintenance_history_size": len(self.maintenance_history),
            "predicted_state": dict(self.predicted_state),
        }
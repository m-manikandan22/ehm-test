"""Persistence baseline — no-action control.

Holds the grid in its last state without issuing any control signal,
useful as the lowest bar against which DQN/RULE/FLISR policies are
compared in the ablation and monte-carlo experiments.
"""
from __future__ import annotations

from typing import Any, Optional


class PersistencePolicy:
    """Always returns ``None`` — apply no control action."""

    def choose_action(self, state: Any, grid_state: Optional[dict] = None) -> None:
        return None

    def predict(self, sequence) -> float:
        """Hold-last-value forecaster — used as the LSTM baseline."""
        return float(getattr(self, "_last", 0.0) or 0.0)

    def reset(self) -> None:
        self._last = 0.0

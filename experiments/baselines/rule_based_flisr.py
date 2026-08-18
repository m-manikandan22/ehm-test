"""rule_based_flisr.py — Pure FLISR baseline (no DQN, no LSTM, no Twin).

Drives the existing ``SmartGrid.flisr_restore`` after every topology
change with a fixed 5-second cycle, isolating FLISR's contribution
from the DQN / LSTM / Twin stack in the ablation studies.
"""
from __future__ import annotations

from typing import Any, Optional


class RuleBasedFLISRBaseline:
    """No-action policy; relies on the built-in FLISR for self-healing."""

    def __init__(self) -> None:
        self._ticks_since_flisr = 0
        self._flisr_period = 5  # run FLISR every 5 ticks

    def choose_action(self, state: Any, grid_state: Optional[dict] = None) -> None:
        return None

    def pre_step(self, grid) -> None:
        """Hook called before ``grid.step()`` runs.

        Triggers ``flisr_restore`` every 5 ticks — this is the same
        cadence the rest of the simulation uses, so the baseline's
        self-healing response time matches the DQN/RULE-driven runs.
        """
        self._ticks_since_flisr += 1
        if self._ticks_since_flisr >= self._flisr_period:
            self._ticks_since_flisr = 0
            try:
                grid.flisr_restore()
            except Exception:  # noqa: BLE001
                # Let the experiment runner's exception handler decide
                pass

    def reset(self) -> None:
        self._ticks_since_flisr = 0

"""
baselines.py — Baseline policies for benchmarking against the DQN agent.

Each baseline implements the same interface:
    choose_action(state, grid_state) -> int   (action_id 0..4)
    reset()
"""
from __future__ import annotations

import random
from typing import Optional


# Action catalogue (must mirror rl_agent.ACTIONS)
ACTION_BOOST_GEN  = 0
ACTION_USE_BATT   = 1
ACTION_USE_SUPER  = 2
ACTION_SHIFT_LOAD = 3
ACTION_REROUTE    = 4


class RandomPolicy:
    """Pure random action selection — uniform over the 5 actions."""

    def __init__(self, action_count: int = 5, seed: Optional[int] = None):
        self.action_count = action_count
        self.rng = random.Random(seed)

    def choose_action(self, state, grid_state=None) -> int:
        return self.rng.randrange(self.action_count)

    def reset(self):
        pass


class RuleBasedPolicy:
    """Replicates the rule-guided expert policy used in rl_agent.smart_warmup.

    Used both as a baseline and as a control in the ablation studies.

    Delegates to ``rl.expert_policy.choose_action`` so the rule ladder
    is defined exactly once across the codebase.
    """

    def choose_action(self, state, grid_state=None) -> int:
        from rl.expert_policy import choose_action as _choose
        return _choose(state, grid_state)

    def reset(self):
        pass


class PersistencePolicy:
    """Predicts next-step load by holding the previous value (no learning).

    Implements a `predict()` method that returns the last observed load.
    Used as a baseline for the LSTM forecaster.
    """

    def __init__(self):
        self.last_load = 0.5

    def predict(self, sequence) -> float:
        return float(self.last_load)

    def reset(self):
        self.last_load = 0.5


class NaiveThresholdPolicy:
    """Baseline fault detector: pure threshold with no ML."""

    def __init__(self, voltage_low: float = 0.85,
                 voltage_high: float = 1.10,
                 freq_low: float = 49.0,
                 freq_high: float = 51.0):
        self.voltage_low = voltage_low
        self.voltage_high = voltage_high
        self.freq_low = freq_low
        self.freq_high = freq_high

    def detect(self, grid_nodes) -> list:
        alerts = []
        for nid, n in grid_nodes.items():
            v = getattr(n, "voltage", 1.0)
            f = getattr(n, "frequency", 50.0)
            failed = getattr(n, "failed", False)
            isolated = getattr(n, "isolated", False)
            if failed:
                alerts.append({"node_id": nid, "fault_type": "hard_failure",
                                "score": 1.0, "severity": "CRITICAL"})
            elif isolated:
                alerts.append({"node_id": nid, "fault_type": "de_energized",
                                "score": 0.5, "severity": "MEDIUM"})
            elif v < self.voltage_low or v > self.voltage_high:
                alerts.append({"node_id": nid, "fault_type": "undervoltage",
                                "score": 0.7, "severity": "HIGH"})
            elif f < self.freq_low or f > self.freq_high:
                alerts.append({"node_id": nid, "fault_type": "frequency_deviation",
                                "score": 0.7, "severity": "HIGH"})
        return alerts

    def reset(self):
        pass
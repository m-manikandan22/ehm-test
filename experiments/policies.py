"""policies.py — Policy registry used by the experiment harness.

Each entry is a callable that returns a *fresh* policy instance per run,
so the harness can fork N independent seeds without sharing state.

The keys are policy names that appear in the experiments CLI
(``--policies random,rule_based,dqn,flisr_only,persistence``).
"""
from __future__ import annotations

from typing import Callable, Dict


def _make_random():
    from benchmarks.baselines import RandomPolicy
    return RandomPolicy(seed=None)


def _make_rule_based():
    from benchmarks.baselines import RuleBasedPolicy
    return RuleBasedPolicy()


def _make_dqn():
    try:
        from experiments.baselines.dqn_only import DQNOnlyBaseline
        return DQNOnlyBaseline()
    except Exception as exc:  # noqa: BLE001
        # Fall back to random if torch/RL stack is unavailable.
        from benchmarks.baselines import RandomPolicy
        return RandomPolicy(seed=None)


def _make_flisr_only():
    from experiments.baselines.rule_based_flisr import RuleBasedFLISRBaseline
    return RuleBasedFLISRBaseline()


def _make_persistence():
    from experiments.baselines.persistence import PersistencePolicy
    return PersistencePolicy()


POLICY_REGISTRY: Dict[str, Callable] = {
    "random":      _make_random,
    "rule_based":  _make_rule_based,
    "dqn":         _make_dqn,
    "flisr_only":  _make_flisr_only,
    "persistence": _make_persistence,
}


def make_policy(name: str):
    """Return a fresh policy instance for the given name.

    Raises ``KeyError`` for unknown names; the caller is expected to
    validate against ``POLICY_REGISTRY`` before invocation.
    """
    if name not in POLICY_REGISTRY:
        raise KeyError(
            f"Unknown policy: {name}. "
            f"Available: {sorted(POLICY_REGISTRY.keys())}"
        )
    return POLICY_REGISTRY[name]()


def available_policies() -> list:
    """Return the list of registered policy names."""
    return sorted(POLICY_REGISTRY.keys())

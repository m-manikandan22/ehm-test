"""
expert_policy.py — Rule-based action selector used as a DQN warm-up signal.

Why this exists
---------------
The DQN's ``smart_warmup`` populates the replay buffer with transitions
whose actions are chosen by a hand-coded rule ladder. This module
*centralises* that ladder so the same rule is used by:

1. ``backend/models/rl_agent.py`` — DQN ``smart_warmup``.
2. ``backend/benchmarks/baselines.py`` — ``RuleBasedPolicy`` baseline.
3. ``backend/experiments/baselines/`` — experiment framework baselines.

It is **not** imitation learning in the technical sense. There is no
``state -> expert_action`` regression loss, no behavioural-cloning head,
no DAgger, no queryable expert at training time. The network is trained
on standard Bellman regression over transitions whose *actions* happened
to be chosen by this rule ladder. This is **dataset bootstrapping from
rule outputs**, and is documented as such in
``docs/ROADMAP_AFTER_CRITICAL_10.md`` and the README.

Threshold rationale (calibration):
- ``balance < -0.3`` → boost generation (large deficit)
- ``balance < -0.1`` → discharge battery (smaller deficit)
- any failed / isolated node → reroute (highest priority)
- any node with ``load > 1.2`` → supercapacitor (transient spike)
- otherwise → shift load (default: defer non-critical demand)
"""
from __future__ import annotations

from typing import Optional


# Action IDs match ``models/rl_agent.ACTIONS`` and ``benchmarks/baselines.ACTION_*``.
ACTION_BOOST_GEN  = 0
ACTION_USE_BATT   = 1
ACTION_USE_SUPER  = 2
ACTION_SHIFT_LOAD = 3
ACTION_REROUTE    = 4


def choose_action(state, grid_state: Optional[dict] = None) -> int:
    """Return the action id the rule ladder would choose.

    Parameters
    ----------
    state : Any
        Unused. The DQN state vector is not consumed by the rule ladder;
        we accept it for interface parity with policy interfaces.
    grid_state : dict, optional
        The output of ``SmartGrid.get_state()``. Expected keys:
        ``system.balance``, ``nodes.{failed, isolated, load}``.

    Returns
    -------
    int
        Action id in {0, 1, 2, 3, 4}.
    """
    sys_info = (grid_state or {}).get("system", {})
    nodes    = (grid_state or {}).get("nodes", {})

    balance = sys_info.get("balance", 0.0)
    n_failed  = sum(1 for n in nodes.values() if n.get("failed"))
    n_isolated = sum(1 for n in nodes.values() if n.get("isolated"))
    has_spike  = any(n.get("load", 0) > 1.2 for n in nodes.values())

    # Priority 1 — failures always trigger reroute.
    if n_failed > 0 or n_isolated > 0:
        return ACTION_REROUTE
    # Priority 2 — transient spike → supercap.
    if has_spike:
        return ACTION_USE_SUPER
    # Priority 3 — generation balance.
    if balance < -0.3:
        return ACTION_BOOST_GEN
    if balance < -0.1:
        return ACTION_USE_BATT
    # Default — defer non-critical load.
    return ACTION_SHIFT_LOAD
"""
rewards.py — modular reward decomposition for the RL agent.

Why
---
A research-grade RL paper must be able to ablate reward components.
The legacy ``DQNAgent.compute_reward`` is one opaque function; here
we expose it as a weighted sum of named components, each a callable
``(state, action, next_state) -> float``.  Each call returns a
``RewardBreakdown`` that carries the per-component values, so the
XAI panel can later explain "this action's reward was −0.42,
driven mainly by critical_load_restored (+0.18) and overload_penalty
(−0.6)".

Components implemented here:
  - ``critical_load_restored`` : +1 per critical node that regained power.
  - ``outage_penalty``         : −1 per node that lost power.
  - ``overload_penalty``       : −1 per overloaded edge.
  - ``switching_cost``         : −0.1 per switch toggled.
  - ``renewable_usage``        : +0.1 × fraction of renewable output used.
  - ``reliability_bonus``      : +0.5 if reliability index > 0.8.
  - ``voltage_stability_bonus``: +0.2 if no node voltage < 0.92 pu.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict


@dataclass
class RewardBreakdown:
    total: float = 0.0
    components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"total": self.total, "components": dict(self.components)}


def _count_critical_restored(state: Dict[str, Any], next_state: Dict[str, Any]) -> int:
    """Count critical nodes that newly regained power."""
    # The state schema is opaque here; we look for the ``node_states``
    # key populated by ``simulation.grid.get_state``.
    cur = state.get("node_states", {}) or {}
    nxt = next_state.get("node_states", {}) or {}
    crit_types = {"hospital", "hospital_icu", "gov_building"}
    delta = 0
    for nid, info in nxt.items():
        if info.get("node_type") not in crit_types:
            continue
        was_off = not (cur.get(nid, {}).get("received_power", 0.0) > 0.0)
        is_on = info.get("received_power", 0.0) > 0.0
        if was_off and is_on:
            delta += 1
    return delta


def _count_new_outages(state: Dict[str, Any], next_state: Dict[str, Any]) -> int:
    cur = state.get("node_states", {}) or {}
    nxt = next_state.get("node_states", {}) or {}
    delta = 0
    for nid, info in nxt.items():
        if not info.get("failed", False):
            continue
        if not cur.get(nid, {}).get("failed", False):
            delta += 1
    return delta


def _count_overloaded_edges(next_state: Dict[str, Any]) -> int:
    edges = next_state.get("edges", {}) or {}
    delta = 0
    for ed in edges.values():
        flow = float(ed.get("flow", 0.0))
        cap = float(ed.get("capacity", 1.0))
        if cap > 0 and abs(flow) > 0.95 * cap:
            delta += 1
    return delta


def _switching_cost(action: Dict[str, Any]) -> int:
    name = (action or {}).get("name", "")
    if name in {"open_switch", "close_switch", "reconfigure_feeder"}:
        return 1
    if name == "merge_island":
        return 1
    return 0


def _renewable_usage_fraction(next_state: Dict[str, Any]) -> float:
    nodes = next_state.get("node_states", {}) or {}
    gen = 0.0
    ren = 0.0
    for info in nodes.values():
        g = float(info.get("generation", 0.0))
        gen += g
        if info.get("node_type") in {"solar_farm", "wind_farm",
                                      "generator_solar", "generator_wind"}:
            ren += g
    if gen <= 0:
        return 0.0
    return max(0.0, min(1.0, ren / gen))


def _reliability(next_state: Dict[str, Any]) -> float:
    return float(next_state.get("reliability_index", 0.0))


def _min_voltage(next_state: Dict[str, Any]) -> float:
    nodes = next_state.get("node_states", {}) or {}
    if not nodes:
        return 1.0
    return min(float(info.get("voltage", 1.0)) for info in nodes.values())


@dataclass
class RewardComposer:
    """Linear weighted combination of named reward components."""

    w_critical_restored: float = 1.0
    w_outage_penalty: float = -1.0
    w_overload_penalty: float = -0.5
    w_switching_cost: float = -0.1
    w_renewable_usage: float = 0.3
    w_reliability_bonus: float = 0.5
    w_voltage_bonus: float = 0.2
    # M5 (EHM upgrade) — carbon / economic penalty weights.
    # These are pulled into the weighted sum only when the corresponding
    # key (``carbon_kg`` or ``economic_usd``) is present in
    # ``state`` or ``next_state``.  Defaults are conservative.
    w_carbon_penalty: float = -0.05
    w_economic_penalty: float = -0.02

    components: Dict[str, Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any]], float]] = field(
        default_factory=lambda: {
            "critical_load_restored": lambda s, a, n: float(
                _count_critical_restored(s, n)
            ),
            "outage_penalty": lambda s, a, n: float(_count_new_outages(s, n)),
            "overload_penalty": lambda s, a, n: float(_count_overloaded_edges(n)),
            "switching_cost": lambda s, a, n: float(_switching_cost(a)),
            "renewable_usage": lambda s, a, n: _renewable_usage_fraction(n),
            "reliability_bonus": lambda s, a, n: 1.0 if _reliability(n) > 0.8 else 0.0,
            "voltage_stability_bonus": lambda s, a, n: 1.0 if _min_voltage(n) > 0.92 else 0.0,
        }
    )

    def compute(
        self,
        state: Dict[str, Any],
        action: Dict[str, Any],
        next_state: Dict[str, Any],
    ) -> RewardBreakdown:
        weights = {
            "critical_load_restored": self.w_critical_restored,
            "outage_penalty": self.w_outage_penalty,
            "overload_penalty": self.w_overload_penalty,
            "switching_cost": self.w_switching_cost,
            "renewable_usage": self.w_renewable_usage,
            "reliability_bonus": self.w_reliability_bonus,
            "voltage_stability_bonus": self.w_voltage_bonus,
        }
        bd = RewardBreakdown()
        total = 0.0
        for name, fn in self.components.items():
            value = float(fn(state, action, next_state))
            weight = float(weights.get(name, 0.0))
            contrib = weight * value
            bd.components[name] = contrib
            total += contrib
        # M5 (EHM upgrade) — carbon / economic penalties are read
        # directly from ``state`` / ``next_state`` (populated by the
        # ``/metrics/carbon`` endpoint or by an inline cost function).
        try:
            carbon_kg = float(next_state.get("carbon_kg")
                              or state.get("carbon_kg", 0.0))
            bd.components["carbon_penalty"] = (
                self.w_carbon_penalty * carbon_kg / 1000.0
            )
            total += bd.components["carbon_penalty"]
        except (TypeError, ValueError):
            pass
        try:
            econ_usd = float(next_state.get("economic_usd")
                             or state.get("economic_usd", 0.0))
            bd.components["economic_penalty"] = (
                self.w_economic_penalty * econ_usd / 1000.0
            )
            total += bd.components["economic_penalty"]
        except (TypeError, ValueError):
            pass
        bd.total = total
        return bd

    # Backward-compat shim — legacy ``DQNAgent.compute_reward`` callers
    # call this with the same signature.
    def legacy(
        self,
        state: Any,
        action: Dict[str, Any],
        next_state: Any,
    ) -> float:
        # The legacy agent sometimes passes a numeric numpy state, not a
        # dict.  We fall back to a stub if the schema isn't recognised.
        if not isinstance(state, dict) or not isinstance(next_state, dict):
            return 0.0
        return self.compute(state, action, next_state).total
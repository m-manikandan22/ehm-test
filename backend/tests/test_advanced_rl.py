"""test_advanced_rl.py — AdvancedDQNAgent + ActionMask + Explainer."""
from __future__ import annotations

import pytest

from rl.action_mask import ActionMask, AdvancedAction
from rl.explainer import RLExplainer
from rl.policy_registry import PolicyRegistry
from rl.advanced_rl_agent import AdvancedDQNAgent, ACTION_NAMES


# ----------------------------------------------------------------------
# Action mask
# ----------------------------------------------------------------------

def _empty_grid():
    class _N:
        def __init__(self, ntype, **kw):
            self.node_type = ntype
            for k, v in kw.items():
                setattr(self, k, v)

    class _E(dict):
        def __init__(self, edges):
            super().__init__(edges)
            self._edges = edges

        def edges(self, data=False):
            return [(u, v, d) for (u, v), d in self._edges.items()]

    return type("G", (), {
        "nodes": {
            "g1": _N("generator_coal", failed=False),
            "h1": _N("house", failed=False, received_power=1.0),
            "b1": _N("battery", battery_level=0.5, failed=False),
        },
        "graph": _E({
            ("t1", "t2"): {"is_tie_switch": True, "switch_status": "open"},
        }),
    })()


def test_action_mask_default_all_true():
    mask = ActionMask(legal={})
    assert mask.as_array() == [True] * 9


def test_action_mask_close_switch_requires_open_tie():
    mask = ActionMask.from_grid(_empty_grid())
    assert mask.allows(AdvancedAction.CLOSE_SWITCH) is True


def test_action_mask_open_switch_requires_closed_tie():
    # No closed ties → OPEN_SWITCH should be False.
    mask = ActionMask.from_grid(_empty_grid())
    assert mask.allows(AdvancedAction.OPEN_SWITCH) is False


def test_action_mask_discharge_requires_soc():
    mask = ActionMask.from_grid(_empty_grid())
    # SOC 0.5 > 0.1 → allowed.
    assert mask.allows(AdvancedAction.DISCHARGE_BATTERY) is True


def test_action_mask_disconnect_load_requires_powered_load():
    mask = ActionMask.from_grid(_empty_grid())
    assert mask.allows(AdvancedAction.DISCONNECT_LOAD) is True


def test_action_mask_no_op_always_legal():
    mask = ActionMask.from_grid(_empty_grid())
    assert mask.allows(AdvancedAction.NO_OP) is True


# ----------------------------------------------------------------------
# Explainer
# ----------------------------------------------------------------------

def test_explainer_returns_top_features():
    ex = RLExplainer(n_top_features=3, n_alternatives=2)
    report = ex.explain(
        features={"voltage": [0.85, 1.0, 1.1], "load": [0.7]},
        q_values=[0.1, 0.5, 0.9, 0.0, 0.2],
        chosen_action=2,
        action_names=["a", "b", "c", "d", "e"],
    )
    assert len(report.why) == 3
    assert all("feature" in w and "importance" in w for w in report.why)
    assert len(report.alternatives) == 2
    assert 0.0 <= report.confidence <= 1.0
    assert report.expected_benefit == 0.9


def test_explainer_handles_empty_inputs():
    ex = RLExplainer()
    report = ex.explain(
        features={},
        q_values=[0.0],
        chosen_action=0,
        action_names=["x"],
    )
    assert report.why == []
    assert report.alternatives == []
    assert report.confidence == 1.0


def test_explainer_alternatives_exclude_chosen():
    ex = RLExplainer(n_alternatives=10)
    report = ex.explain(
        features={"x": [1.0]},
        q_values=[0.5, 0.7, 0.9, 0.1],
        chosen_action=2,
        action_names=["a", "b", "c", "d"],
    )
    assert all(alt["action_id"] != 2 for alt in report.alternatives)


# ----------------------------------------------------------------------
# Policy registry
# ----------------------------------------------------------------------

def test_policy_registry_register_and_create():
    reg = PolicyRegistry()
    reg.register("noop", lambda: "noop_agent")
    assert reg.has("noop")
    assert "noop" in reg.names()
    assert reg.create("noop") == "noop_agent"


def test_policy_registry_unknown_raises():
    reg = PolicyRegistry()
    with pytest.raises(KeyError):
        reg.create("nope")


def test_policy_registry_clear():
    reg = PolicyRegistry()
    reg.register("a", lambda: 1)
    reg.clear()
    assert not reg.has("a")


# ----------------------------------------------------------------------
# Advanced agent
# ----------------------------------------------------------------------

def test_advanced_agent_select_action_returns_legal_action():
    agent = AdvancedDQNAgent()
    grid = _empty_grid()
    action = agent.select_action(grid, state={})
    assert 0 <= action <= 8
    assert action != int(AdvancedAction.OPEN_SWITCH)  # no closed ties


def test_advanced_agent_records_xai_after_decision():
    agent = AdvancedDQNAgent()
    grid = _empty_grid()
    agent.select_action(grid, state={})
    assert agent.last_xai is not None
    assert agent.explain_last() is not None


def test_advanced_agent_action_names_complete():
    """Every AdvancedAction has a friendly name."""
    for a in AdvancedAction:
        assert int(a) in ACTION_NAMES
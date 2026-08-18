"""test_state_builder.py — StateBuilder + RewardComposer unit tests."""
from __future__ import annotations

import pytest

from rl.state_builder import StateBuilder
from rl.rewards import RewardComposer


def _empty_grid():
    """Bare-bones stand-in for SmartGrid (subset of attributes used)."""

    class _N:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class _G:
        def __init__(self):
            self.nodes = {
                "n1": _N(node_type="house", voltage=1.0, frequency=50.0,
                         load=0.4, generation=0.05, battery_level=0.5,
                         stress_level=0.2, load_history=[0.3, 0.4]),
                "n2": _N(node_type="solar_farm", voltage=1.05, frequency=50.0,
                         load=0.0, generation=1.5, battery_level=0.0,
                         stress_level=0.0, load_history=[0.0]),
                "n3": _N(node_type="battery", voltage=1.0, frequency=50.0,
                         load=0.0, generation=0.0, battery_level=0.8,
                         stress_level=0.0, load_history=[]),
            }
            # Empty DiGraph-like stand-in.
            self.graph = type("E", (), {})()

    return _G()


def test_state_builder_returns_features_and_vector():
    sb = StateBuilder()
    out = sb.build(_empty_grid())
    assert "features" in out and "vector" in out
    assert isinstance(out["features"], dict)
    assert isinstance(out["vector"], list)
    assert len(out["vector"]) > 0
    # All named extractors produced something.
    for k in ("voltage", "frequency", "load_forecast", "battery_soc",
              "renewable", "congestion", "node_stress", "switches", "weather"):
        assert k in out["features"]


def test_voltage_features_have_mean_min_max_count():
    sb = StateBuilder()
    out = sb.build_features(_empty_grid())
    assert len(out["voltage"]) == 4


def test_renewable_features_count_solar():
    sb = StateBuilder()
    out = sb.build_features(_empty_grid())
    # solar_farm contributes 1.5 of 1.55 total gen
    assert out["renewable"][0] == pytest.approx(1.5, rel=1e-3)


def test_state_builder_handles_missing_attributes():
    """Empty grid shouldn't crash the extractors."""

    class _G:
        nodes = {}
        graph = type("E", (), {})()

    sb = StateBuilder()
    out = sb.build(_G())
    assert out["vector"] == [] or all(isinstance(v, (int, float))
                                       for v in out["vector"])


def test_reward_composer_total_is_sum_of_components():
    rc = RewardComposer()
    state = {"node_states": {}}
    next_state = {"node_states": {}, "edges": {}, "reliability_index": 0.0}
    action = {"name": "no_op"}
    bd = rc.compute(state, action, next_state)
    assert bd.total == pytest.approx(sum(bd.components.values()), rel=1e-9)


def test_reward_composer_components_are_present():
    rc = RewardComposer()
    state = {"node_states": {}}
    next_state = {"node_states": {}, "edges": {}}
    bd = rc.compute(state, {"name": "no_op"}, next_state)
    for key in ("critical_load_restored", "outage_penalty",
                "overload_penalty", "switching_cost",
                "renewable_usage", "reliability_bonus",
                "voltage_stability_bonus"):
        assert key in bd.components


def test_reward_critical_restored_counts_new_power():
    rc = RewardComposer()
    state = {
        "node_states": {
            "HOSP": {"node_type": "hospital", "received_power": 0.0,
                     "failed": False},
        },
    }
    next_state = {
        "node_states": {
            "HOSP": {"node_type": "hospital", "received_power": 1.0,
                     "failed": False},
        },
    }
    bd = rc.compute(state, {"name": "no_op"}, next_state)
    assert bd.components["critical_load_restored"] == 1.0


def test_reward_switching_cost_for_open_switch():
    rc = RewardComposer()
    state = {"node_states": {}}
    next_state = {"node_states": {}, "edges": {}}
    bd = rc.compute(state, {"name": "open_switch"}, next_state)
    assert bd.components["switching_cost"] == -0.1


def test_reward_overload_penalty_counts_overloaded_edge():
    rc = RewardComposer()
    state = {"node_states": {}}
    next_state = {
        "node_states": {},
        "edges": {"e1": {"flow": 5.0, "capacity": 1.0}},
    }
    bd = rc.compute(state, {"name": "no_op"}, next_state)
    assert bd.components["overload_penalty"] == -0.5
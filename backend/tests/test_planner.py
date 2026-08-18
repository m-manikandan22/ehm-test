"""test_planner.py — AI planner and topology-KPI tests."""
from __future__ import annotations

import math

import pytest

from city.city_generator import CityGenerator
from city.city_profile import CityProfile
from planning.ai_planner import AIPlanner, PlannerConfig, PlanAction
from planning.objectives import (
    expected_outage_energy,
    power_loss_mw,
    reliability_index,
    restoration_time_lower_bound,
    voltage_drop_index,
)
from planning.topology_kpis import (
    all_kpis,
    avg_path_length,
    generator_nodes,
    load_nodes,
    mesh_index,
    redundancy_score,
)
from simulation.grid import SmartGrid


def _grid() -> SmartGrid:
    return CityGenerator(CityProfile(population=50_000, seed=42)).generate()


# ----------------------------------------------------------------------
# topology KPIs
# ----------------------------------------------------------------------

def test_load_and_generator_nodes_partition():
    g = _grid()
    loads = set(load_nodes(g))
    gens = set(generator_nodes(g))
    # No overlap.
    assert loads.isdisjoint(gens)
    # At least one of each.
    assert loads and gens


def test_mesh_index_is_positive():
    g = _grid()
    assert mesh_index(g) > 0.0


def test_redundancy_score_in_zero_one():
    g = _grid()
    score = redundancy_score(g)
    assert 0.0 <= score <= 1.0


def test_avg_path_length_finite_for_connected_grid():
    g = _grid()
    apl = avg_path_length(g)
    assert math.isfinite(apl)
    assert apl > 0


def test_all_kpis_returns_four_keys():
    g = _grid()
    k = all_kpis(g)
    assert set(k.keys()) == {
        "avg_path_length", "mesh_index", "redundancy_score",
        "articulation_count",
    }


# ----------------------------------------------------------------------
# objective functions
# ----------------------------------------------------------------------

def test_objectives_are_floats():
    g = _grid()
    assert isinstance(expected_outage_energy(g), float)
    assert isinstance(voltage_drop_index(g), float)
    assert isinstance(power_loss_mw(g), float)
    assert isinstance(reliability_index(g), float)
    assert isinstance(restoration_time_lower_bound(g), float)


def test_reliability_index_in_zero_one():
    g = _grid()
    rel = reliability_index(g)
    assert 0.0 <= rel <= 1.0


def test_voltage_drop_is_non_negative():
    g = _grid()
    assert voltage_drop_index(g) >= 0.0


def test_power_loss_is_non_negative():
    g = _grid()
    assert power_loss_mw(g) >= 0.0


# ----------------------------------------------------------------------
# AI planner
# ----------------------------------------------------------------------

def test_planner_returns_list():
    g = _grid()
    planner = AIPlanner(g, config=PlannerConfig(max_iterations=4))
    actions = planner.plan()
    assert isinstance(actions, list)
    for a in actions:
        assert isinstance(a, PlanAction)
        assert a.kind in {
            "add_tie_switch", "add_backup_path", "add_feeder",
            "add_transformer", "add_battery", "add_solar",
            "connect_hospital", "add_redundancy", "branch_feeder",
        }
        assert a.expected_delta >= 0.0


def test_planner_to_dict_round_trip():
    g = _grid()
    action = PlanAction(
        kind="add_tie_switch",
        params={"u": "DS_PS0_0", "v": "DS_PS0_1"},
        expected_delta=0.123,
        rationale="Adds redundancy",
    )
    payload = action.to_dict()
    assert payload["kind"] == "add_tie_switch"
    assert payload["params"]["u"] == "DS_PS0_0"
    assert payload["expected_delta"] == pytest.approx(0.123, rel=1e-9)


def test_planner_does_not_mutate_grid():
    g = _grid()
    edge_count_before = g.graph.number_of_edges()
    planner = AIPlanner(g, config=PlannerConfig(max_iterations=2))
    planner.plan()
    # The planner applies candidates in a try/finally so the grid is
    # restored; the edge count must be unchanged.
    assert g.graph.number_of_edges() == edge_count_before


def test_planner_config_computes_cost():
    cfg = PlannerConfig()
    cost = cfg.cost(
        outage=1.0, v_drop=0.5, loss=0.2, rel=0.9, rest=3.0,
    )
    expected = (
        cfg.w_outage * 1.0
        + cfg.w_voltage_drop * 0.5
        + cfg.w_power_loss * 0.2
        - cfg.w_reliability * 0.9
        + cfg.w_restoration * 3.0
    )
    assert cost == pytest.approx(expected, rel=1e-9)

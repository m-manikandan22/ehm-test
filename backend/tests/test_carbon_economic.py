"""test_carbon_economic.py — unit tests for the carbon / economic
metrics module."""

from __future__ import annotations

import pytest

from metrics.carbon_economic import (
    VOLL_USD_PER_MWH,
    compute_step_cost,
    carbon_penalty,
    economic_penalty,
)


class _Node:
    def __init__(self, ntype, generation=0.0, load=0.0,
                 failed=False, voltage=1.0):
        self.node_type = ntype
        self.generation = generation
        self.load = load
        self.failed = failed
        self.voltage = voltage


class _Grid:
    def __init__(self, nodes):
        self.nodes = nodes


def test_carbon_zero_for_passive_grid():
    grid = _Grid({
        "h1": _Node("house", load=0.5),
        "h2": _Node("house", load=0.3),
    })
    out = compute_step_cost(grid)
    assert out.carbon_kg == 0.0
    assert out.economic_usd == 0.0


def test_carbon_uses_emission_factors():
    grid = _Grid({
        "g_coal": _Node("generator_coal", generation=10.0),
        "g_wind": _Node("wind_farm", generation=5.0),
    })
    out = compute_step_cost(grid)
    expected = 820.0 * 10.0 + 11.0 * 5.0
    assert abs(out.carbon_kg - expected) < 1e-6


def test_failed_nodes_are_skipped():
    grid = _Grid({
        "g": _Node("generator_coal", generation=10.0, failed=True),
    })
    out = compute_step_cost(grid)
    assert out.carbon_kg == 0.0


def test_load_shedding_increases_economic_cost():
    grid = _Grid({
        "h1": _Node("house", load=2.0, failed=True),
        "h2": _Node("house", load=1.0),
    })
    out = compute_step_cost(grid)
    expected_voll = VOLL_USD_PER_MWH * 2.0
    assert abs(out.energy_not_served_mwh - 2.0) < 1e-6
    assert out.economic_usd >= expected_voll


def test_voltage_penalty_applied_outside_band():
    grid = _Grid({
        "h1": _Node("house", load=1.0, voltage=0.85),
    })
    out = compute_step_cost(grid)
    assert out.voltage_penalty_usd > 0.0


def test_voltage_penalty_zero_in_band():
    grid = _Grid({
        "h1": _Node("house", load=1.0, voltage=1.02),
    })
    out = compute_step_cost(grid)
    assert out.voltage_penalty_usd == 0.0


def test_to_dict_serialisable():
    grid = _Grid({
        "g": _Node("generator_coal", generation=1.0),
        "h": _Node("house", load=0.5),
    })
    out = compute_step_cost(grid).to_dict()
    assert set(out.keys()) >= {
        "carbon_kg", "economic_usd",
        "energy_not_served_mwh", "voltage_penalty_usd",
        "components",
    }


def test_carbon_penalty_scales():
    assert carbon_penalty({"carbon_kg": 1000.0}) == -1.0
    assert carbon_penalty({"carbon_kg": 0.0}) == 0.0


def test_economic_penalty_scales():
    assert economic_penalty({"economic_usd": 5000.0}) == -5.0


def test_components_include_per_node_breakdown():
    grid = _Grid({
        "g_coal": _Node("generator_coal", generation=2.0),
        "g_wind": _Node("wind_farm", generation=1.0),
        "h_failed": _Node("house", load=1.5, failed=True),
    })
    out = compute_step_cost(grid).to_dict()
    assert any(k.startswith("carbon:") for k in out["components"])
    assert any(k.startswith("gencost:") for k in out["components"])
    assert any(k.startswith("voll:") for k in out["components"])

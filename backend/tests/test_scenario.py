"""test_scenario.py — Deterministic scenario generator validation.

Veres (1) every fault target in a generated Scenario actually exists in
the SmartGrid the runner will replay it on, and (2) the candidate set
includes main-feeder distribution poles / transformers (the assets
FLISR can physically heal).
"""
from __future__ import annotations

import pytest

from experiments.scenario import (
    FaultEvent,
    Scenario,
    make_scenario,
    _grid_fault_candidates,
)


# ── (1) make_scenario produces valid target IDs ──────────────────────
def test_make_scenario_targets_exist_in_grid():
    """Every fault target must be present in the default 49-node SmartGrid.

    This guards against the pre-existing bug in which `make_scenario`
    sampled node IDs that did not exist in the actual grid, causing
    `grid.inject_failure(target)` to raise KeyError on the very first
    injected fault.
    """
    # Force the scenario cache to populate.
    candidates = _grid_fault_candidates()
    assert candidates, "expected at least one fault-eligible node"
    # Build a real grid and a scenario for a fixed seed.
    from simulation.grid import SmartGrid
    grid = SmartGrid()
    grid_ids = set(grid.nodes.keys())

    scen = make_scenario(
        seed=42, total_steps=40, fault_count=5, weather_mode="normal",
    )
    assert len(scen.faults) == 5
    for f in scen.faults:
        assert f.target in grid_ids, (
            f"scenario fault target {f.target!r} is not a grid node; "
            "this would crash grid.inject_failure"
        )


# ── (2) Targets are the assets FLISR can physically heal ──────────────
def test_fault_targets_are_healable_assets():
    """Fault targets must be on the main feeder (pole/transformer),
    not leaf loads (house, hospital) — leaves cannot be rerouted
    around and would bias restoration metrics to zero.
    """
    from simulation.grid import SmartGrid
    grid = SmartGrid()
    healable_types = {"pole", "transformer"}
    bad_targets = []
    for f in make_scenario(seed=7, total_steps=30, fault_count=4).faults:
        node = grid.nodes.get(f.target)
        if node is None or getattr(node, "node_type", "") not in healable_types:
            bad_targets.append((f.target, getattr(node, "node_type", "MISSING")))
    assert not bad_targets, (
        f"healer-irrelevant fault targets produced: {bad_targets}"
    )


# ── (3) Determinism ──────────────────────────────────────────────────
def test_make_scenario_is_deterministic_for_fixed_seed():
    """Same seed → same fault list."""
    a = make_scenario(seed=123, total_steps=20, fault_count=3)
    b = make_scenario(seed=123, total_steps=20, fault_count=3)
    assert [(f.timestep, f.target, f.duration_steps) for f in a.faults] == [
        (f.timestep, f.target, f.duration_steps) for f in b.faults
    ]


# ── (4) Different seeds → different scenarios ─────────────────────────
def test_different_seeds_change_fault_list():
    """Two seeds must produce at least one different fault target."""
    a = make_scenario(seed=1, total_steps=30, fault_count=5)
    b = make_scenario(seed=2, total_steps=30, fault_count=5)
    a_targets = {f.target for f in a.faults}
    b_targets = {f.target for f in b.faults}
    assert a_targets != b_targets


# ── (5) Edge case — zero faults ───────────────────────────────────────
def test_zero_faults_returns_empty_list():
    scen = make_scenario(seed=0, total_steps=20, fault_count=0)
    assert scen.faults == []
    assert scen.total_steps == 20


# ── (6) Edge case — short run still produces well-formed faults ──────
def test_short_run_produces_valid_faults():
    """total_steps=8 with fault_count=2 still produces valid targets."""
    from simulation.grid import SmartGrid
    grid = SmartGrid()
    grid_ids = set(grid.nodes.keys())
    scen = make_scenario(seed=99, total_steps=8, fault_count=2)
    assert len(scen.faults) == 2
    for f in scen.faults:
        assert f.target in grid_ids
        assert 5 <= f.timestep <= 6, (
            f"fault timestep {f.timestep} out of expected band [5,6]"
        )
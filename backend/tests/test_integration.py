"""
test_integration.py — end-to-end smoke test for the full stack.

Why
---
A research-grade project must demonstrate the whole pipeline works
together, not just individual units.  This test exercises:

  1. Generate a procedural city
  2. Run a few simulation steps (with weather + smart faults + microgrid)
  3. Compute IEEE 1366 metrics
  4. Apply the AI planner + redesign loop
  5. Render an XAI report

If any of these throws, the test fails — which catches regressions
in the wiring between modules.
"""
from __future__ import annotations

import pytest

from city.city_generator import CityGenerator
from city.city_profile import CityProfile
from digital_twin.twin_registry import TwinRegistry
from faults.smart_fault_injector import SmartFaultInjector
from improvement.evaluator import SimulationEvaluator
from improvement.redesigner import Redesigner
from metrics.ieee_1366 import saifi, saidi, caidi, maifi, asai, ens_mwh
from microgrid.microgrid_controller import MicrogridController
from rl.advanced_rl_agent import AdvancedDQNAgent
from rl.explainer import RLExplainer
from rl.state_builder import StateBuilder
from weather.weather_engine import WeatherEngine, WeatherState


def test_full_pipeline():
    # 1. Generate city.
    grid = CityGenerator(CityProfile(population=20_000, seed=42)).generate()
    assert len(grid.nodes) > 0

    # 2. Twins + weather + faults + microgrid.
    twins = TwinRegistry()
    twins.register(grid)
    twins.sync(grid, dt_hours=1.0)
    assert len(twins) == len(grid.nodes)

    weather = WeatherEngine(seed=42)
    weather.set(WeatherState.STORM)
    inj = SmartFaultInjector(seed=42, expected_per_step=1.0)
    events = inj.inject(weather.state, grid)
    # Events are random — we just require the call doesn't raise.
    _ = events

    microgrid = MicrogridController()
    islands = microgrid.form_islands(grid, faulted_nodes=[])
    assert islands

    # 3. Run a few steps and snapshot.
    ev = SimulationEvaluator()
    for t in range(3):
        # NOTE: solver exceptions now surface loudly. If a regression
        # breaks update_power_flow(), the test fails (no silent pass).
        grid.update_generation()
        grid.update_power_flow()
        ev.record_step(SimulationEvaluator.snapshot_from_grid(grid, t))
    s = ev.summary()
    # IEEE 1366 keys present.
    for k in ("ieee_saifi", "ieee_saidi", "ieee_caidi",
              "ieee_maifi", "ieee_asai", "ieee_ens_mwh"):
        assert k in s

    # Sanity: index function calls succeed on synthetic arrays.
    s_val = saifi([1000], [2000])
    assert s_val == 2.0
    sd_val = saidi([60000], [1000])
    assert sd_val == 60.0
    ens_val = ens_mwh([1.0], [60.0])
    assert ens_val == pytest.approx(1.0, rel=1e-3)

    # 4. AI planner + redesigner.
    redesigner = Redesigner()
    report = redesigner.propose(grid, s)
    assert report.actions_proposed >= 0

    # 5. Advanced RL agent + XAI.
    agent = AdvancedDQNAgent()
    state = {"node_states": {}, "edges": {}, "islands": []}
    action = agent.select_action(grid, state)
    assert 0 <= action <= 8
    xai = agent.explain_last()
    assert xai is not None
    assert xai.confidence >= 0.0

    # StateBuilder should produce a vector of length > 0.
    sb = StateBuilder()
    feats = sb.build_features(grid)
    assert isinstance(feats, dict)
    assert any(len(v) > 0 for v in feats.values())


def test_redesigner_does_not_corrupt_live_grid():
    grid = CityGenerator(CityProfile(population=15_000, seed=5)).generate()
    n_before = len(grid.nodes)
    e_before = grid.graph.number_of_edges()
    Redesigner().propose(grid, {"n_nodes": n_before})
    assert len(grid.nodes) == n_before
    assert grid.graph.number_of_edges() == e_before


def test_pipeline_with_seed_is_reproducible():
    g1 = CityGenerator(CityProfile(population=12_000, seed=42)).generate()
    g2 = CityGenerator(CityProfile(population=12_000, seed=42)).generate()
    assert sorted(g1.nodes) == sorted(g2.nodes)


def test_explainer_handles_random_action_selection():
    grid = CityGenerator(CityProfile(population=10_000, seed=1)).generate()
    agent = AdvancedDQNAgent()
    state = {"node_states": {}, "edges": {}, "islands": []}
    for _ in range(5):
        agent.select_action(grid, state)
        assert agent.explain_last() is not None
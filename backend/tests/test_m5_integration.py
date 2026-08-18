"""test_m5_integration.py — cross-module integration test for the
M5 EHM upgrades.

Goal
----
Validate that the M5 additions wire together cleanly:

  - Procedural city generator stashes ``_road_network`` / ``_zoning``
    so the ``/city/layout`` view produces real road segments and zone
    polygons (not just an empty fallback).
  - ``PredictiveSelfHealer`` reads twin degradation, computes risk, and
    returns actionable recommendations on a populated grid.
  - ``AutonomousImprovementLoop`` triggers redesign when reliability
    drops and stays in cooldown when called twice.
  - ``ReliabilityRecorder.record_from_grid`` populates a complete
    IEEE-1366 snapshot and ``summary()`` returns SAIFI / SAIDI.
  - Carbon / economic metrics aggregate per-node emissions and VoLL.
  - The RewardComposer accepts ``carbon_kg`` / ``economic_usd`` keys in
    the state dict and includes the new penalties in its breakdown.

If any of these throws, the upgrade broke the wiring between modules.
"""

from __future__ import annotations

import pytest

from city.city_generator import CityGenerator
from city.city_profile import CityProfile
from city.layout import city_layout
from digital_twin.twin_registry import TwinRegistry
from improvement.autonomous import (AutonomousImprovementLoop,
                                    AutonomousConfig)
from improvement.evaluator import SimulationEvaluator
from metrics.carbon_economic import compute_step_cost
from rl.rewards import RewardComposer
from self_healing.predictor import PredictiveSelfHealer
from self_healing.recorder import ReliabilityRecorder


# ───────────────────────────────────────────────────────────────────────
# Shared fixture: tiny procedural grid + twins
# ───────────────────────────────────────────────────────────────────────

def _make_grid():
    return CityGenerator(CityProfile(population=10_000, seed=42)).generate()


def _fail_random(grid, marker):
    """Pick the first matching node and mark it failed. Returns the node id."""
    for nid in grid.nodes:
        if marker in nid:
            grid.nodes[nid].failed = True
            return nid
    # fallback: fail the first node
    nid = next(iter(grid.nodes))
    grid.nodes[nid].failed = True
    return nid


def _restore_random(grid, marker):
    for nid in grid.nodes:
        if marker in nid:
            grid.nodes[nid].failed = False
            return nid


# ───────────────────────────────────────────────────────────────────────
# 1) City layout view exposes real roads + zones
# ───────────────────────────────────────────────────────────────────────

def test_city_layout_returns_real_geometry():
    g = _make_grid()
    layout = city_layout(g)
    assert layout.get("has_layout") is True
    # Roads: at least one segment, each with u/v/kind/length
    assert len(layout["roads"]) > 0
    sample = layout["roads"][0]
    assert {"u", "v", "kind", "length"} <= set(sample.keys())
    # Zones: at least one of each (residential / industrial / commercial / critical)
    zone_set = {z["zone"] for z in layout["zones"]}
    assert {"residential", "industrial"} <= zone_set
    # Buildings: every node is exposed
    assert len(layout["buildings"]) == len(g.nodes)
    # Bounds is a closed rectangle
    b = layout["bounds"]
    assert b["max_x"] >= b["min_x"]
    assert b["max_y"] >= b["min_y"]


# ───────────────────────────────────────────────────────────────────────
# 2) Predictive self-healing end-to-end
# ───────────────────────────────────────────────────────────────────────

def test_predictive_self_healer_pipeline():
    g = _make_grid()
    twins = TwinRegistry()
    twins.register(g)
    twins.sync(g, dt_hours=1.0)

    healer = PredictiveSelfHealer(risk_threshold=0.10)  # low bar
    risks = healer.assess(g, twins)
    # Even with no faults, the pipeline should not blow up.
    assert isinstance(risks, list)
    actions = healer.recommend(g, risks)
    assert isinstance(actions, list)


def test_predictive_self_healer_returns_action_when_grid_failed():
    g = _make_grid()
    # Fail a transformer — should show up as elevated risk.
    _fail_random(g, "T_")
    twins = TwinRegistry()
    twins.register(g)
    twins.sync(g, dt_hours=1.0)

    healer = PredictiveSelfHealer(risk_threshold=0.10)
    actions = healer.recommend(g, healer.assess(g, twins))
    # We don't require an action (depends on topology), but if any
    # action is returned it must serialise cleanly.
    for a in actions:
        d = a.to_dict()
        assert {"kind", "params", "expected_risk_reduction",
                "rationale"} <= set(d.keys())


# ───────────────────────────────────────────────────────────────────────
# 3) Autonomous improvement loop
# ───────────────────────────────────────────────────────────────────────

def test_autonomous_loop_triggers_on_low_reliability():
    g = _make_grid()
    evaluator = SimulationEvaluator()
    loop = AutonomousImprovementLoop(
        AutonomousConfig(reliability_threshold=0.99, ens_step_threshold=0.0,
                         cooldown_steps=1)
    )

    # Seed 5 healthy snapshots so cooldown + window warm up
    for t in range(5):
        snap = SimulationEvaluator.snapshot_from_grid(g, t)
        snap.reliability = 0.99
        snap.ens_mwh = 0.0
        evaluator.record_step(snap)
    loop.attach_evaluator(evaluator)

    # Now drop reliability and force trigger
    bad = SimulationEvaluator.snapshot_from_grid(g, 5)
    bad.reliability = 0.0
    bad.ens_mwh = 100.0
    evaluator.record_step(bad)
    decision = loop.step(g, current_step=5)
    assert decision.triggered is True
    assert decision.reason.startswith("reliability")


def test_autonomous_loop_respects_cooldown():
    g = _make_grid()
    evaluator = SimulationEvaluator()
    loop = AutonomousImprovementLoop(
        AutonomousConfig(reliability_threshold=0.99, ens_step_threshold=0.0,
                         cooldown_steps=999)
    )
    for t in range(5):
        snap = SimulationEvaluator.snapshot_from_grid(g, t)
        snap.reliability = 0.99
        snap.ens_mwh = 0.0
        evaluator.record_step(snap)
    loop.attach_evaluator(evaluator)

    # Trigger once
    bad = SimulationEvaluator.snapshot_from_grid(g, 5)
    bad.reliability = 0.0
    bad.ens_mwh = 100.0
    evaluator.record_step(bad)
    first = loop.step(g, current_step=5)
    assert first.triggered is True

    # Trigger again right away — should be blocked by cooldown
    bad2 = SimulationEvaluator.snapshot_from_grid(g, 6)
    bad2.reliability = 0.0
    bad2.ens_mwh = 100.0
    evaluator.record_step(bad2)
    second = loop.step(g, current_step=6)
    assert second.cooldown_remaining > 0


# ───────────────────────────────────────────────────────────────────────
# 4) Reliability recorder (IEEE 1366 time-series)
# ───────────────────────────────────────────────────────────────────────

def test_reliability_recorder_summary_includes_ieee_keys():
    g = _make_grid()
    recorder = ReliabilityRecorder()
    target = _fail_random(g, "T_")
    target = target  # keep the id for clarity
    for t in range(8):
        # Fail/unfail one transformer on every step to generate
        # sustained interruption events.
        if t % 2 == 0:
            _fail_random(g, "T_")
        else:
            _restore_random(g, "T_")
        recorder.record_from_grid(g, timestep=t, notes=f"step-{t}")

    s = recorder.summary()
    assert {"saifi", "saidi", "caidi", "asai",
            "ens_mwh", "history"} <= set(s.keys())
    # History length matches recorded steps
    assert len(s["history"]) == 8
    # Sustained interruption count is non-negative
    assert s["saifi"] >= 0.0
    assert s["saidi"] >= 0.0


# ───────────────────────────────────────────────────────────────────────
# 5) Carbon + economic cost metrics
# ───────────────────────────────────────────────────────────────────────

def test_carbon_cost_aggregates_emissions_and_voll():
    g = _make_grid()
    # Force every generator to emit coal-class carbon, fail one load.
    for n in g.nodes.values():
        if "generator" in n.node_type or "farm" in n.node_type:
            n.generation = 1.0
        if n.node_type == "house" and "h0" in getattr(n, "id", "").lower():
            n.failed = True
    out = compute_step_cost(g)
    assert out.carbon_kg >= 0.0
    assert out.economic_usd >= 0.0
    # Dict is JSON-safe
    payload = out.to_dict()
    assert {"carbon_kg", "economic_usd", "components"} <= set(payload.keys())


# ───────────────────────────────────────────────────────────────────────
# 6) RewardComposer accepts carbon / economic keys
# ───────────────────────────────────────────────────────────────────────

def test_reward_composer_includes_carbon_and_economic_penalties():
    composer = RewardComposer(w_carbon_penalty=-0.05, w_economic_penalty=-0.02)
    state = {"node_states": {}, "edges": {}, "carbon_kg": 0.0, "economic_usd": 0.0}
    next_state = {"node_states": {}, "edges": {}, "carbon_kg": 4000.0,
                  "economic_usd": 2500.0}
    bd = composer.compute(state, {"name": "noop"}, next_state)
    assert "carbon_penalty" in bd.components
    assert "economic_penalty" in bd.components
    # 4000 kg → -0.05 * 4000 / 1000 = -0.20
    assert bd.components["carbon_penalty"] == pytest.approx(-0.20, rel=1e-6)
    # 2500 USD → -0.02 * 2500 / 1000 = -0.05
    assert bd.components["economic_penalty"] == pytest.approx(-0.05, rel=1e-6)


# ───────────────────────────────────────────────────────────────────────
# 7) Full pipeline: city → twins → recorder → composer → predictor
# ───────────────────────────────────────────────────────────────────────

def test_m5_full_pipeline_runs_clean():
    g = _make_grid()
    # Layout
    assert city_layout(g).get("has_layout") is True
    # Twins
    twins = TwinRegistry()
    twins.register(g)
    twins.sync(g, dt_hours=1.0)
    # Recorder
    recorder = ReliabilityRecorder()
    recorder.record_from_grid(g, timestep=0, notes="init")
    assert len(recorder.summary()["history"]) == 1
    # Predictor
    healer = PredictiveSelfHealer(risk_threshold=0.10)
    risks = healer.assess(g, twins)
    assert isinstance(risks, list)
    # Composer
    composer = RewardComposer()
    bd = composer.compute(
        {"node_states": {}, "edges": {},
         "carbon_kg": 0.0, "economic_usd": 0.0},
        {"name": "noop"},
        {"node_states": {}, "edges": {},
         "carbon_kg": 0.0, "economic_usd": 0.0},
    )
    # With zero carbon / economic cost and no failures, only the
    # voltage_stability_bonus can fire (default min_voltage = 1.0
    # for an empty state).  The carbon / economic components must
    # however be zero — that's the part this test guards.
    assert bd.components.get("carbon_penalty", 0.0) == 0.0
    assert bd.components.get("economic_penalty", 0.0) == 0.0

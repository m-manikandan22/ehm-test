"""test_autonomous.py — unit tests for the autonomous improvement loop."""

from __future__ import annotations

import pytest

from improvement.autonomous import (
    AutonomousConfig,
    AutonomousImprovementLoop,
    ImprovementDecision,
)
from improvement.evaluator import SimulationEvaluator


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


class _Node:
    def __init__(self, ntype, failed=False, load=0.5):
        self.node_type = ntype
        self.failed = failed
        self.load = load
        # Defaults that snapshot_from_grid expects.
        self.voltage = 1.0
        self.frequency = 50.0
        self.generation = 0.0
        self.received_power = 0.5


class _Grid:
    def __init__(self, nodes):
        self.nodes = nodes
        self.timestep = 0


@pytest.fixture
def healthy_grid():
    return _Grid({
        "g1": _Node("generator_coal"),
        "h1": _Node("house"),
        "h2": _Node("house"),
        "h3": _Node("hospital"),
    })


@pytest.fixture
def failing_grid():
    return _Grid({
        "g1": _Node("generator_coal"),
        "h1": _Node("house"),
        "h2": _Node("house"),
        "h3": _Node("hospital", failed=True),
    })


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def test_empty_loop_status_is_perfect():
    loop = AutonomousImprovementLoop()
    out = loop.status()
    assert out["window"] == 0
    assert out["mean_reliability"] == 1.0


def test_healthy_grid_does_not_trigger(healthy_grid):
    loop = AutonomousImprovementLoop()
    # Seed the evaluator with a few healthy steps so the rolling
    # reliability is non-zero before the test step.
    for t in range(5):
        loop._evaluator.record_step(
            SimulationEvaluator.snapshot_from_grid(
                healthy_grid, timestep=t,
            )
        )
    dec = loop.step(healthy_grid, current_step=5)
    assert isinstance(dec, ImprovementDecision)
    # The grid has no critical loads and no failed nodes → reliability
    # remains 1.0; the loop must not trigger a redesign.
    assert dec.triggered is False


def test_failing_grid_triggers_redesign(failing_grid):
    loop = AutonomousImprovementLoop(
        config=AutonomousConfig(reliability_threshold=0.95, cooldown_steps=0),
    )
    # First seed reliability — record a couple of healthy steps so the
    # baseline is reasonable.
    loop._evaluator.record_step(
        SimulationEvaluator.snapshot_from_grid(
            _Grid({"g1": _Node("generator_coal"), "h": _Node("house")}),
            timestep=0,
        )
    )
    dec = loop.step(failing_grid, current_step=1)
    assert dec.triggered is True
    assert "reliability" in dec.reason


def test_cooldown_blocks_repeat_trigger(failing_grid):
    # First trigger the loop (failure → triggered, sets last_trigger_step).
    loop = AutonomousImprovementLoop(
        config=AutonomousConfig(reliability_threshold=0.999,
                                cooldown_steps=50),
    )
    # Trigger once.
    loop.step(failing_grid, current_step=0)
    # Then attempt a second trigger inside the cooldown window.
    dec = loop.step(failing_grid, current_step=1)
    assert dec.triggered is False
    assert "cooldown" in dec.reason


def test_decision_to_dict_is_serialisable():
    dec = ImprovementDecision(
        triggered=False, reason="ok",
        reliability=1.0, ens_per_step=0.0,
        cooldown_remaining=0,
    )
    d = dec.to_dict()
    assert d["triggered"] is False
    assert d["reason"] == "ok"


def test_loop_records_history(healthy_grid):
    loop = AutonomousImprovementLoop()
    for t in range(3):
        loop.step(healthy_grid, current_step=t)
    assert len(loop.history) == 3


def test_loop_reset_clears_state(healthy_grid):
    loop = AutonomousImprovementLoop()
    loop.step(healthy_grid, current_step=0)
    loop.reset()
    assert len(loop.history) == 0
    assert loop.status()["window"] == 0

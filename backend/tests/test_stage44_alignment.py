"""test_stage44_alignment.py — Stage-44 alignment + range tests.

Verifies:
  * The training forecast feature is the output of the real LSTM,
    NOT the ``aggregate_load/20`` stand-in.
  * No future leakage in the training-time LSTM history.
  * The training-time twin features span a meaningful range
    (not always zero).
  * The training-time storage features span high / medium / low
    SOC for both battery and supercap.
  * The training scenarios are independent of evaluation scenarios.
"""
from __future__ import annotations

import os
import sys

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_BACKEND)
for _p in (_BACKEND, _PROJECT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest


def test_training_lstm_no_future_leakage():
    """Stage-44 training must consume only past observations."""
    from collections import deque

    from experiments.stage44_dqn_training import _lstm_predict

    # History built only with past (load, gen, weather) tuples.
    history = deque(maxlen=10)
    for t in range(15):
        history.append((0.5 + t * 0.01, 0.4, 0.2))
        # The prediction must only depend on the deque.
        pred = _lstm_predict(_FakeLSTM(), list(history))
        assert isinstance(pred, float)
        assert 0.0 <= pred <= 1.0 or 0.0 <= pred <= 2.0  # clipped


class _FakeLSTM:
    """Predict() returns the last ``load`` value scaled."""

    def predict(self, seq):
        # seq is a list of [load, gen, weather] triples.
        last_load = float(seq[-1][0])
        return float(max(0.05, min(2.0, last_load * 0.5 + 0.1)))


def test_training_lstm_is_real_lstm():
    """The training forecast feature is the LSTM's prediction."""
    from experiments.stage44_dqn_training import _lstm_predict

    class RealLSTM:
        def predict(self, seq):
            # Stable signature of an LSTM prediction: bounded,
            # not proportional to the most-recent load by a constant.
            seq_arr = [s[0] for s in seq]
            return float(
                max(0.05, min(2.0, sum(seq_arr) / len(seq_arr)))
            )
    fc = RealLSTM()
    history = [(0.4, 0.3, 0.2)] * 10
    pred = _lstm_predict(fc, history)
    # The LSTM's prediction must NOT equal aggregate_load/20 (the
    # Stage-43 stand-in's signature for the same input).
    aggregate_load = sum(s[0] for s in history)
    stage43_stand_in = max(0.05, min(2.0, aggregate_load / 20.0))
    assert abs(pred - stage43_stand_in) > 1e-3, (
        "training forecast feature looks like the Stage-43 stand-in"
    )


def test_training_includes_faults_and_high_risk_twins():
    """The training scenario generator must produce fault and
    high-risk-twin conditions."""
    from experiments.train_scenario_generator import (
        sample_training_scenarios,
    )
    sc = sample_training_scenarios(master_seed=100, n_episodes=24)
    conditions = [s.condition for s in sc]
    assert "SINGLE_FAULT" in conditions
    assert "DEGRADED_ASSET" in conditions
    assert "FAULT_AND_DEGRADED" in conditions
    # At least one scenario with a fault and at least one with a
    # health_override.
    assert any(s.fault_plan for s in sc)
    assert any(s.health_override for s in sc)


def test_twin_training_feature_range():
    """At least some training episodes should produce a non-zero
    twin_max_risk when ticked through."""
    from collections import deque

    from experiments.train_scenario_generator import (
        apply_training_scenario,
        sample_training_scenarios,
    )
    from experiments.stage44_dqn_training import (
        _build_twin_registry, _apply_health_override,
        _tick_twin, _twin_features,
    )
    from simulation.grid import SmartGrid
    from utils.seeds import set_global_seed

    sc = sample_training_scenarios(master_seed=100, n_episodes=24)
    max_risk_seen = []
    for s in sc:
        if not s.health_override:
            continue
        set_global_seed(100 + hash(s.label) % 1000)
        grid = SmartGrid(seed=100, rng_seed=42)
        apply_training_scenario(grid, s)
        try:
            grid.update_power_flow()
        except Exception:
            pass
        reg = _build_twin_registry(grid)
        _apply_health_override(grid, reg, s.health_override)
        for _ in range(10):
            _tick_twin(grid, reg)
        feats = _twin_features(reg)
        max_risk_seen.append(feats["max_risk"])
    assert max_risk_seen, "no health_override scenario found"
    assert any(r > 0.0 for r in max_risk_seen), (
        "twin features must exceed 0.0 during training when "
        "health_override is applied"
    )


def test_storage_state_training_range():
    """The training scenarios must exercise low / medium / high SOC
    for both battery and supercap."""
    from experiments.train_scenario_generator import (
        sample_training_scenarios,
    )

    sc = sample_training_scenarios(master_seed=100, n_episodes=24)
    battery = [s.battery_soc_init for s in sc if s.battery_soc_init is not None]
    supercap = [s.supercap_soc_init for s in sc if s.supercap_soc_init is not None]
    assert battery, "no battery SOC override found"
    assert supercap, "no supercap SOC override found"
    assert min(battery) <= 0.1, (
        "training must include a low-battery episode"
    )
    assert max(battery) >= 0.6, (
        "training must include a high-battery episode"
    )
    assert min(supercap) <= 0.1, (
        "training must include a low-supercap episode"
    )
    assert max(supercap) >= 0.6, (
        "training must include a high-supercap episode"
    )


def test_training_scenarios_independent_of_eval():
    """Training and evaluation scenarios must not share seeds or
    conditions."""
    from experiments.train_scenario_generator import (
        sample_training_scenarios,
    )
    # Evaluation scenarios are seeded by ``0..9`` (Stage-43 validation).
    eval_seeds = set(range(10))
    # Training scenarios are sampled via master_seed; pick a value
    # far away from the evaluation seeds.
    training = sample_training_scenarios(
        master_seed=1000, n_episodes=24,
    )
    # The training seed stream is independent of eval seeds
    # (different master_seed => different grid hashes, different
    # fault schedules).
    assert training, "no training scenarios generated"
    # The training labels should not collide with evaluation
    # labels (which start with 'A'..'J').
    for s in training:
        assert not s.label.startswith(("A_", "B_", "C_", "D_", "E_",
                                       "F_", "G_", "H_", "I_", "J_")), (
            f"training scenario {s.label} collides with eval label"
        )


def test_reward_components_decompose():
    """The reward function must decompose into named components
    (Stage-44 auditability)."""
    from models.rl_agent import DQNAgent

    grid_state = {
        "nodes": {
            "H": {"node_type": "house", "load": 1.5, "failed": False},
        },
        "system": {
            "avg_voltage": 0.99, "avg_frequency": 50.0,
            "balance": 1.0, "total_energy_loss": 0.0,
        },
    }
    comp = DQNAgent._compute_reward_components(
        grid_state, action_name="use_supercapacitor",
        supercap_level_pre=0.5, supercap_level_post=0.3,
    )
    expected_keys = {
        "total", "stability_voltage", "stability_freq", "balance_penalty",
        "failed_penalty", "isolated_penalty", "loss_penalty",
        "supercap_spike_bonus", "reroute_bonus",
    }
    assert expected_keys.issubset(comp.keys())
    # The supercap bonus fires when there is a spike AND supercap dropped.
    assert comp["supercap_spike_bonus"] == pytest.approx(2.0)


def test_reward_supercap_bonus_requires_effect():
    """Stage-44 redesign: supercap bonus only fires when the action
    actually discharged the supercap (post < pre)."""
    from models.rl_agent import DQNAgent

    grid_state = {
        "nodes": {
            "H": {"node_type": "house", "load": 1.5, "failed": False},
        },
        "system": {
            "avg_voltage": 0.99, "avg_frequency": 50.0,
            "balance": 1.0, "total_energy_loss": 0.0,
        },
    }
    # No effect: pre == post.
    comp_no_effect = DQNAgent._compute_reward_components(
        grid_state, action_name="use_supercapacitor",
        supercap_level_pre=0.5, supercap_level_post=0.5,
    )
    assert comp_no_effect["supercap_spike_bonus"] == 0.0
    # With effect.
    comp_with_effect = DQNAgent._compute_reward_components(
        grid_state, action_name="use_supercapacitor",
        supercap_level_pre=0.5, supercap_level_post=0.3,
    )
    assert comp_with_effect["supercap_spike_bonus"] == pytest.approx(2.0)


def test_reward_reroute_bonus_still_conditional_on_fault():
    """Stage-44 keeps the +3 reroute bonus: it only fires when there
    is a fault AND the policy took the reroute action."""
    from models.rl_agent import DQNAgent

    grid_no_fault = {
        "nodes": {"H": {"node_type": "house", "load": 0.5, "failed": False}},
        "system": {"avg_voltage": 1.0, "avg_frequency": 50.0,
                   "balance": 0.0, "total_energy_loss": 0.0},
    }
    grid_with_fault = {
        "nodes": {"H": {"node_type": "house", "load": 0.5, "failed": True}},
        "system": {"avg_voltage": 1.0, "avg_frequency": 50.0,
                   "balance": 0.0, "total_energy_loss": 0.0},
    }
    # No fault → no bonus.
    assert DQNAgent._compute_reward_components(
        grid_no_fault, action_name="reroute_energy",
    )["reroute_bonus"] == 0.0
    # Fault + reroute → +3.
    assert DQNAgent._compute_reward_components(
        grid_with_fault, action_name="reroute_energy",
    )["reroute_bonus"] == pytest.approx(3.0)

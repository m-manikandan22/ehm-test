"""test_dqn_eval_mode.py — EHM-CRIT-006: DQN train/eval separation."""
from __future__ import annotations

from models.rl_agent import DQNAgent


def test_default_state_is_training():
    a = DQNAgent()
    assert a.is_training is True


def test_eval_mode_disables_exploration():
    a = DQNAgent()
    a.eval_mode()
    state = [0.5] * 72
    result = a.select_action(state, predicted_load=0.5, grid_state=None)
    assert result["epsilon"] == 0.0


def test_eval_mode_does_not_advance_step_counter():
    a = DQNAgent()
    a.eval_mode()
    state = [0.5] * 72
    for _ in range(10):
        a.select_action(state, predicted_load=0.5, grid_state=None)
    assert a.steps_done == 0


def test_eval_mode_drops_experiences():
    a = DQNAgent()
    a.eval_mode()
    a.store_experience([0.0] * 72, 1, 1.0, [0.0] * 72, False)
    a.store_experience([0.0] * 72, 2, -0.5, [0.0] * 72, False)
    assert len(a.buffer) == 0
    assert a.dropped_experiences == 2


def test_eval_mode_sets_policies_to_eval():
    a = DQNAgent()
    a.eval_mode()
    assert a.policy_net.training is False
    assert a.target_net.training is False


def test_train_mode_resumes_learning():
    a = DQNAgent()
    a.eval_mode()
    a.store_experience([0.0] * 72, 1, 1.0, [0.0] * 72, False)
    a.train_mode()
    assert a.is_training is True
    a.store_experience([0.0] * 72, 1, 1.0, [0.0] * 72, False)
    assert len(a.buffer) == 1


def test_train_mode_advances_step_counter():
    a = DQNAgent()
    state = [0.5] * 72
    a.select_action(state, predicted_load=0.5, grid_state=None)
    assert a.steps_done == 1

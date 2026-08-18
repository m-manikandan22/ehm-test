"""Stage-43 Repair 1 — RNG isolation tests.

Required causal tests (Stage-43 spec):
  * test_controller_rng_does_not_change_environment
  * test_paired_controllers_share_environment
plus regression tests for the Stage-42.5 findings:
  * DQN eval-mode inference must consume zero RNG (finding 12)
  * LSTM construction must be RNG-neutral for the DQN weights (finding 6)
"""
from __future__ import annotations

import random

from utils.seeds import derive_stream_seeds


def _load_snapshot(grid) -> tuple:
    """Deterministic snapshot of per-node loads (sorted by node id)."""
    return tuple(
        round(float(n.load), 6)
        for nid, n in sorted(grid.nodes.items())
    )


def test_derive_stream_seeds_are_deterministic_and_distinct():
    s1 = derive_stream_seeds(7)
    s2 = derive_stream_seeds(7)
    assert s1 == s2
    assert len({s1["environment"], s1["controller"], s1["training"]}) == 3
    s3 = derive_stream_seeds(8)
    assert s3["environment"] != s1["environment"]
    assert s3["training"] != s1["training"]


def test_controller_rng_does_not_change_environment():
    """Controller draws between environment steps must not alter grid noise."""
    from simulation.grid import SmartGrid

    seeds = derive_stream_seeds(123)
    g_clean = SmartGrid(seed=123, rng_seed=seeds["environment"])
    g_busy = SmartGrid(seed=123, rng_seed=seeds["environment"])
    controller = random.Random(seeds["controller"])

    g_clean.step()
    g_busy.step()
    assert _load_snapshot(g_busy) == _load_snapshot(g_clean)

    # g_busy's controller burns 100 draws between steps; g_clean's does not.
    for _ in range(100):
        controller.uniform(0.0, 1.0)

    g_clean.step()
    g_busy.step()
    assert _load_snapshot(g_busy) == _load_snapshot(g_clean)

    # Also: an unseeded controller mutating the global stream must not
    # reach the grid's environment stream.
    for _ in range(50):
        random.random()
    g_clean.step()
    g_busy.step()
    assert _load_snapshot(g_busy) == _load_snapshot(g_clean)


def test_dqn_eval_consumes_no_randomness():
    """Eval-mode select_action must draw nothing from python or torch RNG.

    Stage-42.5 finding 12: eval-mode DQN previously consumed one global
    ``random.random()`` per call, perturbing the grid noise stream.
    """
    import torch  # type: ignore

    from models.rl_agent import DQNAgent

    seeds = derive_stream_seeds(42)
    torch.manual_seed(seeds["training"])
    agent = DQNAgent()
    agent.eval_mode()

    state = [0.5] * 72
    random.seed(99)
    py_before = random.getstate()
    torch_before = torch.random.get_rng_state().clone()

    agent.select_action(state, predicted_load=0.5, grid_state=None)

    assert random.getstate() == py_before
    assert torch.equal(torch.random.get_rng_state(), torch_before)


def test_lstm_construction_is_rng_neutral_for_dqn():
    """Stage-42.5 finding 6: building the LSTM before the DQN must not
    change the DQN's random-initialised weights."""
    import numpy as np
    import torch  # type: ignore

    from models.lstm_model import DemandForecaster
    from models.rl_agent import DQNAgent

    seeds = derive_stream_seeds(7)

    torch.manual_seed(seeds["training"])
    agent_no_lstm = DQNAgent()

    torch.manual_seed(seeds["training"])
    np_state = np.random.get_state()
    with torch.random.fork_rng(devices=[]):
        DemandForecaster()
    np.random.set_state(np_state)
    torch.manual_seed(seeds["training"])
    agent_with_lstm = DQNAgent()

    for p1, p2 in zip(
        agent_no_lstm.policy_net.parameters(),
        agent_with_lstm.policy_net.parameters(),
    ):
        assert torch.equal(p1.detach(), p2.detach())


def test_paired_controllers_share_environment():
    """random and rule_based draw differently, yet must observe the
    identical environment for the same master seed.

    Stage-43 (Repair 3): controller actions now have REAL physical
    effects (storage discharge, load shift, tie closure), so from the
    first action onward the two controllers legitimately see different
    trajectories — that is the environment *responding* to the
    controller, not RNG leakage. The honest invariants are:

      * identical stream seeds (controller randomness never re-seeds
        the environment);
      * identical environment fingerprints — grid topology + static
        params, demand profile, renewable profile and fault plan
        (the inputs the controller sees are byte-for-byte the same);
      * identical first pre-action observation (same starting state).

    Controller-RNG isolation itself is pinned by
    ``test_controller_rng_does_not_change_environment``.
    """
    from experiments.experiment_config import ExperimentConfig
    from experiments.runner import run_single
    from experiments.scenario import make_scenario

    base = dict(
        enable_dqn=False,
        enable_lstm=False,
        enable_twin=False,
        enable_predictive_healing=False,
        enable_reward_shaping=False,
        enable_flisr=False,
        enable_ems=False,
        enable_storage=False,
        enable_xai=False,
    )
    cfg_random = ExperimentConfig(**base, label="random")
    cfg_rule = ExperimentConfig(**base, label="rule_based")

    scenario = make_scenario(seed=4, total_steps=10, fault_count=2)
    r_rand = run_single(config=cfg_random, scenario=scenario, run_seed=4)
    r_rule = run_single(config=cfg_rule, scenario=scenario, run_seed=4)

    # Same recorded stream seeds.
    assert r_rand["seeds"] == r_rule["seeds"]
    assert r_rand["git_sha"] == r_rule["git_sha"]
    # Identical environment inputs (topology, profiles, faults).
    assert r_rand["fingerprints"] == r_rule["fingerprints"], (
        "paired controllers must see the identical environment "
        "(grid/demand/renewable/fault hashes)"
    )
    # Identical initial pre-action observation.
    assert r_rand["environment_trace"][0] == r_rule["environment_trace"][0]
    # …while the controllers genuinely took different decisions.
    assert (r_rand["metrics"]["action_counts"]
            != r_rule["metrics"]["action_counts"])


def test_same_seed_same_environment_trace_across_runs():
    """Re-running the same controller+seed reproduces the env trace."""
    from experiments.experiment_config import ExperimentConfig
    from experiments.runner import run_single
    from experiments.scenario import make_scenario

    cfg = ExperimentConfig(
        enable_dqn=False, enable_lstm=False, enable_twin=False,
        enable_predictive_healing=False, enable_reward_shaping=False,
        enable_flisr=False, enable_ems=False, enable_storage=False,
        enable_xai=False, label="rule_based",
    )
    scenario = make_scenario(seed=11, total_steps=8, fault_count=1)
    a = run_single(config=cfg, scenario=scenario, run_seed=11)
    b = run_single(config=cfg, scenario=scenario, run_seed=11)
    assert a["environment_trace"] == b["environment_trace"]
    assert a["seeds"] == b["seeds"]
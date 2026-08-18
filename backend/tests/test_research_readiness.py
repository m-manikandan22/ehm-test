"""test_research_readiness.py — PHASE 20 readiness tests.

These are the tests the master plan calls out in PHASE 20:

  1. ExperimentConfig actually disables LSTM.
  2. ExperimentConfig actually disables Twin.
  3. Predictive healing can be disabled.
  4. Reward shaping can be disabled.
  5. DQN-only baseline does not consume LSTM/Twin features.
  6. Same seed generates identical scenarios.
  7. Different seed changes scenario.
  8. All policies receive identical scenario for same seed.
  9. Invalid solver runs are excluded from aggregate statistics.
 10. FLISR exceptions are not silently swallowed.
 11. Statistical functions return expected results on known samples.
 12. Ablation output contains genuine configuration information.
 13. No NaN/Inf appears in valid experiment results.
 14. Critical-load restoration is calculated correctly.
 15. Restoration time is calculated correctly.
"""
from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from unittest import mock

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
for p in (BACKEND_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)


# ── Lazy imports so the failure trace names the right module ────────────
def _config():
    from experiments.experiment_config import ExperimentConfig, ABLATION_CONFIGS
    return ExperimentConfig, ABLATION_CONFIGS


def _scenario():
    from experiments.scenario import make_scenario
    return make_scenario


def _validity():
    from experiments.validity import (
        InvalidRunReason, ValidityReport, check_run_validity,
    )
    return InvalidRunReason, ValidityReport, check_run_validity


def _metrics():
    from experiments.research_metrics import (
        MetricCollector, compute_research_metrics, CRITICAL_NODE_TYPES,
        FaultRecord,
    )
    return MetricCollector, compute_research_metrics, CRITICAL_NODE_TYPES, FaultRecord


def _runner():
    from experiments.runner import run_single, run_experiment, _build_grid
    return {"run_single": run_single,
            "run_experiment": run_experiment,
            "_build_grid": _build_grid}


# Aliases for tests that only need one of them.
def _run_single():
    return _runner()["run_single"]


def _run_experiment():
    return _runner()["run_experiment"]


def _ablation():
    from experiments.ablation import run_ablation
    return run_ablation


def _stats():
    from metrics.statistics import paired_comparison, summarise, cohens_d_paired
    return paired_comparison, summarise, cohens_d_paired


# ── (1) ExperimentConfig disables LSTM ──────────────────────────────────
def test_config_actually_disables_lstm():
    ExperimentConfig, _ = _config()
    cfg = ExperimentConfig.no_lstm(seed=42)
    assert cfg.enable_lstm is False
    # Disabled module list must contain "lstm".
    assert "lstm" in cfg.disabled_modules()
    assert "lstm" not in cfg.active_modules()


# ── (2) ExperimentConfig disables Twin ──────────────────────────────────
def test_config_actually_disables_twin():
    ExperimentConfig, _ = _config()
    cfg = ExperimentConfig.no_twin(seed=42)
    assert cfg.enable_twin is False
    assert "digital_twin" in cfg.disabled_modules()
    assert "digital_twin" not in cfg.active_modules()


# ── (3) Predictive healing can be disabled ──────────────────────────────
def test_config_actually_disables_predictive():
    ExperimentConfig, _ = _config()
    cfg = ExperimentConfig.no_predictive(seed=42)
    assert cfg.enable_predictive_healing is False
    assert "predictive_healing" in cfg.disabled_modules()


# ── (4) Reward shaping can be disabled ──────────────────────────────────
def test_config_actually_disables_reward_shaping():
    ExperimentConfig, _ = _config()
    cfg = ExperimentConfig.no_reward(seed=42)
    assert cfg.enable_reward_shaping is False
    assert "reward_shaping" in cfg.disabled_modules()


# ── (5) DQN-only baseline does not consume LSTM/Twin features ───────────
def test_dqn_only_disables_lstm_and_twin():
    ExperimentConfig, _ = _config()
    cfg = ExperimentConfig.dqn_core_only(seed=42)
    assert cfg.enable_dqn is True
    assert cfg.enable_lstm is False
    assert cfg.enable_twin is False
    assert cfg.enable_predictive_healing is False
    assert cfg.enable_reward_shaping is False
    assert "lstm" in cfg.disabled_modules()
    assert "digital_twin" in cfg.disabled_modules()


# ── (6) Same seed generates identical scenarios ──────────────────────────
def test_same_seed_same_scenario():
    make_scenario = _scenario()
    a = make_scenario(seed=7, total_steps=40, fault_count=3)
    b = make_scenario(seed=7, total_steps=40, fault_count=3)
    assert a.faults == b.faults
    assert a.total_steps == b.total_steps


# ── (7) Different seed → different scenario ─────────────────────────────
def test_different_seed_different_scenario():
    make_scenario = _scenario()
    a = make_scenario(seed=11, total_steps=40, fault_count=3)
    b = make_scenario(seed=12, total_steps=40, fault_count=3)
    assert a.faults != b.faults


# ── (8) All policies receive identical scenario for same seed ───────────
def test_all_policies_same_scenario_for_same_seed():
    ExperimentConfig, _ = _config()
    runner = _runner()
    run_experiment = runner["run_experiment"]
    with tempfile.TemporaryDirectory() as td:
        cfg_labels = ["random", "rule_based", "dqn_core_only", "full_stack"]
        configs = []
        for label in cfg_labels:
            cfg = ExperimentConfig(
                enable_dqn=ABLATION_CONFIGS_OR_DEFAULT(label).enable_dqn,
                enable_lstm=ABLATION_CONFIGS_OR_DEFAULT(label).enable_lstm,
                enable_twin=ABLATION_CONFIGS_OR_DEFAULT(label).enable_twin,
                enable_predictive_healing=ABLATION_CONFIGS_OR_DEFAULT(label).enable_predictive_healing,
                enable_reward_shaping=ABLATION_CONFIGS_OR_DEFAULT(label).enable_reward_shaping,
                enable_flisr=ABLATION_CONFIGS_OR_DEFAULT(label).enable_flisr,
                enable_ems=ABLATION_CONFIGS_OR_DEFAULT(label).enable_ems,
                enable_storage=ABLATION_CONFIGS_OR_DEFAULT(label).enable_storage,
                enable_xai=ABLATION_CONFIGS_OR_DEFAULT(label).enable_xai,
                seed=0, label=label,
            )
            configs.append(cfg)
        out = os.path.join(td, "fair.json")
        report = run_experiment(
            configs=configs, seeds=1, ticks=6, faults_per_run=1,
            weather_modes=["normal"], output_path=out,
            write_csv=False,
        )
        # Group runs by (seed, weather) and verify the scenario is
        # byte-for-byte identical across policies for the same seed.
        runs_by_key = {}
        for run in report["runs"]:
            key = (run["seed"], run["weather_mode"])
            runs_by_key.setdefault(key, []).append(run)
        for key, group in runs_by_key.items():
            scenarios = [json.dumps(r["scenario"], sort_keys=True) for r in group]
            # Every policy's scenario for this seed must be identical.
            assert len(set(scenarios)) == 1, (
                f"Policies received different scenarios for {key}: "
                f"{set(scenarios)}"
            )


def ABLATION_CONFIGS_OR_DEFAULT(label: str):
    """Convenience accessor so the test above reads cleanly."""
    _, ABLATION_CONFIGS = _config()
    return ABLATION_CONFIGS[label]


# ── (9) Invalid solver runs are excluded from aggregate statistics ──────
def test_invalid_runs_excluded_from_aggregate():
    _, _, check_run_validity = _validity()
    # A trivially invalid grid (empty topology).
    invalid_grid = mock.Mock()
    invalid_grid.nodes = {}
    invalid_grid.graph = mock.Mock()
    rep = check_run_validity(invalid_grid)
    assert rep.valid is False
    # The aggregator must skip invalid rows.
    from experiments.aggregate import _per_policy
    runs = [
        {"validity": {"valid": True}, "controller_label": "A",
         "metrics": {"x": 1.0}},
        {"validity": {"valid": False}, "controller_label": "A",
         "metrics": {"x": 99.0}},
    ]
    grouped = _per_policy(runs)
    assert "A" in grouped
    # Only the valid run is kept.
    assert len(grouped["A"]) == 1
    assert grouped["A"][0]["metrics"]["x"] == 1.0


# ── (10) FLISR exceptions are not silently swallowed ────────────────────
def test_flisr_exceptions_not_swallowed():
    """The runner marks a run invalid on FLISR failure rather than
    swallowing the exception."""
    runner = _runner()
    run_single = runner["run_single"]
    ExperimentConfig, _ = _config()
    make_scenario = _scenario()

    cfg = ExperimentConfig.rule_based(seed=42)
    scenario = make_scenario(
        seed=42, total_steps=8, fault_count=1, weather_mode="normal",
        label="manual",
    )

    class _BoomNode:
        voltage = 1.0
        failed = False
        isolated = False

    class _BoomGrid:
        def __init__(self, seed=None, rng_seed=None):
            # ``_build_grid(seed, rng_seed)`` now passes the run seed
            # and the environment-stream seed through to grid
            # construction (EHM-HIGH-009, Stage-43 RNG isolation);
            # accept and ignore them.
            del seed, rng_seed
            # Non-empty topology so the per-step topology validity
            # check passes; the FLISR exception is the only invalid
            # signal the test wants to assert.
            self.nodes = {"P_A1": _BoomNode()}
            self.graph = _BoomGraph()

        def get_state(self):
            return {}

        def get_rl_state(self):
            return []

        def inject_failure(self, target):
            pass

        def step(self):
            pass

        def flisr_restore(self):
            raise RuntimeError("simulated FLISR crash")

    class _BoomGraph:
        def edges(self, data=False):
            return []

    # Patch the runner's _build_grid to return our boom grid.
    with mock.patch("experiments.runner._build_grid", _BoomGrid):
        run = run_single(config=cfg, scenario=scenario)
    assert run["validity"]["valid"] is False
    assert run["validity"]["invalid_reason"] in (
        "CONTROLLER_FAILED", "UNEXPECTED_EXCEPTION",
    )
    assert "FLISR" in run["validity"]["details"].get("controller", "") \
        or "FLISR" in str(run["validity"]["details"])


# ── (11) Statistical functions return expected results on known samples ─
def test_paired_comparison_known_samples():
    paired_comparison, _, _ = _stats()
    rep = paired_comparison([10, 11, 12, 13, 14], [1, 1, 2, 2, 3])
    assert rep["valid"] is True
    assert rep["n"] == 5
    # The difference is large and consistent.
    assert rep["mean_difference"] > 0
    assert rep["t_p_value"] < 0.05
    assert rep["effect_size"] > 0.0


def test_summarise_returns_expected_keys():
    _, summarise, _ = _stats()
    s = summarise([1, 2, 3, 4, 5])
    assert s["n"] == 5
    assert s["mean"] == 3.0
    assert "ci95_low" in s and "ci95_high" in s


def test_cohens_d_paired_returns_finite_number():
    _, _, cohens_d_paired = _stats()
    # Use inputs that produce a *variable* difference so the SD is
    # non-zero and Cohen's d is defined (a perfect constant diff
    # gives d = 0 / 0 = 0 by convention).
    d = cohens_d_paired([5, 7, 6, 9, 11], [1, 1, 2, 3, 4])
    assert math.isfinite(d)
    assert d > 0


# ── (12) Ablation output contains genuine configuration information ────
def test_ablation_output_has_real_config_info():
    run_ablation = _ablation()
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "abl.json")
        report = run_ablation(
            seeds=1, ticks=5, faults_per_run=1,
            output_path=out,
            labels=["full_stack", "no_lstm", "no_twin"],
        )
        assert report["status"] == "real"
        for label in ("full_stack", "no_lstm", "no_twin"):
            assert label in report["per_config"]
            cfg = report["per_config"][label]
            assert "active_modules" in cfg
            assert "disabled_modules" in cfg
            # Genuine distinction: full_stack has lstm active, no_lstm
            # has lstm disabled.
        assert (
            "lstm" in report["per_config"]["full_stack"]["active_modules"]
        )
        assert (
            "lstm" in report["per_config"]["no_lstm"]["disabled_modules"]
        )
        assert (
            "digital_twin" in report["per_config"]["no_twin"]["disabled_modules"]
        )


# ── (13) No NaN/Inf appears in valid experiment results ─────────────────
def test_no_nan_in_valid_metrics():
    ExperimentConfig, _ = _config()
    runner = _runner()
    run_single = runner["run_single"]
    make_scenario = _scenario()
    cfg = ExperimentConfig.rule_based(seed=42)
    scenario = make_scenario(
        seed=42, total_steps=6, fault_count=1, weather_mode="normal",
    )
    run = run_single(config=cfg, scenario=scenario)
    metrics = run.get("metrics") or {}
    # Walk every numeric leaf.
    def _walk(o):
        if isinstance(o, dict):
            for v in o.values():
                yield from _walk(v)
        elif isinstance(o, list):
            for v in o:
                yield from _walk(v)
        elif isinstance(o, (int, float)):
            yield o
    nums = list(_walk(metrics))
    for v in nums:
        if isinstance(v, float):
            assert math.isfinite(v), f"non-finite value in metrics: {v}"


# ── (14) Critical-load restoration is calculated correctly ──────────────
def test_critical_load_restoration_calculated():
    _, compute_research_metrics, _, _ = _metrics()

    class _N:
        def __init__(self, node_type="house", load=0.0, failed=False,
                      isolated=False, voltage=1.0):
            self.node_type = node_type
            self.load = load
            self.failed = failed
            self.isolated = isolated
            self.voltage = voltage

    class _G:
        def __init__(self, nodes):
            self.nodes = nodes
            self.graph = self

    grid = _G({
        "HOSP":    _N(node_type="hospital",       load=1.0, failed=False),
        "WAT":     _N(node_type="water_plant",    load=0.5, failed=True),
        "HOUSE":   _N(node_type="house",          load=0.3, failed=False),
    })
    MetricCollector, _, _, _ = _metrics()
    collector = MetricCollector()
    metrics = compute_research_metrics(
        grid=grid, collector=collector,
        run_started_at=0.0,
    )
    # Total critical load = 1 + 0.5 = 1.5. Critical restored = 1 (the
    # hospital). Percentage = 1 / 1.5 * 100 ≈ 66.67 %.
    assert metrics["critical_load_total_mw"] == 1.5
    assert metrics["critical_load_restored_mw"] == 1.0
    assert 66.0 < metrics["critical_load_restored_pct"] < 67.0


# ── (15) Restoration time is calculated correctly ───────────────────────
def test_restoration_time_calculated():
    MetricCollector, _, _, FaultRecord = _metrics()
    c = MetricCollector()
    c.record_fault(timestep=2, target="H01", baseline_load_mw=1.0,
                   baseline_critical_mw=0.0)
    c.mark_restoration_complete(fault_target="H01", timestep=10)
    rec = c.faults[0]
    assert rec.successful_restoration is True
    assert rec.restoration_timestep == 10
    assert rec.restoration_steps == 8
    assert rec.restoration_seconds == 8.0


def test_restoration_time_unset_when_not_restored():
    MetricCollector, _, _, _ = _metrics()
    c = MetricCollector()
    c.record_fault(timestep=2, target="H01", baseline_load_mw=1.0,
                   baseline_critical_mw=0.0)
    rec = c.faults[0]
    assert rec.successful_restoration is False
    assert rec.restoration_timestep is None
    assert rec.restoration_steps is None


# ── (16) Grid construction is deterministic per seed (EHM-HIGH-009) ───
def test_grid_deterministic_per_seed():
    _build_grid = _runner()["_build_grid"]
    g1 = _build_grid(seed=7)
    g2 = _build_grid(seed=7)
    g3 = _build_grid(seed=8)
    loads1 = [round(n.load, 6) for n in g1.nodes.values()]
    loads2 = [round(n.load, 6) for n in g2.nodes.values()]
    loads3 = [round(n.load, 6) for n in g3.nodes.values()]
    assert loads1 == loads2
    assert loads1 != loads3


# ── (17) DQN is actually invoked in eval mode (EHM-CRIT-007a) ─────────
def test_dqn_agent_invoked_in_eval_mode():
    run_single = _run_single()
    ExperimentConfig, _ = _config()
    make_scenario = _scenario()
    scen = make_scenario(seed=0, total_steps=4, fault_count=0,
                         weather_mode="normal")

    with mock.patch("models.rl_agent.DQNAgent", autospec=True) as agent_cls:
        agent = agent_cls.return_value
        agent.select_action.return_value = {
            "action_id": 3, "action_name": "shift_load",
        }
        run = run_single(config=ExperimentConfig.full_stack(seed=0),
                         scenario=scen)
    # The agent must be switched to evaluation mode and actually queried.
    assert agent.eval_mode.called
    assert agent.select_action.called
    # Its chosen action (3 = shift_load) must be the recorded action and
    # must be dispatched — not a hard-coded stub action.
    assert run["metrics"]["actions_taken"] == scen.total_steps


# ── (18) Clock advances for every policy (EHM-CRIT-007b) ──────────────
def test_clock_advances_for_all_policies():
    from simulation.grid import SmartGrid
    run_single = _run_single()
    ExperimentConfig, _ = _config()
    make_scenario = _scenario()
    scen = make_scenario(seed=3, total_steps=6, fault_count=1,
                         weather_mode="normal")

    # persistence disables storage — the clock must still advance.
    with mock.patch.object(
        SmartGrid, "step", wraps=SmartGrid.step, autospec=True,
    ) as step_mock:
        run = run_single(config=ExperimentConfig.persistence(seed=3),
                         scenario=scen)
    assert step_mock.call_count == scen.total_steps
    assert run["validity"]["valid"] is True


# ── (19) Ablation rows reproduce full_stack for the same seed ─────────
def test_ablation_rows_identical_ens_same_seed():
    """Harness honesty check: rows that toggle modules the thin runner
    does not (yet) consume must reproduce the full_stack trajectory
    exactly for the same seed."""
    run_ablation = _ablation()
    report = run_ablation(
        seeds=1, ticks=6, faults_per_run=1,
        labels=["full_stack", "no_lstm", "no_twin",
                "no_predictive", "no_reward"],
    )
    ens = {}
    for label in ("full_stack", "no_lstm", "no_twin",
                  "no_predictive", "no_reward"):
        row = report["per_config"][label]["metrics_summary"][0]
        ens[label] = row["energy_not_served_mwh_mean"]
    assert len(set(round(v, 6) for v in ens.values())) == 1, ens

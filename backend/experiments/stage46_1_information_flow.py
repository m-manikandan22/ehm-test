"""stage46_1_information_flow.py — Stage 46.1 single-state information-flow
experiment.

For a set of deterministic (scenario, seed, timestep) states, evaluate the
FROZEN Stage-44 DQN checkpoint under each ablation configuration and record,
for every feature group:

  * the exact 78-dim extended state vector,
  * per-feature ablation differences,
  * the raw Q-values (all 5 heads),
  * the masked-argmax action,
  * the immediate physical outcome (served MWh / ENS shortfall / voltage
    violations) after dispatching the selected action from the same
    pre-action state.

Configurations compared on the SAME environment state:
  full_stack        — all channels enabled
  no_lstm           — enable_lstm=False (forecast feature = 0.5 sentinel)
  no_twin           — enable_twin=False (twin features zeroed)
  no_ems            — enable_ems=False  (EMS not run; DQN state unchanged)
  no_predictive     — enable_predictive=False (healer not run; DQN state unchanged)

The checkpoint is NEVER modified. Its SHA-256 is recorded before and after.

Run from ``backend/``::

  python -m experiments.stage46_1_information_flow \
      --out experiments/results/stage46_1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
BACKEND = PROJECT_ROOT / "backend"
for p in (str(PROJECT_ROOT), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)
THIS_DIR = BACKEND / "experiments"
for p in (str(THIS_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402
import torch  # noqa: E402

from utils.seeds import set_global_seed  # noqa: E402
from simulation.grid import SmartGrid  # noqa: E402
from models.rl_agent import (  # noqa: E402
    DQNAgent, build_extended_state, EXTENDED_STATE_DIM,
)
from experiments.stage44_validation import (  # noqa: E402
    _build_scenario_for_seed, _apply_scenario_to_grid,
    _Stage44DQNAdapter, _get_shared_forecaster,
)
from experiments.scenario_matrix import get_scenario_spec  # noqa: E402
from experiments.info_flow import (  # noqa: E402
    _aggregate_grid_load_and_gen, _pre_age_twins,
)

CKPT = BACKEND / "experiments" / "checkpoints" / "dqn_stage44.pt"
WEATHER_MAP = {"normal": 0.2, "storm": 0.85, "heatwave": 0.5}

FEATURE_BLOCKS = {
    "lstm": [72],
    "storage": [73, 74],
    "twin": [75, 76, 77],
}


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ----------------------------------------------------------------------
# Deterministic state builder (mirrors the Stage-44/45 harness loop)
# ----------------------------------------------------------------------

class _StateCtx:
    """Holds the environment forward state for a (scenario, seed, step)."""

    def __init__(self, scenario_label: str, seed: int, step: int):
        scenario = _build_scenario_for_seed(scenario_label, seed)
        self.scenario = scenario
        self.seed = int(seed)
        self.step = int(step)
        set_global_seed(seed)
        grid = SmartGrid(seed=seed)
        _apply_scenario_to_grid(grid, scenario)
        try:
            grid.update_power_flow()
        except Exception:
            pass
        for t in range(step):
            for fault in scenario.faults:
                if fault.timestep == t:
                    try:
                        grid.inject_failure(fault.target)
                    except Exception:
                        pass
            try:
                grid.step()
            except Exception:
                pass
            try:
                grid.update_power_flow()
            except Exception:
                pass
        self.grid = grid
        # LSTM history identical to the harness (past only).
        self.lstm_history = deque(maxlen=10)
        self.weather_proxy = WEATHER_MAP.get(
            str(getattr(scenario, "weather_mode", "normal")), 0.2
        )
        # Twin registry gated exactly like the harness.
        self.twin = None

    def enable_twin_build(self, enable_twin: bool) -> None:
        if not enable_twin:
            self.twin = None
            return
        from digital_twin.twin_registry import TwinRegistry
        twin = TwinRegistry()
        twin.register(self.grid)
        spec = get_scenario_spec(self.scenario.label.split("|")[0])
        if spec is not None and spec.health_override:
            try:
                _pre_age_twins(twin, dict(spec.health_override))
            except Exception:
                pass
        self.twin = twin

    def advance_history(self) -> None:
        try:
            _l, _g = _aggregate_grid_load_and_gen(self.grid)
            self.lstm_history.append((_l, _g, self.weather_proxy))
        except Exception:
            pass

    def twin_features(self) -> Tuple[float, float, float]:
        if self.twin is None:
            return 0.0, 0.0, 0.0
        vals = []
        for tw in self.twin.all():
            try:
                v = float(getattr(tw, "health_risk_score", 0.0) or 0.0)
                vals.append(v)
            except Exception:
                continue
        if not vals:
            return 0.0, 0.0, 0.0
        return (
            float(max(vals)),
            float(sum(vals) / len(vals)),
            float(sum(1 for v in vals if v >= 0.5) / len(vals)),
        )

    def storage_soc(self) -> Tuple[float, float]:
        battery = 0.0
        supercap = 0.0
        for n in self.grid.nodes.values():
            if str(getattr(n, "node_type", "")) == "house":
                battery = max(battery, float(getattr(n, "battery_level", 0.0) or 0.0))
                supercap = max(supercap, float(getattr(n, "supercap_level", 0.0) or 0.0))
        return battery, supercap


def _q_and_argmax(agent, state, grid_state):
    with torch.no_grad():
        q = agent.policy_net(
            torch.tensor(np.array(state, dtype=np.float32)).unsqueeze(0)
        )[0].numpy()
    valid = agent._valid_actions_mask(grid_state) or [0, 1, 2, 3, 4]
    masked = np.full(5, -np.inf)
    for a in valid:
        masked[a] = q[a]
    argmax = int(masked.argmax())
    return [float(v) for v in q], argmax, valid


def _physical_outcome(grid, action_id):
    """Dispatch ``action_id`` from the given grid and measure immediate
    physical consequences (Stage-45 metric surface)."""
    served_before = sum(
        float(getattr(n, "received_power", 0.0) or 0.0)
        for n in grid.nodes.values()
    ) / 60.0
    if 0 <= action_id <= 4:
        try:
            from experiments.runner import _dispatch_action
            _dispatch_action(grid, action_id)
        except Exception:
            pass
    try:
        grid.step()
    except Exception:
        pass
    try:
        grid.update_power_flow()
    except Exception:
        pass
    served_after = sum(
        float(getattr(n, "received_power", 0.0) or 0.0)
        for n in grid.nodes.values()
    ) / 60.0
    # ENS shortfall this step (consumer baseline - served), MWh.
    short = 0.0
    crit_int = 0
    vviol = 0
    for n in grid.nodes.values():
        nt = str(getattr(n, "node_type", ""))
        if nt not in ("house", "industry", "hospital", "hospital_icu"):
            continue
        received = float(getattr(n, "received_power", 0.0) or 0.0)
        base = float(getattr(n, "_base_load", 0.0) or 0.0)
        short += max(0.0, base - received) / 60.0
        if nt in ("hospital", "hospital_icu") and received <= 0:
            crit_int += 1
    for n in grid.nodes.values():
        if abs(float(getattr(n, "voltage", 1.0) or 1.0) - 1.0) > 0.10:
            vviol += 1
    return {
        "served_mwh_delta": float(served_after - served_before),
        "ens_shortfall_mwh": float(short),
        "critical_interrupted_nodes": int(crit_int),
        "voltage_violation_nodes": int(vviol),
    }


# ----------------------------------------------------------------------
# Experiment
# ----------------------------------------------------------------------

CONFIGS = [
    ("full_stack", dict(enable_lstm=True, enable_twin=True,
                        enable_predictive=True, enable_ems=True)),
    ("no_lstm", dict(enable_lstm=False, enable_twin=True,
                     enable_predictive=True, enable_ems=True)),
    ("no_twin", dict(enable_lstm=True, enable_twin=False,
                     enable_predictive=True, enable_ems=True)),
    ("no_ems", dict(enable_lstm=True, enable_twin=True,
                    enable_predictive=True, enable_ems=False)),
    ("no_predictive", dict(enable_lstm=True, enable_twin=True,
                           enable_predictive=False, enable_ems=True)),
]

# Deterministic probe states: (scenario, seed, step)
PROBE_STATES = [
    ("A", 0, 10),
    ("A", 0, 30),
    ("A", 0, 60),
    ("E", 0, 10),
    ("E", 0, 40),
    ("I", 0, 10),
    ("I", 0, 40),
    ("J", 0, 10),
    ("H", 0, 10),   # twin health_override -> nonzero twin feature
]


def norm(v: List[float]) -> float:
    return float(np.linalg.norm(np.asarray(v, dtype=float)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", default=str(CKPT))
    ap.add_argument("--out", default=str(BACKEND / "experiments" / "results" / "stage46_1"))
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    ckpt = Path(args.checkpoint)
    hash_before = sha256(ckpt)

    agent = DQNAgent.load_checkpoint(str(ckpt), state_dim=EXTENDED_STATE_DIM,
                                     eval_mode=True)
    fc = _get_shared_forecaster()

    state_comparison = []
    q_value_comparison = []
    action_comparison = []
    sensitivity_rows = []

    for scen, seed, step in PROBE_STATES:
        ctx = _StateCtx(scen, seed, step)
        ctx.enable_twin_build(True)
        ctx.advance_history()

        # Per-config states built on the SAME environment snapshot.
        config_states = {}
        config_q = {}
        config_action = {}

        base_rl = ctx.grid.get_rl_state()
        grid_state = ctx.grid.get_state()
        twin_max, twin_mean, twin_frac = ctx.twin_features()
        bat_soc, sc_soc = ctx.storage_soc()

        # Reuse one adapter per config set; install the real per-run history.
        adapter = _Stage44DQNAdapter(agent, enable_lstm=True, enable_twin=True)
        adapter.set_lstm_history(ctx.lstm_history)

        for label, cfg in CONFIGS:
            if cfg["enable_lstm"]:
                forecast = adapter._predicted_load()
            else:
                forecast = 0.5

            state = build_extended_state(
                base_rl,
                predicted_load=forecast,
                battery_soc=bat_soc,
                supercap_soc=sc_soc,
                twin_max_risk=twin_max if cfg["enable_twin"] else 0.0,
                twin_mean_risk=twin_mean if cfg["enable_twin"] else 0.0,
                twin_high_frac=twin_frac if cfg["enable_twin"] else 0.0,
            )
            config_states[label] = [float(x) for x in state]
            q, argmax, valid = _q_and_argmax(agent, state, grid_state)
            config_q[label] = q
            config_action[label] = {"argmax": argmax, "valid": valid}

        # Full-state reference for the physical comparison.
        full_action = config_action["full_stack"]["argmax"]

        # Physical outcomes measured from IDENTICAL pre-action snapshots.
        phys = {}
        for label in ("full_stack", "no_lstm", "no_twin", "no_ems", "no_predictive"):
            act = config_action[label]["argmax"]
            g = ctx.grid
            # copy the grid for each dispatch so the pre-action state is
            # byte-identical across configs.
            import copy as _copy
            g2 = _copy.deepcopy(g)
            phys[label] = _physical_outcome(g2, act)

        # ---- state comparison record ----
        full_state = config_states["full_stack"]
        for label in ("no_lstm", "no_twin", "no_ems", "no_predictive"):
            a_state = config_states[label]
            diffs = {
                str(i): {
                    "full": full_state[i],
                    "ablated": a_state[i],
                    "diff": a_state[i] - full_state[i],
                }
                for i in range(len(full_state))
                if abs(a_state[i] - full_state[i]) > 1e-12
            }
            state_comparison.append({
                "scenario": scen, "seed": seed, "step": step,
                "ablation": label,
                "state_dim_full": len(full_state),
                "state_dim_ablated": len(a_state),
                "n_features_differ": len(diffs),
                "feature_differences": diffs,
                "delta_state_norm": norm([a_state[i] - full_state[i]
                                          for i in range(len(full_state))]),
            })

        # ---- q-value comparison record ----
        q_full = config_q["full_stack"]
        for label in ("no_lstm", "no_twin", "no_ems", "no_predictive"):
            q_a = config_q[label]
            q_value_comparison.append({
                "scenario": scen, "seed": seed, "step": step,
                "ablation": label,
                "Q_full": q_full,
                "Q_ablated": q_a,
                "dQ": [q_a[i] - q_full[i] for i in range(5)],
                "dQ_norm": norm([q_a[i] - q_full[i] for i in range(5)]),
                "argmax_full": config_action["full_stack"]["argmax"],
                "argmax_ablated": config_action[label]["argmax"],
                "action_changed": (
                    config_action["full_stack"]["argmax"]
                    != config_action[label]["argmax"]
                ),
            })

        # ---- action comparison record ----
        for label in ("no_lstm", "no_twin", "no_ems", "no_predictive"):
            action_comparison.append({
                "scenario": scen, "seed": seed, "step": step,
                "ablation": label,
                "argmax_full": config_action["full_stack"]["argmax"],
                "argmax_ablated": config_action[label]["argmax"],
                "valid_full": config_action["full_stack"]["valid"],
                "valid_ablated": config_action[label]["valid"],
                "action_changed": (
                    config_action["full_stack"]["argmax"]
                    != config_action[label]["argmax"]
                ),
                "physical": {
                    "full_stack": phys["full_stack"],
                    label: phys[label],
                    "physical_changed": (
                        phys["full_stack"]["ens_shortfall_mwh"]
                        != phys[label]["ens_shortfall_mwh"]
                        or phys["full_stack"]["served_mwh_delta"]
                        != phys[label]["served_mwh_delta"]
                        or phys["full_stack"]["voltage_violation_nodes"]
                        != phys[label]["voltage_violation_nodes"]
                        or phys["full_stack"]["critical_interrupted_nodes"]
                        != phys[label]["critical_interrupted_nodes"]
                    ),
                },
            })

        # ---- sensitivity matrix row ----
        q_arr_full = np.array(q_full)
        for block, indices in FEATURE_BLOCKS.items():
            d_state = np.array([
                config_states[label][i] - full_state[i]
                for label in ("no_lstm", "no_twin", "no_ems", "no_predictive")
                for i in indices
            ])
            # per-block state delta norm (max across configs of that block)
            block_delta = 0.0
            for label in ("no_lstm", "no_twin", "no_ems", "no_predictive"):
                v = np.array([
                    config_states[label][i] - full_state[i] for i in indices
                ])
                block_delta = max(block_delta, float(np.linalg.norm(v)))
            dq = 0.0
            sensitivity_rows.append({
                "scenario": scen, "seed": seed, "step": step,
                "feature_group": block,
                "features": indices,
                "delta_state_norm": block_delta,
                "delta_Q_norm": None,  # filled per config below
                "delta_argmax": False,
                "delta_physical": False,
            })
        # Fill Q/argmax/physical sensitivity from the per-config records.
        for row in sensitivity_rows:
            if row["scenario"] != scen or row["seed"] != seed or row["step"] != step:
                continue
            block = row["feature_group"]
            configs_for_block = {
                "lstm": ["no_lstm"],
                "storage": ["no_ems"],  # storage features only change via EMS side-effects; here they are constant
                "twin": ["no_twin"],
            }[block]
            # For storage, EMS does not alter the DQN features in this
            # snapshot (SOC read from house nodes only), so we report 0.
            dqs = []
            for c in configs_for_block:
                qrec = next(
                    r for r in q_value_comparison
                    if r["scenario"] == scen and r["seed"] == seed
                    and r["step"] == step and r["ablation"] == c
                )
                arec = next(
                    r for r in action_comparison
                    if r["scenario"] == scen and r["seed"] == seed
                    and r["step"] == step and r["ablation"] == c
                )
                dqs.append(qrec["dQ_norm"])
                row["delta_argmax"] = row["delta_argmax"] or arec["action_changed"]
                row["delta_physical"] = (
                    row["delta_physical"] or arec["physical"]["physical_changed"]
                )
            row["delta_Q_norm"] = max(dqs) if dqs else 0.0
            if block == "storage":
                row["delta_Q_norm"] = 0.0
                row["delta_argmax"] = False

    # ---- checkpoint integrity ----
    hash_after = sha256(ckpt)
    checkpoint_hash = {
        "path": str(ckpt),
        "sha256_before": hash_before,
        "sha256_after": hash_after,
        "unchanged": hash_before == hash_after,
        "size_bytes": ckpt.stat().st_size,
        "state_dim": EXTENDED_STATE_DIM,
    }
    assert hash_before == hash_after, "BLOCKED — CHECKPOINT MODIFIED"

    # ---- write outputs ----
    def _dump(name, obj):
        (out_dir / name).write_text(
            json.dumps(obj, indent=2, default=str), encoding="utf-8"
        )
        print(f"[stage46_1] wrote {out_dir / name}")

    _dump("checkpoint_hash.json", checkpoint_hash)
    _dump("state_comparison.json", state_comparison)
    _dump("q_value_comparison.json", q_value_comparison)
    _dump("action_comparison.json", action_comparison)
    _dump("information_sensitivity.json", sensitivity_rows)

    manifest = {
        "schema_version": "stage46.1.manifest.1.0",
        "experiment": "stage46_1_information_flow",
        "checkpoint": str(ckpt),
        "checkpoint_sha256": hash_after,
        "checkpoint_unchanged": checkpoint_hash["unchanged"],
        "state_dim": EXTENDED_STATE_DIM,
        "probe_states": [f"{s}_s{seed}_t{step}" for s, seed, step in PROBE_STATES],
        "configs": [c[0] for c in CONFIGS],
        "feature_blocks": FEATURE_BLOCKS,
        "n_state_comparisons": len(state_comparison),
        "n_q_comparisons": len(q_value_comparison),
        "n_action_comparisons": len(action_comparison),
        "n_sensitivity_rows": len(sensitivity_rows),
        "git_sha": __import__("subprocess").run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=str(PROJECT_ROOT),
        ).stdout.strip() or "no_git",
    }
    _dump("manifest.json", manifest)

    # ---- console summary ----
    print("\n=== Stage 46.1 single-state ablation summary ===")
    print(f"{'probe':<18} {'ablation':<12} {'Δstate':>8} {'ΔQ_norm':>9} {'Δargmax':>8}")
    for r in state_comparison:
        q = next(
            (q for q in q_value_comparison if q["scenario"] == r["scenario"]
             and q["seed"] == r["seed"] and q["step"] == r["step"]
             and q["ablation"] == r["ablation"]), None)
        a = next(
            (a for a in action_comparison if a["scenario"] == r["scenario"]
             and a["seed"] == r["seed"] and a["step"] == r["step"]
             and a["ablation"] == r["ablation"]), None)
        probe = f"{r['scenario']} s{r['seed']} t{r['step']}"
        print(f"{probe:<18} {r['ablation']:<12} "
              f"{r['delta_state_norm']:8.4f} "
              f"{q['dQ_norm'] if q else 0:9.4f} "
              f"{str(a['action_changed']) if a else '?':>8}")


if __name__ == "__main__":
    main()
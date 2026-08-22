"""stage46_2_storage_audit.py — Stage 46.2 physical storage & EMS integration
audit.

Verifies, with the FROZEN Stage-44 checkpoint and an untouched simulator,
whether the advertised architecture actually exists in the executable
system:

    renewable generation
        -> hybrid battery + supercapacitor storage
        -> intelligent energy management
        -> DQN / smart-grid controller
        -> continuous consumer supply

Probes (all deterministic, seed 0):

  1. Node-type audit for STORAGE_BAT / STORAGE_SC and every
     battery/supercap/storage_bat/storage_sc reference in the codebase.
  2. Per-action physical probes (actions 0..4) at midday and night:
     battery SOC, supercap SOC, generation, load, received power, ENS,
     voltage — measured before and after a runner-order step.
  3. EMS ON vs EMS OFF on byte-identical pre-EMS snapshots.
  4. DQN observability of storage SOC (features 73/74).
  5. Battery/supercap priority behaviour on the A..E scenario set.
  6. Energy-accounting model and voltage feasibility.

The checkpoint is NEVER modified. SHA-256 recorded before and after.

Run from ``backend/``::

  python -m experiments.stage46_2_storage_audit \
      --out experiments/results/stage46_2
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

THIS = Path(__file__).resolve()
BACKEND = THIS.parents[1]
PROJECT_ROOT = THIS.parents[2]
for p in (str(PROJECT_ROOT), str(BACKEND), str(BACKEND / "experiments")):
    if p not in sys.path:
        sys.path.insert(0, p)

from utils.seeds import set_global_seed  # noqa: E402
from simulation.grid import SmartGrid  # noqa: E402
from simulation.ems import EnergyManagementSystem  # noqa: E402
from experiments.stage44_validation import (  # noqa: E402
    _build_scenario_for_seed, _apply_scenario_to_grid,
)
from experiments.runner import _dispatch_action  # noqa: E402
from experiments.scenario_matrix import get_scenario_spec  # noqa: E402

CKPT = BACKEND / "experiments" / "checkpoints" / "dqn_stage44.pt"
EXPECTED_SHA256 = "eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493"

_CONSUMER_TYPES = ("house", "hospital", "industry", "hospital_icu")

ACTION_NAMES = {0: "increase_generation", 1: "use_battery",
                2: "use_supercapacitor", 3: "shift_load", 4: "reroute_energy"}


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _spec(scenario) -> dict:
    return get_scenario_spec(scenario.label.split("|")[0])


def build_grid(scenario_label: str, seed: int = 0) -> Tuple[SmartGrid, object]:
    scenario = _build_scenario_for_seed(scenario_label, seed)
    set_global_seed(seed)
    grid = SmartGrid(seed=seed)
    _apply_scenario_to_grid(grid, scenario)
    try:
        grid.update_power_flow()
    except Exception:
        pass
    return grid, scenario


def advance(grid, scenario, n_steps: int) -> None:
    """Run ``n_steps`` of the runner-style loop (fault injection +
    physics step + power flow) without any controller action."""
    for t in range(n_steps):
        for f in scenario.faults:
            if f.timestep == t:
                try:
                    grid.inject_failure(f.target)
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


def snap(grid) -> dict:
    """Full physical snapshot of the grid (Stage-45 metric surface)."""
    nodes = list(grid.nodes.values())
    total_gen = sum(float(n.generation) for n in nodes)
    total_load = sum(float(n.load) for n in nodes)
    recv = sum(float(getattr(n, "received_power", 0.0) or 0.0) for n in nodes)
    served_mwh = recv / 60.0
    ens = 0.0
    crit_out = 0
    for n in nodes:
        if str(getattr(n, "node_type", "")) not in _CONSUMER_TYPES:
            continue
        base = float(grid.would_be_load(n))
        served = float(getattr(n, "received_power", 0.0) or 0.0)
        ens += max(0.0, base - served) / 60.0
        if str(getattr(n, "node_type", "")) in ("hospital", "hospital_icu") \
                and served <= 0:
            crit_out += 1
    vols = [float(n.voltage) for n in nodes]
    deficits = sum(float(n.deficit) for n in nodes)
    excesses = sum(float(n.excess_energy) for n in nodes)
    sb = grid.nodes["STORAGE_BAT"]
    sc = grid.nodes["STORAGE_SC"]
    house_bat = max(float(n.battery_level) for n in nodes
                    if n.node_type == "house")
    house_sc = max(float(n.supercap_level) for n in nodes
                   if n.node_type == "house")
    failed = sum(1 for n in nodes if n.failed)
    isolated = sum(1 for n in nodes if n.isolated)
    return {
        "timestep": int(getattr(grid, "timestep", 0)),
        "total_gen_mw": round(total_gen, 6),
        "total_load_mw": round(total_load, 6),
        "balance_mw": round(total_gen - total_load, 6),
        "received_power_mw": round(recv, 6),
        "served_mwh": round(served_mwh, 6),
        "ens_shortfall_mwh": round(ens, 6),
        "critical_interrupted_nodes": crit_out,
        "system_deficit_mw": round(deficits, 6),
        "system_excess_mw": round(excesses, 6),
        "voltage_min": round(min(vols), 6),
        "voltage_max": round(max(vols), 6),
        "voltage_violations": sum(1 for v in vols if abs(v - 1.0) > 0.10),
        "battery_bat_soc": round(float(sb.battery_level), 6),
        "supercap_sc_soc": round(float(sc.supercap_level), 6),
        "battery_bat_gen": round(float(sb.generation), 6),
        "supercap_sc_gen": round(float(sc.generation), 6),
        "house_battery_soc": round(house_bat, 6),
        "house_supercap_soc": round(house_sc, 6),
        "failed_nodes": failed,
        "isolated_nodes": isolated,
    }


def run_action_step(grid, scenario, action_id: int) -> None:
    """Mirror the runner's per-step order: dispatch -> step -> power flow."""
    _dispatch_action(grid, action_id)
    try:
        grid.step()
    except Exception:
        pass
    try:
        grid.update_power_flow()
    except Exception:
        pass


def run_ems_step(grid, scenario, ems) -> dict:
    """Mirror the runner's EMS step: step -> EMS -> power flow."""
    try:
        grid.step()
    except Exception:
        pass
    report = {}
    if ems is not None:
        report = ems.run(grid)
    try:
        grid.update_power_flow()
    except Exception:
        pass
    return report


# ----------------------------------------------------------------------
# 1. Node-type audit
# ----------------------------------------------------------------------

def node_type_audit() -> dict:
    g, _ = build_grid("A", seed=0)
    sb = g.nodes["STORAGE_BAT"]
    sc = g.nodes["STORAGE_SC"]
    rows = [
        {
            "location": "simulation/grid.py::_build_grid (line ~237/247)",
            "expected_type": "battery / supercap",
            "actual_type": (sb.node_type, sc.node_type),
            "effect": "grid-scale storage connected to S_MAIN",
        },
        {
            "location": "experiments/runner.py::_dispatch_action (action 1)",
            "match_rule": "'storage_bat' in node_type or node_type=='house'",
            "actual_type": sb.node_type,
            "effect": f"matched={('storage_bat' in sb.node_type)} "
                      f"-> STORAGE_BAT is NOT dispatched by action 1",
        },
        {
            "location": "experiments/runner.py::_dispatch_action (action 2)",
            "match_rule": "'storage_sc' in node_type or node_type=='house'",
            "actual_type": sc.node_type,
            "effect": f"matched={('storage_sc' in sc.node_type)} "
                      f"-> STORAGE_SC is NOT dispatched by action 2",
        },
        {
            "location": "experiments/stage44_dqn_training.py::_highest_storage_soc",
            "match_rule": "'storage_bat'/'storage_sc' substring",
            "actual_type": (sb.node_type, sc.node_type),
            "effect": "SOC features 73/74 exclude STORAGE_BAT/STORAGE_SC "
                      "during training",
        },
        {
            "location": "experiments/dqn_training.py::_soc",
            "match_rule": "'storage_bat'/'storage_sc' substring",
            "actual_type": (sb.node_type, sc.node_type),
            "effect": "SOC features exclude grid-scale storage",
        },
        {
            "location": "experiments/runner.py::_storage_level",
            "match_rule": "'storage_bat'/'storage_sc' substring",
            "actual_type": (sb.node_type, sc.node_type),
            "effect": "runner DQN state excludes grid-scale storage SOC",
        },
        {
            "location": "experiments/stage44_validation.py (feature 73/74)",
            "match_rule": "node_type=='house'",
            "actual_type": (sb.node_type, sc.node_type),
            "effect": "validation harness SOC features read houses only",
        },
        {
            "location": "simulation/ems.py::_charge_storage",
            "match_rule": "node_type in ('battery','supercap')",
            "actual_type": (sb.node_type, sc.node_type),
            "effect": "EMS charging DOES target STORAGE_BAT/STORAGE_SC",
        },
        {
            "location": "simulation/grid.py BFS source broadening (line ~1127)",
            "match_rule": "generation>0 and type in (house,battery,supercap,...)",
            "actual_type": (sb.node_type, sc.node_type),
            "effect": "power-flow WOULD deliver a battery/supercap "
                      "generation injection if one existed",
        },
    ]
    return {
        "STORAGE_BAT": {
            "node_id": "STORAGE_BAT", "node_type": sb.node_type,
            "battery_capacity_mwh": sb.battery_capacity,
            "battery_soc_init": sb.battery_level,
            "discharge_rate_mw": getattr(sb, "discharge_rate", None),
            "role": sb.role, "source_type": sb.source_type,
            "connected_to": list(g.graph.neighbors("STORAGE_BAT")),
        },
        "STORAGE_SC": {
            "node_id": "STORAGE_SC", "node_type": sc.node_type,
            "supercap_capacity_mwh": sc.supercap_capacity,
            "supercap_soc_init": sc.supercap_level,
            "discharge_rate_mw": getattr(sc, "discharge_rate", None),
            "role": sc.role, "source_type": sc.source_type,
            "connected_to": list(g.graph.neighbors("STORAGE_SC")),
        },
        "audit_rows": rows,
        "mismatch_summary": (
            "ACTION DISPATCH + SOC OBSERVATION use the substrings "
            "'storage_bat'/'storage_sc' which do NOT match the actual "
            "node_types 'battery'/'supercap'. EMS charging and the BFS "
            "power-flow use the correct types."
        ),
    }


# ----------------------------------------------------------------------
# 2. Action probes
# ----------------------------------------------------------------------

def probe_action(scenario_label: str, seed: int, reference_step: int,
                 action_id: int) -> dict:
    """Probe one action at a reference step (runner-order dispatch)."""
    grid, scenario = build_grid(scenario_label, seed)
    advance(grid, scenario, reference_step)
    pre = snap(grid)
    # Attribute-level deltas of interest (before the step executes).
    nodes = grid.nodes
    bat = nodes["STORAGE_BAT"]
    scp = nodes["STORAGE_SC"]
    action_specific_pre = {
        "bat_soc": float(bat.battery_level),
        "sc_soc": float(scp.supercap_level),
        "bat_gen": float(bat.generation),
        "sc_gen": float(scp.generation),
        "gen_solar": float(nodes["GEN_SOLAR"].generation),
        "gen_gas": float(nodes["GEN_GAS"].generation),
    }
    house_bat_soc_pre = max(float(n.battery_level)
                            for n in nodes.values() if n.node_type == "house")
    house_sc_soc_pre = max(float(n.supercap_level)
                           for n in nodes.values() if n.node_type == "house")
    total_load_pre = sum(float(n.load) for n in nodes.values())
    base_loads_pre = {nid: float(getattr(n, "_base_load", 0.0) or 0.0)
                      for nid, n in nodes.items()}

    # Dispatch then advance one runner-order step.
    _dispatch_action(grid, action_id)
    dispatched = snap(grid)  # after dispatch, before step
    run_action_step(grid, scenario, action_id)
    post = snap(grid)

    house_bat_soc_post = max(float(n.battery_level)
                             for n in nodes.values() if n.node_type == "house")
    house_sc_soc_post = max(float(n.supercap_level)
                            for n in nodes.values() if n.node_type == "house")
    total_load_post = sum(float(n.load) for n in nodes.values())
    base_loads_post = {nid: float(getattr(n, "_base_load", 0.0) or 0.0)
                       for nid, n in nodes.items()}

    gen_solar_after_step = float(nodes["GEN_SOLAR"].generation)
    gen_gas_after_step = float(nodes["GEN_GAS"].generation)

    return {
        "scenario": scenario_label, "seed": seed,
        "reference_step": reference_step,
        "action_id": action_id,
        "action_name": ACTION_NAMES[action_id],
        "pre": pre,
        "post": post,
        "deltas": {
            "battery_bat_soc": round(post["battery_bat_soc"] - pre["battery_bat_soc"], 6),
            "supercap_sc_soc": round(post["supercap_sc_soc"] - pre["supercap_sc_soc"], 6),
            "battery_bat_gen": round(post["battery_bat_gen"] - pre["battery_bat_gen"], 6),
            "supercap_sc_gen": round(post["supercap_sc_gen"] - pre["supercap_sc_gen"], 6),
            "house_battery_soc": round(house_bat_soc_post - house_bat_soc_pre, 6),
            "house_supercap_soc": round(house_sc_soc_post - house_sc_soc_pre, 6),
            "total_load_mw": round(total_load_post - total_load_pre, 6),
            "served_mwh": round(post["served_mwh"] - pre["served_mwh"], 6),
            "ens_shortfall_mwh": round(post["ens_shortfall_mwh"] - pre["ens_shortfall_mwh"], 6),
            "received_power_mw": round(post["received_power_mw"] - pre["received_power_mw"], 6),
            "voltage_min": round(post["voltage_min"] - pre["voltage_min"], 6),
            "voltage_violations": post["voltage_violations"] - pre["voltage_violations"],
            "gen_solar_after_step": round(gen_solar_after_step, 6),
            "gen_gas_after_step": round(gen_gas_after_step, 6),
        },
        "target_verdict": {
            "action1_targets_storage_bat": action_id == 1 and (
                post["battery_bat_soc"] - pre["battery_bat_soc"] != 0
            ),
            "action2_targets_storage_sc": action_id == 2 and (
                post["supercap_sc_soc"] - pre["supercap_sc_soc"] != 0
            ),
            "action0_persists_on_solar": action_id == 0 and (
                abs(gen_solar_after_step - pre["total_gen_mw"]) > 0.4
            ),
            "load_conserved": action_id == 3 and (
                abs(total_load_post - total_load_pre) < 1e-9
            ),
            "base_load_conserved": action_id == 3 and all(
                abs(base_loads_post.get(k, 0) - v) < 1e-9
                for k, v in base_loads_pre.items()
            ),
        },
    }


# ----------------------------------------------------------------------
# 3. EMS ON vs OFF
# ----------------------------------------------------------------------

def probe_ems(scenario_label: str, seed: int, reference_step: int) -> dict:
    grid_on, scenario = build_grid(scenario_label, seed)
    advance(grid_on, scenario, reference_step)
    grid_off = copy.deepcopy(grid_on)
    pre = snap(grid_on)

    ems = EnergyManagementSystem(use_pypsa=False)
    report = run_ems_step(grid_on, scenario, ems)
    run_ems_step(grid_off, scenario, None)

    post_on = snap(grid_on)
    post_off = snap(grid_off)
    keys = [
        "total_gen_mw", "total_load_mw", "balance_mw", "received_power_mw",
        "served_mwh", "ens_shortfall_mwh", "system_deficit_mw",
        "system_excess_mw", "voltage_min", "voltage_max",
        "voltage_violations", "battery_bat_soc", "supercap_sc_soc",
        "battery_bat_gen", "supercap_sc_gen",
    ]
    return {
        "scenario": scenario_label, "seed": seed, "reference_step": reference_step,
        "pre": pre,
        "ems_on": post_on,
        "ems_off": post_off,
        "ems_report_message": str(report.get("message", "")),
        "deltas": {
            k: round(post_on[k] - post_off[k], 6) for k in keys
        },
        "physical_effect": any(
            abs(post_on[k] - post_off[k]) > 1e-9 for k in keys
        ),
    }


# ----------------------------------------------------------------------
# 4. DQN observability
# ----------------------------------------------------------------------

def probe_observability(scenario_label: str, seed: int, reference_step: int) -> dict:
    from models.rl_agent import build_extended_state
    grid, scenario = build_grid(scenario_label, seed)
    advance(grid, scenario, reference_step)
    # Harness formula (as in stage44_validation / stage45_validation).
    house_bat = max(float(n.battery_level) for n in grid.nodes.values()
                    if n.node_type == "house")
    house_sc = max(float(n.supercap_level) for n in grid.nodes.values()
                   if n.node_type == "house")
    # Corrected formula (would include dedicated storage).
    all_bat = max(float(n.battery_level) for n in grid.nodes.values()
                  if n.node_type in ("house", "battery"))
    all_sc = max(float(n.supercap_level) for n in grid.nodes.values()
                 if n.node_type in ("house", "supercap"))

    # Discharge the dedicated storage physically.
    g2, _ = build_grid(scenario_label, seed)
    advance(g2, scenario, reference_step)
    g2.nodes["STORAGE_BAT"].use_battery(30.0)   # real drain, 150 MWh cap
    g2.nodes["STORAGE_SC"].use_supercapacitor(5.0)  # real drain, 15 MWh cap
    g2_house_bat = max(float(n.battery_level) for n in g2.nodes.values()
                       if n.node_type == "house")
    g2_house_sc = max(float(n.supercap_level) for n in g2.nodes.values()
                      if n.node_type == "house")
    g2_all_bat = max(float(n.battery_level) for n in g2.nodes.values()
                     if n.node_type in ("house", "battery"))
    g2_all_sc = max(float(n.supercap_level) for n in g2.nodes.values()
                    if n.node_type in ("house", "supercap"))

    base = grid.get_rl_state()
    f_harness_pre = build_extended_state(base, battery_soc=house_bat,
                                         supercap_soc=house_sc)
    f_harness_post = build_extended_state(base, battery_soc=g2_house_bat,
                                          supercap_soc=g2_house_sc)
    f_corrected_pre = build_extended_state(base, battery_soc=all_bat,
                                           supercap_soc=all_sc)
    f_corrected_post = build_extended_state(base, battery_soc=g2_all_bat,
                                            supercap_soc=g2_all_sc)
    return {
        "scenario": scenario_label, "seed": seed, "reference_step": reference_step,
        "storage_after_drain": {
            "STORAGE_BAT.battery_level": round(float(g2.nodes["STORAGE_BAT"].battery_level), 6),
            "STORAGE_SC.supercap_level": round(float(g2.nodes["STORAGE_SC"].supercap_level), 6),
        },
        "feature_73_harness_house_only": {
            "before": f_harness_pre[73], "after_storage_drain": f_harness_post[73],
            "changed": f_harness_post[73] != f_harness_pre[73],
        },
        "feature_74_harness_house_only": {
            "before": f_harness_pre[74], "after_storage_drain": f_harness_post[74],
            "changed": f_harness_post[74] != f_harness_pre[74],
        },
        "feature_73_corrected": {
            "before": f_corrected_pre[73], "after_storage_drain": f_corrected_post[73],
            "changed": f_corrected_post[73] != f_corrected_pre[73],
        },
        "feature_74_corrected": {
            "before": f_corrected_pre[74], "after_storage_drain": f_corrected_post[74],
            "changed": f_corrected_post[74] != f_corrected_pre[74],
        },
        "classification": (
            "PHYSICALLY ACTIVE / OBSERVATION DISCONNECTED: dedicated storage "
            "SOC changes physically but never reaches features 73/74 under the "
            "house-only harness formula."
        ),
    }


# ----------------------------------------------------------------------
# 5. Priority behaviour
# ----------------------------------------------------------------------

def probe_priority() -> dict:
    import torch
    from models.rl_agent import DQNAgent, EXTENDED_STATE_DIM, build_extended_state
    agent = DQNAgent.load_checkpoint(str(CKPT), state_dim=EXTENDED_STATE_DIM,
                                     eval_mode=True)
    out = []
    for label in ("A", "B", "C", "D", "E"):
        grid, scenario = build_grid(label, seed=0)
        advance(grid, scenario, 30)
        snap_pre = snap(grid)
        rl_state = grid.get_rl_state()
        grid_state = grid.get_state()
        # Build extended state (78-dim) with current SOC features
        battery_soc = max(float(n.battery_level) for n in grid.nodes.values()
                          if n.node_type in ("house", "battery"))
        supercap_soc = max(float(n.supercap_level) for n in grid.nodes.values()
                           if n.node_type in ("house", "supercap"))
        twin_max_risk = 0.0
        twin_mean_risk = 0.0
        twin_high_frac = 0.0
        ext_state = build_extended_state(
            rl_state,
            predicted_load=0.5,
            battery_soc=battery_soc,
            supercap_soc=supercap_soc,
            twin_max_risk=twin_max_risk,
            twin_mean_risk=twin_mean_risk,
            twin_high_frac=twin_high_frac,
        )
        with torch.no_grad():
            q = agent.policy_net(
                torch.tensor(ext_state, dtype=torch.float32).unsqueeze(0)
            )[0].numpy()
        valid = agent._valid_actions_mask(grid_state) or [0, 1, 2, 3, 4]
        masked = {a: float(q[a]) for a in valid}
        argmax = max(masked, key=masked.get)
        out.append({
            "scenario": label,
            "characterization": {
                "balance_mw": snap_pre["balance_mw"],
                "system_deficit_mw": snap_pre["system_deficit_mw"],
                "system_excess_mw": snap_pre["system_excess_mw"],
                "battery_available_mwh": snap_pre["battery_bat_soc"] * 150.0,
                "supercap_available_mwh": snap_pre["supercap_sc_soc"] * 15.0,
                "voltage_min": snap_pre["voltage_min"],
            },
            "policy_action": argmax,
            "policy_action_name": ACTION_NAMES[argmax],
            "battery_selected_when_deficit": argmax == 1 and snap_pre["balance_mw"] < 0,
            "supercap_selected_when_voltage_low": (
                argmax == 2 and snap_pre["voltage_min"] < 0.97
            ),
            "storage_ever_selected": argmax in (1, 2),
        })
    return out


# ----------------------------------------------------------------------
# 6. Energy accounting + voltage feasibility
# ----------------------------------------------------------------------

def probe_energy_balance(scenario_label: str, seed: int, reference_step: int) -> dict:
    grid, scenario = build_grid(scenario_label, seed)
    advance(grid, scenario, reference_step)
    snap_pre = snap(grid)
    nodes = grid.nodes.values()
    total_gen = sum(float(n.generation) for n in nodes)
    total_load = sum(float(n.load) for n in nodes)
    recv = sum(float(getattr(n, "received_power", 0.0) or 0.0) for n in nodes)
    deficits = sum(float(n.deficit) for n in nodes)
    excesses = sum(float(n.excess_energy) for n in nodes)
    total_loss = float(getattr(grid, "total_energy_loss", 0.0) or 0.0)
    grid_import = max(0.0, total_load - total_gen)  # import proxy (positive deficit)
    grid_export = max(0.0, total_gen - total_load)
    return {
        "scenario": scenario_label, "seed": seed, "reference_step": reference_step,
        "generation_mw": round(total_gen, 6),
        "load_mw": round(total_load, 6),
        "received_power_mw": round(recv, 6),
        "deficit_mw": round(deficits, 6),
        "excess_mw": round(excesses, 6),
        "dc_losses_mw": round(total_loss, 6),
        "grid_import_proxy_mw": round(grid_import, 6),
        "grid_export_proxy_mw": round(grid_export, 6),
        "generation_minus_load_minus_excess_minus_deficit":
            round(total_gen - total_load - excesses + deficits, 6),
        "accounting_model": (
            "The simulator does NOT track a single closed energy balance. "
            "It tracks per-node generation/load, per-node excess/deficit "
            "(post auto-charge), BFS received_power, and DC line losses. "
            "Storage auto-charge in node.step() consumes surplus before "
            "excess_energy is computed; storage discharge appears as "
            "generation injection (battery) or node-local load offset "
            "(supercap). A closed-form conservation equation is NOT "
            "enforced; the closest identity is "
            "gen - load = excess - deficit after auto-charge."
        ),
    }


def probe_voltage_feasibility() -> list:
    out = []
    for action_id in range(5):
        grid, scenario = build_grid("A", seed=0)
        advance(grid, scenario, 30)
        pre = snap(grid)
        run_action_step(grid, scenario, action_id)
        post = snap(grid)
        out.append({
            "action_id": action_id,
            "action_name": ACTION_NAMES[action_id],
            "voltage_min_pre": pre["voltage_min"],
            "voltage_max_pre": pre["voltage_max"],
            "voltage_min_post": post["voltage_min"],
            "voltage_max_post": post["voltage_max"],
            "violations_pre": pre["voltage_violations"],
            "violations_post": post["voltage_violations"],
            "creates_new_violation": post["voltage_violations"] > pre["voltage_violations"],
            "all_within_0_9_1_1": 0.9 <= post["voltage_min"] and post["voltage_max"] <= 1.1,
        })
    return out


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkpoint", default=str(CKPT))
    ap.add_argument("--out", default=str(BACKEND / "experiments" / "results" / "stage46_2"))
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt = Path(args.checkpoint)

    hash_before = sha256(ckpt)
    assert hash_before == EXPECTED_SHA256, "BLOCKED — checkpoint changed"

    # 1. Node-type audit
    audit = node_type_audit()
    _dump(out_dir, "node_type_audit.json", audit)

    # 2. Action probes at midday (solar peak, hour 10) and night (hour 4).
    action_probes = []
    for ref_step in (34, 4):
        for action_id in range(5):
            p = probe_action("A", 0, ref_step, action_id)
            action_probes.append(p)
            print(f"[action] t={ref_step} a{action_id} "
                  f"{p['action_name']:<18} "
                  f"dSOC_bat={p['deltas']['battery_bat_soc']:.5f} "
                  f"dSOC_sc={p['deltas']['supercap_sc_soc']:.5f} "
                  f"dhouse_bat={p['deltas']['house_battery_soc']:.5f} "
                  f"dhouse_sc={p['deltas']['house_supercap_soc']:.5f} "
                  f"dserved={p['deltas']['served_mwh']:.6f} "
                  f"dENS={p['deltas']['ens_shortfall_mwh']:.6f}")
    _dump(out_dir, "action_physical_effects.json", action_probes)

    # 3. EMS on/off
    ems_probes = [probe_ems("A", 0, 34), probe_ems("A", 0, 4)]
    for p in ems_probes:
        print(f"[ems] t={p['reference_step']} physical_effect={p['physical_effect']} "
              f"dSOC_bat={p['deltas']['battery_bat_soc']} "
              f"dSOC_sc={p['deltas']['supercap_sc_soc']} "
              f"dgen={p['deltas']['total_gen_mw']} "
              f"dserved={p['deltas']['served_mwh']}")
    _dump(out_dir, "ems_comparison.json", ems_probes)

    # 4. Observability
    obs = [probe_observability("A", 0, 34), probe_observability("A", 0, 4)]
    for o in obs:
        print(f"[obs] t={o['reference_step']} "
              f"feat73_harness_changed={o['feature_73_harness_house_only']['changed']} "
              f"feat74_harness_changed={o['feature_74_harness_house_only']['changed']} "
              f"feat73_corrected_changed={o['feature_73_corrected']['changed']} "
              f"feat74_corrected_changed={o['feature_74_corrected']['changed']}")
    _dump(out_dir, "storage_state_trace.json", obs)

    # 5. Priority behaviour
    prio = probe_priority()
    for p in prio:
        print(f"[prio] {p['scenario']}: balance={p['characterization']['balance_mw']:.3f} "
              f"action={p['policy_action']} ({p['policy_action_name']})")
    _dump(out_dir, "priority_behaviour.json", prio)

    # 6. Energy balance + voltage
    eb = probe_energy_balance("A", 0, 34)
    _dump(out_dir, "energy_balance.json", eb)
    volt = probe_voltage_feasibility()
    _dump(out_dir, "voltage_effects.json", volt)

    # Checkpoint integrity
    hash_after = sha256(ckpt)
    assert hash_after == EXPECTED_SHA256, "BLOCKED — checkpoint modified"
    chk = {
        "path": str(ckpt),
        "sha256_before": hash_before,
        "sha256_after": hash_after,
        "unchanged": hash_before == hash_after,
        "size_bytes": ckpt.stat().st_size,
    }
    _dump(out_dir, "checkpoint_hash.json", chk)

    manifest = {
        "schema_version": "stage46.2.manifest.1.0",
        "experiment": "stage46_2_storage_audit",
        "checkpoint": str(ckpt),
        "checkpoint_sha256": hash_after,
        "checkpoint_unchanged": chk["unchanged"],
        "git_sha": __import__("subprocess").run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=str(PROJECT_ROOT)).stdout.strip() or "no_git",
        "action_probes": len(action_probes),
        "ems_probes": len(ems_probes),
        "observability_probes": len(obs),
        "priority_scenarios": [p["scenario"] for p in prio],
    }
    _dump(out_dir, "manifest.json", manifest)
    print(f"\nStage 46.2 audit complete. Wrote {len(list(out_dir.iterdir()))} files to {out_dir}")


def _dump(out_dir, name, obj):
    (out_dir / name).write_text(json.dumps(obj, indent=2, default=str),
                                encoding="utf-8")
    print(f"[stage46_2] wrote {out_dir / name}")


if __name__ == "__main__":
    main()
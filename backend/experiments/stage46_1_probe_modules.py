"""Stage 46.1 probe — do EMS / predictive-healer / twin actually change
anything on the Stage-45 evaluation scenarios (A, E, I, J)?

Read-only: builds a scenario state and measures post-call grid deltas.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from utils.seeds import set_global_seed
from simulation.grid import SmartGrid
from experiments.stage44_validation import (
    _build_scenario_for_seed, _apply_scenario_to_grid,
)


def grid_snapshot(grid):
    return {
        nid: {
            "load": float(getattr(n, "load", 0.0) or 0.0),
            "generation": float(getattr(n, "generation", 0.0) or 0.0),
            "battery_level": float(getattr(n, "battery_level", 0.0) or 0.0),
            "supercap_level": float(getattr(n, "supercap_level", 0.0) or 0.0),
            "deficit": float(getattr(n, "deficit", 0.0) or 0.0),
            "excess_energy": float(getattr(n, "excess_energy", 0.0) or 0.0),
            "voltage": float(getattr(n, "voltage", 1.0) or 1.0),
            "failed": bool(getattr(n, "failed", False)),
            "isolated": bool(getattr(n, "isolated", False)),
        }
        for nid, n in grid.nodes.items()
    }


def diff_snap(a, b):
    keys = set(a) | set(b)
    out = {}
    for k in keys:
        da, db = a.get(k), b.get(k)
        if da is None or db is None:
            continue
        for f in da:
            va, vb = da[f], db[f]
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                if abs(float(va) - float(vb)) > 1e-9:
                    out[f"{k}.{f}"] = (va, vb)
    return out


def run_probe(scen_label, seed, step):
    scenario = _build_scenario_for_seed(scen_label, seed)
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

    # --- twin risk after a full scenario build ---
    from digital_twin.twin_registry import TwinRegistry
    from experiments.scenario_matrix import get_scenario_spec
    twin = TwinRegistry()
    twin.register(grid)
    spec = get_scenario_spec(scen_label)
    if spec.health_override:
        from experiments.info_flow import _pre_age_twins
        _pre_age_twins(twin, dict(spec.health_override))
    risks = {}
    for tw in twin.all():
        v = float(getattr(tw, "health_risk_score", 0.0) or 0.0)
        if v > 1e-9:
            risks[tw.asset_id] = v
    print(f"[{scen_label} s{seed} t{step}] twin risks > 0: {risks}")

    # --- EMS effect ---
    before = grid_snapshot(grid)
    from simulation.ems import EnergyManagementSystem
    ems = EnergyManagementSystem(use_pypsa=False)
    report = ems.run(grid)
    after = grid_snapshot(grid)
    d = diff_snap(before, after)
    print(f"[{scen_label} s{seed} t{step}] EMS run -> grid deltas: {d}")
    print(f"    EMS message: {report.get('message')}")
    print(f"    EMS log: {report.get('log')}")

    # --- predictive healer effect ---
    before2 = grid_snapshot(grid)
    from self_healing.predictor import PredictiveSelfHealer
    healer = PredictiveSelfHealer()
    rep = healer.run(grid, twin)
    after2 = grid_snapshot(grid)
    d2 = diff_snap(before2, after2)
    print(f"[{scen_label} s{seed} t{step}] PredictiveSelfHealer.run -> grid deltas: {d2}")
    print(f"    healer risk_count={rep.get('risk_count')} action_count={rep.get('action_count')}")


if __name__ == "__main__":
    for scen, seed, step in [("A", 0, 10), ("E", 0, 10), ("I", 0, 10), ("J", 0, 10), ("H", 0, 10)]:
        run_probe(scen, seed, step)
        print()
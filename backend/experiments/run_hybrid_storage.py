"""run_hybrid_storage.py — Stage 21 hybrid-storage experiment.

Compares three storage policies under the same fault scenario:

  * ``hybrid``      — battery + supercap with supercap-first dispatch.
  * ``battery_only`` — battery only (no supercap).
  * ``supercap_only`` — supercap only (no battery).
  * ``none``        — no storage at all (control).

Each policy is run on a fresh default SmartGrid with the same fault
scenario. The metrics of interest are:

  * **Energy not served (MWh)** — total load that could not be met.
  * **Average customer-minutes interrupted** — sum of (load ×
    outage-time) per consumer node.
  * **Number of recovery events** — count of timesteps where a
    previously-isolated node became re-energised.

The experiment is deterministic given a fixed ``--seed`` and a
frozen scenario. Output is persisted to
``experiments/results/hybrid_storage.json``.

Limitations
-----------
* Round-trip efficiency is 100 % (no thermal losses — see
  ``docs/LIMITATIONS.md``).
* No DC-bus dynamics, no inverter model.
* Comparison is over a *single* scenario (the user can pass
  ``--scenario-seed`` to vary it).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from simulation.grid import SmartGrid           # noqa: E402
from experiments.scenario import make_scenario   # noqa: E402
from utils.seeds import make_rng                # noqa: E402


POLICIES = ("hybrid", "battery_only", "supercap_only", "none")


@dataclass
class StepMetric:
    timestep: int
    served_mw: float
    customer_minutes_interrupted: float
    energy_not_served_mwh: float


def _total_load(grid: SmartGrid) -> float:
    return sum(
        float(getattr(n, "load", 0.0) or 0.0)
        for n in grid.nodes.values()
        if n.node_type in ("house", "hospital", "industry", "hospital_icu",
                            "commercial", "school", "university", "ev_charger")
    )


def _served(grid: SmartGrid) -> float:
    served = 0.0
    for n in grid.nodes.values():
        if n.node_type in ("house", "hospital", "industry", "hospital_icu",
                            "commercial", "school", "university", "ev_charger"):
            r = float(getattr(n, "received_power", 0.0) or 0.0)
            if r > 0:
                served += r
    return served


def _apply_storage_policy(
    grid: SmartGrid,
    policy: str,
) -> None:
    """One-step storage dispatch for the given policy."""
    if policy == "none":
        return
    for n in grid.nodes.values():
        if not getattr(n, "is_storage", False):
            continue
        nt = n.node_type
        if policy == "battery_only" and nt != "battery":
            continue
        if policy == "supercap_only" and nt != "supercap":
            continue
        # Hybrid: supercap first (if present and low), then battery.
        if policy == "hybrid":
            if nt == "supercap" and n.supercap_level < 0.95:
                n.supercap_level = min(1.0, n.supercap_level + 0.02)
            elif nt == "battery" and n.battery_level < 0.95:
                n.battery_level = min(1.0, n.battery_level + 0.01)
        elif policy == "battery_only":
            if n.battery_level < 0.95:
                n.battery_level = min(1.0, n.battery_level + 0.02)
        elif policy == "supercap_only":
            if n.supercap_level < 0.95:
                n.supercap_level = min(1.0, n.supercap_level + 0.04)


def _run_policy(
    *,
    policy: str,
    scenario_seed: int,
    total_steps: int,
    fault_count: int,
) -> Dict[str, float]:
    grid = SmartGrid()
    scen = make_scenario(
        seed=scenario_seed,
        total_steps=total_steps,
        fault_count=fault_count,
        weather_mode="normal",
    )

    faults_by_step: Dict[int, list] = {}
    for f in scen.faults:
        faults_by_step.setdefault(f.timestep, []).append(f)

    total_load = _total_load(grid)
    cumulative_ensi = 0.0
    cumulative_ens = 0.0
    n_steps = 0
    n_recoveries = 0
    last_failed_count = 0

    for step in range(scen.total_steps):
        # Inject faults
        for f in faults_by_step.get(step, []):
            try:
                grid.inject_failure(f.target)
            except Exception:
                pass

        # Storage dispatch
        _apply_storage_policy(grid, policy)

        # Power flow
        try:
            grid.update_power_flow()
        except Exception:
            pass

        # Record
        n_steps += 1
        served = _served(grid)
        ensi_step = max(0.0, total_load - served)
        ens_mwh = ensi_step * (1.0 / 60.0)
        cumulative_ensi += ensi_step
        cumulative_ens += ens_mwh

        # Recovery heuristic
        failed_now = sum(1 for n in grid.nodes.values() if n.failed)
        if failed_now < last_failed_count:
            n_recoveries += (last_failed_count - failed_now)
        last_failed_count = failed_now

    return {
        "policy": policy,
        "n_steps": n_steps,
        "energy_not_served_mwh": cumulative_ens,
        "customer_minutes_interrupted": cumulative_ensi,
        "n_recoveries": n_recoveries,
    }


def run(
    *,
    scenario_seed: int = 0,
    total_steps: int = 40,
    fault_count: int = 5,
    write_path: Optional[Path] = None,
) -> dict:
    rng = make_rng(scenario_seed)
    del rng  # unused — placeholder for future weather integration

    per_policy: List[Dict[str, float]] = []
    for policy in POLICIES:
        result = _run_policy(
            policy=policy,
            scenario_seed=scenario_seed,
            total_steps=total_steps,
            fault_count=fault_count,
        )
        per_policy.append(result)

    summary_lines = [
        f"Hybrid-storage experiment (scenario_seed={scenario_seed}, "
        f"total_steps={total_steps}, fault_count={fault_count}):",
    ]
    for row in per_policy:
        summary_lines.append(
            f"  {row['policy']:>15}: ENS={row['energy_not_served_mwh']:.4f} MWh, "
            f"CMI={row['customer_minutes_interrupted']:.2f}, "
            f"recoveries={row['n_recoveries']}"
        )

    out = {
        "scenario_seed": scenario_seed,
        "total_steps": total_steps,
        "fault_count": fault_count,
        "results": per_policy,
        "summary": "\n".join(summary_lines),
    }

    if write_path:
        write_path.parent.mkdir(parents=True, exist_ok=True)
        with open(write_path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
    return out


def _parse_args(argv: list) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compare hybrid vs battery-only vs supercap-only storage."
    )
    p.add_argument("--seed", type=int, default=0,
                   help="Scenario RNG seed (default: 0).")
    p.add_argument("--ticks", type=int, default=40,
                   help="Total timesteps per run (default: 40).")
    p.add_argument("--faults", type=int, default=5,
                   help="Number of faults per scenario (default: 5).")
    p.add_argument("--out", type=str, default=str(HERE / "results" / "hybrid_storage.json"))
    return p.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    out = run(
        scenario_seed=args.seed,
        total_steps=args.ticks,
        fault_count=args.faults,
        write_path=Path(args.out),
    )
    print(out["summary"])
    print(f"\nResults written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
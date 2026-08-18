"""
runner.py — Benchmark orchestration: runs each (policy, scenario, seed)
combination, collects metrics, and writes a JSON summary.

Usage:
    python -m benchmarks.runner --seeds 5 --output results/smoke.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from typing import Dict, List

# Allow `python -m benchmarks.runner` or `python benchmarks/run_benchmark.py`
_THIS = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_THIS)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from simulation.grid import SmartGrid  # noqa: E402
from simulation.scada import ScadaControlCenter  # noqa: E402
from benchmarks.scenarios import SCENARIOS, WEATHER_MODES, apply_weather  # noqa: E402
from benchmarks.metrics import compute_all  # noqa: E402
from benchmarks.baselines import (  # noqa: E402
    RandomPolicy, RuleBasedPolicy,
)


def _build_policies(seed: int) -> Dict[str, object]:
    return {
        "random":     RandomPolicy(seed=seed),
        "rule_based": RuleBasedPolicy(),
    }


# Map baseline action_id → rl_agent action name
_ACTION_NAMES = {
    0: "increase_generation",
    1: "use_battery",
    2: "use_supercapacitor",
    3: "shift_load",
    4: "reroute_energy",
}


def _run_one(seed: int, policy_name: str, scenario_name: str,
             weather: str, max_steps: int = 30) -> Dict[str, float]:
    """Run a single (seed, policy, scenario, weather) and return metrics."""
    random.seed(seed)
    grid = SmartGrid()
    apply_weather(grid, weather)
    meta = SCENARIOS[scenario_name](grid)

    # A SCADA control center is what dispatches actions in production.
    # We instantiate a fresh one for each run so RL state is isolated.
    scada = ScadaControlCenter()

    policy = _build_policies(seed)[policy_name]
    for step in range(max_steps):
        state = grid.get_state()
        rl_state = grid.get_rl_state()
        action_id = policy.choose_action(rl_state, state)
        action_name = _ACTION_NAMES[action_id]
        scada._dispatch_control_signal(action_name, state, grid)
        grid.update_power_flow()

    return compute_all(grid, meta)


def run(seeds: int = 5, output_path: str = "results/run.json") -> dict:
    """Run all (policy × scenario × weather) for each seed."""
    started = time.time()
    results: List[dict] = []
    for seed in range(seeds):
        for policy_name in ["random", "rule_based"]:
            for scenario_name in SCENARIOS.keys():
                for weather in WEATHER_MODES:
                    metrics = _run_one(seed, policy_name, scenario_name, weather)
                    results.append({
                        "seed":      seed,
                        "policy":    policy_name,
                        "scenario":  scenario_name,
                        "weather":   weather,
                        "metrics":   metrics,
                    })
    summary = {
        "wallclock_s": round(time.time() - started, 2),
        "n_seeds":      seeds,
        "n_policies":   2,
        "n_scenarios":  len(SCENARIOS),
        "n_weathers":   len(WEATHER_MODES),
        "total_runs":   len(results),
        "results":      results,
    }
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[bench] Wrote {len(results)} runs to {output_path} "
          f"in {summary['wallclock_s']:.1f} s")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds",  type=int, default=5)
    p.add_argument("--output", type=str, default="benchmarks/results/run.json")
    args = p.parse_args()
    run(seeds=args.seeds, output_path=args.output)


if __name__ == "__main__":
    main()
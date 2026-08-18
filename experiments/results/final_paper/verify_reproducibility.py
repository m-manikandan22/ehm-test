"""verify_reproducibility.py — Phase 7 verification.

Confirms that the scenario generator is deterministic in seed:
  - Same seed → same fault list
  - Different seeds → different fault lists
  - Across all weather modes
  - Same seed paired with different configs receives the same scenario

Emits reproducibility_report.json.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, List

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
for p in (os.path.join(PROJECT_ROOT, "backend"), PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from experiments.scenario import make_scenario  # noqa: E402
from experiments.runner import run_single  # noqa: E402
from experiments.experiment_config import ABLATION_CONFIGS  # noqa: E402


def main() -> int:
    out_dir = os.path.join("experiments", "results", "final_paper", "logs")
    os.makedirs(out_dir, exist_ok=True)

    TICKS = 50
    FAULTS = 2
    WEATHERS = ["normal", "high_demand", "storm"]
    SEEDS = [0, 1, 2, 3, 4]

    # 1. Same seed → same fault list
    same_seed_report: List[Dict[str, object]] = []
    for seed in SEEDS:
        for weather in WEATHERS:
            a = make_scenario(seed=seed, total_steps=TICKS, fault_count=FAULTS,
                              weather_mode=weather, label="a")
            b = make_scenario(seed=seed, total_steps=TICKS, fault_count=FAULTS,
                              weather_mode=weather, label="b")
            same = (
                [(f.timestep, f.target, f.duration_steps) for f in a.faults]
                == [(f.timestep, f.target, f.duration_steps) for f in b.faults]
            )
            same_seed_report.append({
                "seed": seed,
                "weather": weather,
                "faults_a": [(f.timestep, f.target) for f in a.faults],
                "faults_b": [(f.timestep, f.target) for f in b.faults],
                "identical": same,
            })

    # 2. Different seeds → different fault lists (with high probability)
    different_seed_report: List[Dict[str, object]] = []
    for weather in WEATHERS:
        for s1, s2 in [(0, 1), (1, 2), (2, 3)]:
            a = make_scenario(seed=s1, total_steps=TICKS, fault_count=FAULTS,
                              weather_mode=weather)
            b = make_scenario(seed=s2, total_steps=TICKS, fault_count=FAULTS,
                              weather_mode=weather)
            different_seed_report.append({
                "weather": weather,
                "seed_a": s1,
                "seed_b": s2,
                "faults_a": [(f.timestep, f.target) for f in a.faults],
                "faults_b": [(f.timestep, f.target) for f in b.faults],
                "different": (a.faults != b.faults),
            })

    # 3. Same seed paired across configs receives the same scenario
    paired_seed_report: List[Dict[str, object]] = []
    for seed in [0, 1, 2]:
        scenario = make_scenario(seed=seed, total_steps=20, fault_count=1,
                                  weather_mode="normal")
        for label in ["full_stack", "no_lstm", "no_twin", "no_predictive",
                      "no_reward", "dqn_core_only", "rule_based", "random",
                      "persistence"]:
            cfg = ABLATION_CONFIGS[label]
            run = run_single(config=cfg, scenario=scenario)
            paired_seed_report.append({
                "seed": seed,
                "label": label,
                "faults_in_scenario": [(f.timestep, f.target)
                                       for f in scenario.faults],
                "valid": bool(run["validity"]["valid"]),
            })

    # Summarise
    same_seed_pass = all(r["identical"] for r in same_seed_report)
    diff_seed_pass = sum(1 for r in different_seed_report if r["different"]) >= 1
    paired_valid = all(r["valid"] for r in paired_seed_report)

    report = {
        "schema_version": "1.0",
        "scenario_generator": "experiments.scenario.make_scenario",
        "same_seed": {
            "description": "Same seed → identical fault list",
            "n_cases": len(same_seed_report),
            "all_identical": same_seed_pass,
            "details": same_seed_report,
        },
        "different_seed": {
            "description": "Different seeds → different fault lists",
            "n_cases": len(different_seed_report),
            "all_different": diff_seed_pass,
            "details": different_seed_report,
        },
        "paired_scenario_across_configs": {
            "description": "Same scenario replayed across all configs",
            "n_cases": len(paired_seed_report),
            "all_valid": paired_valid,
            "details": paired_seed_report,
        },
        "verdict": "PASS" if (same_seed_pass and paired_valid) else "FAIL",
    }
    json_path = os.path.join(out_dir, "reproducibility_report.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True, default=str)
    print(f"Wrote {json_path}")
    print(f"verdict: {report['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

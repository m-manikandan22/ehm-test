"""run_final_experiment.py — Phase 13: Run the final 100-seed experiment.

Uses the paper_experiment runner with the frozen configuration.
Writes:
  - baseline_results.{json,csv}
  - ablation_results.{json,csv}
  - manifest.json
  - scenarios.json
  - summary.json
  - statistics.{json,md}
  - baseline_table.{csv,md}
  - ablation_table.{csv,md}
"""
from __future__ import annotations

import json
import os
import sys
import time

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
for p in (os.path.join(PROJECT_ROOT, "backend"), PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from experiments.paper_experiment import run_paper_experiment  # noqa: E402


def main() -> int:
    out_dir = os.path.join("experiments", "results", "final_paper", "raw", "paper")
    os.makedirs(out_dir, exist_ok=True)

    seeds = 100
    ticks = 200
    faults = 3
    weather_modes = ["normal"]
    baseline_labels = ["random", "persistence", "rule_based",
                       "dqn_core_only", "full_stack"]
    ablation_labels = ["full_stack", "no_lstm", "no_twin", "no_predictive",
                       "no_reward", "dqn_core_only"]

    print(f"Final experiment: seeds={seeds}, ticks={ticks}, faults={faults}")
    print(f"  baselines: {baseline_labels}")
    print(f"  ablations: {ablation_labels}")
    t0 = time.time()
    summary = run_paper_experiment(
        seeds=seeds,
        ticks=ticks,
        faults_per_run=faults,
        weather_modes=weather_modes,
        baseline_labels=baseline_labels,
        ablation_labels=ablation_labels,
        output_dir=out_dir,
        write_csv=True,
    )
    elapsed = time.time() - t0
    print(f"Done. Total elapsed: {elapsed:.2f}s")
    print(f"Total runs: {summary['n_total_runs']}")
    print(f"Valid runs: {summary['n_valid_runs']} "
          f"({summary['valid_rate'] * 100:.1f}%)")
    print(f"Baseline validity: {summary['baseline_validity']}")
    print(f"Ablation validity: {summary['ablation_validity']}")
    print(f"Outputs: {summary['outputs']}")
    print(f"Output dir: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

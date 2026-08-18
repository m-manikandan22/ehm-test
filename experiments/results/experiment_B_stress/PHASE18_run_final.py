"""PHASE 18 — Final Experiment B run.

Reads the frozen config and runs the full 100-seed × 2-stress-level
experiment. Output is written to experiment_B_runs.json. The
manifest is written to experiment_B_manifest.json.

This is the single source of evidence for the final reports. We
do NOT overwrite experiment_B_config.json after this is run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, '.')
sys.path.insert(0, 'backend')
from experiments.stress_runner import run_stress_experiment


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--config",
        default="experiments/results/experiment_B_stress/experiment_B_config.json",
    )
    ap.add_argument(
        "--output",
        default="experiments/results/experiment_B_stress/experiment_B_runs.json",
    )
    ap.add_argument(
        "--manifest",
        default="experiments/results/experiment_B_stress/experiment_B_manifest.json",
    )
    ap.add_argument(
        "--seeds",
        type=int,
        default=None,
        help="override seed count (else use config.n_seeds)",
    )
    ap.add_argument(
        "--stress-levels",
        default=None,
        help="comma-separated levels (else use config.stress_levels)",
    )
    ap.add_argument(
        "--policies",
        default=None,
        help="comma-separated policies (else use union of controllers+ablations)",
    )
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    seeds = args.seeds or int(config["n_seeds"])
    levels = (
        [s.strip() for s in args.stress_levels.split(",")]
        if args.stress_levels else list(config["stress_levels"])
    )
    if args.policies:
        policies = [s.strip() for s in args.policies.split(",")]
    else:
        # Union of (controllers + ablations) — preserves raw provenance.
        seen = set()
        policies = []
        for l in list(config["controllers"]) + list(config["ablations"]):
            if l not in seen:
                seen.add(l)
                policies.append(l)

    print(f"PHASE 18 FINAL EXPERIMENT B")
    print(f"seeds={seeds} ticks={config['ticks']}")
    print(f"stress_levels={levels}")
    print(f"policies={policies}")
    expected = len(levels) * seeds * len(policies)
    print(f"expected total runs: {expected}")
    print()

    started = time.time()
    out = run_stress_experiment(
        stress_levels=levels,
        seeds=seeds,
        ticks=int(config["ticks"]),
        policies=policies,
        output_path=args.output,
        write_manifest_path=args.manifest,
    )
    elapsed = time.time() - started

    print()
    print(f"n_total={out['n_total']} n_valid={out['n_valid']} "
          f"n_invalid={out['n_invalid']} "
          f"elapsed={out['elapsed_s']:.1f}s")
    print(f"wall_clock={elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

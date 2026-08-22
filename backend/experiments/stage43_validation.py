"""stage43_validation.py — Stage-43 controlled validation (10 seeds).

Implements the Stage-43 spec §21 validation matrix:

    scenarios   : A, E, G, H, J
    controllers : random, rule_based, untrained_dqn, trained_dqn,
                  full_stack
    seeds       : 0..9 (10)

Every controller runs the IDENTICAL environment for a given
(scenario, seed): the scenario's fault schedule, the grid construction
seed and the stream seeds are fixed, and the run records environment
fingerprints (grid / demand / renewable / fault hashes) so the pairing
can be verified — no controller can claim to have seen a different
environment.

Deliverables
------------
* ``experiments/results/stage43_validation/validation.json`` — every
  run with its fingerprints, seeds, metrics.
* ``experiments/results/stage43_validation/summary.md`` — descriptive
  summary (mean ± std) per (scenario, controller) plus paired
  differences for the paper's headline comparisons. The report is
  DESCRIPTIVE: with n=10 per pair nothing is claimed as significant
  here — the completion report (and only it) issues the gate verdict.

Usage
-----
    python -m experiments.stage43_validation
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from experiments.experiment_config import ExperimentConfig
from experiments.runner import run_single
from experiments.scenario_matrix import build_scenario, get_scenario_spec

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "stage43_validation"
CHECKPOINT = HERE / "checkpoints" / "dqn_extended.pt"

SCENARIO_LABELS = ["A", "E", "G", "H", "J"]
CONTROLLERS = ["random", "rule_based", "untrained_dqn",
               "trained_dqn", "full_stack"]
N_SEEDS = 10


def _config(label: str, seed: int) -> ExperimentConfig:
    if label == "random":
        return ExperimentConfig.random(seed=seed)
    if label == "rule_based":
        return ExperimentConfig.rule_based(seed=seed)
    if label == "untrained_dqn":
        # Full pipeline, DQN on random-initialised weights (no
        # checkpoint) — the Stage-42.5 "policy".
        return ExperimentConfig(
            label=label, seed=seed,
            enable_dqn=True, enable_lstm=True, enable_twin=True,
            enable_predictive_healing=True, enable_reward_shaping=True,
            enable_flisr=True, enable_ems=True, enable_storage=True,
            enable_xai=False, checkpoint_path="",
        )
    if label == "trained_dqn":
        # Full pipeline with the frozen trained policy.
        return ExperimentConfig(
            label=label, seed=seed,
            enable_dqn=True, enable_lstm=True, enable_twin=True,
            enable_predictive_healing=True, enable_reward_shaping=True,
            enable_flisr=True, enable_ems=True, enable_storage=True,
            enable_xai=False,
            checkpoint_path=str(CHECKPOINT) if CHECKPOINT.exists() else "",
        )
    if label == "full_stack":
        return ExperimentConfig.full_stack(seed=seed)
    raise ValueError(label)


def run_validation(seeds: int = N_SEEDS) -> dict:
    runs = []
    for scenario_label in SCENARIO_LABELS:
        spec = get_scenario_spec(scenario_label)
        for seed in range(seeds):
            scenario = build_scenario(seed=seed, spec=spec)
            for ctrl in CONTROLLERS:
                cfg = _config(ctrl, seed)
                result = run_single(
                    config=cfg, scenario=scenario, run_seed=seed,
                )
                result["scenario_label"] = scenario_label
                result["controller_label"] = ctrl
                result["seed"] = seed
                runs.append(result)

    return {
        "schema_version": 2,
        "n_seeds": seeds,
        "scenarios": SCENARIO_LABELS,
        "controllers": CONTROLLERS,
        "checkpoint": str(CHECKPOINT),
        "n_runs": len(runs),
        "runs": runs,
    }


def summarize(data: dict) -> str:
    """Render the descriptive markdown summary."""
    runs = data["runs"]
    lines = [
        "# Stage-43 controlled validation (10 seeds)",
        "",
        f"Scenarios: {', '.join(data['scenarios'])} | "
        f"Controllers: {', '.join(data['controllers'])} | "
        f"Seeds: {data['n_seeds']} | Runs: {data['n_runs']}",
        f"Checkpoint: `{data['checkpoint']}`",
        "",
        "## Pairing integrity (fingerprints)",
        "",
        "Every (scenario, seed) must show identical grid/demand/"
        "renewable/fault fingerprints across all five controllers:",
        "",
    ]
    ok = True
    for sl in data["scenarios"]:
        for seed in range(data["n_seeds"]):
            fp_rows = [
                r["fingerprints"] for r in runs
                if r["scenario_label"] == sl and r["seed"] == seed
            ]
            if len(set(str(f) for f in fp_rows)) != 1:
                ok = False
                lines.append(f"- FAIL {sl}/seed {seed}: fingerprints differ")
    lines.append(f"- {'ALL PAIRS MATCH' if ok else 'MISMATCHES FOUND'}")
    lines.append("")

    lines.append("## Mean ENS (MWh) — lower is better")
    lines.append("")
    lines.append("| Scenario | " + " | ".join(CONTROLLERS) + " |")
    lines.append("| --- | " + " | ".join(["---"] * len(CONTROLLERS)) + " |")
    for sl in data["scenarios"]:
        row = [sl]
        for ctrl in CONTROLLERS:
            vals = [
                r["metrics"]["energy_not_served_mwh"] for r in runs
                if r["scenario_label"] == sl and r["controller_label"] == ctrl
            ]
            if vals:
                mean = sum(vals) / len(vals)
                std = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
                row.append(f"{mean:.4f}±{std:.4f}")
            else:
                row.append("—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## Restoration rate")
    lines.append("")
    lines.append("| Scenario | " + " | ".join(CONTROLLERS) + " |")
    lines.append("| --- | " + " | ".join(["---"] * len(CONTROLLERS)) + " |")
    for sl in data["scenarios"]:
        row = [sl]
        for ctrl in CONTROLLERS:
            vals = [
                r["metrics"].get("restoration_rate") for r in runs
                if r["scenario_label"] == sl and r["controller_label"] == ctrl
            ]
            vals = [v for v in vals if v is not None]
            if vals:
                row.append(f"{sum(vals) / len(vals):.3f}")
            else:
                row.append("—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## Paired comparisons (trained_dqn vs others)")
    lines.append("")
    lines.append("Reported as `mean(other − trained_dqn)` over the 10 "
                 "paired seeds; positive = trained_dqn has LESS ENS.")
    lines.append("")
    lines.append("| Scenario | vs rule_based | vs untrained_dqn | vs random |")
    lines.append("| --- | --- | --- | --- |")
    for sl in data["scenarios"]:
        row = [sl]
        t_ens = {
            r["seed"]: r["metrics"]["energy_not_served_mwh"]
            for r in runs
            if r["scenario_label"] == sl and r["controller_label"] == "trained_dqn"
        }
        for other in ("rule_based", "untrained_dqn", "random"):
            diffs = []
            for r in runs:
                if r["scenario_label"] != sl or r["controller_label"] != other:
                    continue
                if r["seed"] in t_ens:
                    diffs.append(t_ens[r["seed"]] - r["metrics"]["energy_not_served_mwh"])
            if diffs:
                mean = sum(diffs) / len(diffs)
                pos = sum(1 for d in diffs if d > 0)
                row.append(f"{mean:+.4f} ({pos}/{len(diffs)} pairs)")
            else:
                row.append("—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("## Action counts (all scenarios pooled)")
    lines.append("")
    for ctrl in CONTROLLERS:
        counts = {}
        for r in runs:
            if r["controller_label"] != ctrl:
                continue
            for a, c in r["metrics"].get("action_counts", {}).items():
                counts[a] = counts.get(a, 0) + c
        lines.append(f"- **{ctrl}**: {dict(sorted(counts.items()))}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    data = run_validation(seeds=N_SEEDS)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "validation.json").write_text(
        json.dumps(data, indent=2, default=str), encoding="utf-8",
    )
    md = summarize(data)
    (RESULTS / "summary.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\nSaved to {RESULTS}")


if __name__ == "__main__":
    main()

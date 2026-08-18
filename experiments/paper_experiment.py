"""paper_experiment.py — One-command paper experiment runner.

This is the entry point for the paper-grade sweep the master plan
calls out in PHASE 23:

    python -m experiments.paper_experiment \
        --seeds 100 --ticks 200 --faults 3

It runs:

  1. The *baseline comparison* across every controller, using a
     single Scenario per (seed, weather) so the comparison is fair.
  2. The *ablation* across full_stack and the no_* configurations.
  3. The *tables* generator, emitting JSON / CSV / Markdown.
  4. The *manifest* describing the entire run.

Output layout (created if missing):

    experiments/results/paper/
        baseline_results.json
        baseline_results.csv
        baseline_table.md
        ablation_results.json
        ablation_results.csv
        ablation_table.md
        statistics.json
        statistics.md
        manifest.json
        scenarios.json

The defaults are intentionally small (3 seeds × 50 ticks) so a
``smoke`` invocation finishes in seconds; the paper run is then
launched with larger numbers via the CLI.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Dict, List

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
for p in (BACKEND_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from utils.seeds import set_global_seed  # noqa: E402

from experiments.experiment_config import (  # noqa: E402
    ABLATION_CONFIGS, ExperimentConfig, list_ablation_labels,
)
from experiments.runner import run_experiment  # noqa: E402
from experiments.tables import (  # noqa: E402
    build_report, render_markdown, write_csv_and_markdown,
)
from experiments.scenario import make_scenario  # noqa: E402


logger = logging.getLogger(__name__)


# ── Default policy sets ─────────────────────────────────────────────────
# These are the *baseline* and *ablation* policy sets we use for the
# paper. Both include the persistence / random / rule_based anchors
# so every comparison has a common denominator.
DEFAULT_BASELINE_LABELS: List[str] = [
    "random",
    "rule_based",
    "dqn_core_only",
    "full_stack",
]

DEFAULT_ABLATION_LABELS: List[str] = [
    "full_stack",
    "no_lstm",
    "no_twin",
    "no_predictive",
    "no_reward",
    "dqn_core_only",
    "rule_based",
    "random",
]

DEFAULT_WEATHER_MODES: List[str] = ["normal"]


# ── Helpers ─────────────────────────────────────────────────────────────
def _resolve_configs(labels: List[str]) -> List[ExperimentConfig]:
    out: List[ExperimentConfig] = []
    for label in labels:
        if label not in ABLATION_CONFIGS:
            raise KeyError(
                f"Unknown label {label!r}. "
                f"Available: {list_ablation_labels()}"
            )
        out.append(ABLATION_CONFIGS[label])
    return out


def _scenarios_for(seeds: int, ticks: int, faults_per_run: int,
                   weather_modes: List[str]) -> List[dict]:
    out: List[dict] = []
    for weather in weather_modes:
        for seed in range(int(seeds)):
            scen = make_scenario(
                seed=int(seed), total_steps=int(ticks),
                fault_count=int(faults_per_run), weather_mode=weather,
                label=f"seed_{seed}_{weather}",
            )
            out.append(scen.to_dict())
    return out


# ── Main entry point ────────────────────────────────────────────────────
def run_paper_experiment(
    *,
    seeds: int,
    ticks: int,
    faults_per_run: int,
    weather_modes: List[str],
    baseline_labels: List[str],
    ablation_labels: List[str],
    output_dir: str,
    write_csv: bool = True,
) -> Dict[str, object]:
    """Run the paper experiment end-to-end and return the summary."""
    os.makedirs(output_dir, exist_ok=True)

    # Always seed the global PRNG first so torch / numpy are also
    # deterministic.
    set_global_seed(0)

    # Pre-generate the scenario list (for the manifest).
    scenarios = _scenarios_for(seeds, ticks, faults_per_run, weather_modes)
    with open(os.path.join(output_dir, "scenarios.json"), "w") as f:
        json.dump(scenarios, f, indent=2, sort_keys=True)

    # ── Baseline comparison ───────────────────────────────────────────
    baseline_configs = _resolve_configs(baseline_labels)
    baseline_report = run_experiment(
        configs=baseline_configs,
        seeds=seeds,
        ticks=ticks,
        faults_per_run=faults_per_run,
        weather_modes=weather_modes,
        output_path=os.path.join(output_dir, "baseline_results.json"),
        write_csv=write_csv,
        write_manifest_path=os.path.join(output_dir, "manifest.json"),
    )

    # ── Ablation ──────────────────────────────────────────────────────
    ablation_configs = _resolve_configs(ablation_labels)
    ablation_report = run_experiment(
        configs=ablation_configs,
        seeds=seeds,
        ticks=ticks,
        faults_per_run=faults_per_run,
        weather_modes=weather_modes,
        output_path=os.path.join(output_dir, "ablation_results.json"),
        write_csv=write_csv,
        write_manifest_path=None,    # manifest already written above
    )

    # ── Tables ────────────────────────────────────────────────────────
    baseline_tables = build_report(
        runs=baseline_report["runs"], anchor_label="rule_based",
    )
    ablation_tables = build_report(
        runs=ablation_report["runs"], anchor_label="full_stack",
    )
    statistics = {
        "baseline": baseline_tables,
        "ablation": ablation_tables,
    }
    with open(os.path.join(output_dir, "statistics.json"), "w") as f:
        json.dump(statistics, f, indent=2, sort_keys=True, default=str)
    with open(os.path.join(output_dir, "statistics.md"), "w") as f:
        f.write("# EHM-simulation — paper-experiment statistics\n\n")
        f.write("## Baseline comparison\n\n")
        f.write(render_markdown(baseline_tables))
        f.write("\n\n## Ablation study\n\n")
        f.write(render_markdown(ablation_tables))

    if write_csv:
        write_csv_and_markdown(
            baseline_tables,
            csv_path=os.path.join(output_dir, "baseline_table.csv"),
            md_path=os.path.join(output_dir, "baseline_table.md"),
        )
        write_csv_and_markdown(
            ablation_tables,
            csv_path=os.path.join(output_dir, "ablation_table.csv"),
            md_path=os.path.join(output_dir, "ablation_table.md"),
        )

    summary = {
        "n_seeds":           int(seeds),
        "ticks":             int(ticks),
        "faults_per_run":    int(faults_per_run),
        "weather_modes":     list(weather_modes),
        "baseline_labels":   list(baseline_labels),
        "ablation_labels":   list(ablation_labels),
        "n_total_runs":      baseline_report["n_total"]
                              + ablation_report["n_total"],
        "n_valid_runs":      baseline_report["n_valid"]
                              + ablation_report["n_valid"],
        "valid_rate": (
            (baseline_report["n_valid"] + ablation_report["n_valid"])
            / max(1, baseline_report["n_total"] + ablation_report["n_total"])
        ),
        "outputs": {
            "scenarios":     "scenarios.json",
            "baseline_json": "baseline_results.json",
            "baseline_csv":  "baseline_results.csv",
            "baseline_md":   "baseline_table.md",
            "ablation_json": "ablation_results.json",
            "ablation_csv":  "ablation_results.csv",
            "ablation_md":   "ablation_table.md",
            "statistics":    "statistics.json",
            "statistics_md": "statistics.md",
            "manifest":      "manifest.json",
        },
        "baseline_validity": {
            "n_total":   baseline_report["n_total"],
            "n_valid":   baseline_report["n_valid"],
            "n_invalid": baseline_report["n_invalid"],
        },
        "ablation_validity": {
            "n_total":   ablation_report["n_total"],
            "n_valid":   ablation_report["n_valid"],
            "n_invalid": ablation_report["n_invalid"],
        },
    }
    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    return summary


# ── CLI ─────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=3,
                        help="Number of seeds (≥1). Recommended 100 for paper.")
    parser.add_argument("--ticks", type=int, default=50,
                        help="Number of simulation ticks per run.")
    parser.add_argument("--faults", type=int, default=1,
                        help="Number of faults per scenario.")
    parser.add_argument("--weather", default="normal",
                        help="Comma-separated weather modes (normal,high_demand,storm)")
    parser.add_argument("--policies", default=",".join(DEFAULT_BASELINE_LABELS),
                        help="Comma-separated baseline labels.")
    parser.add_argument("--ablation-policies",
                        default=",".join(DEFAULT_ABLATION_LABELS),
                        help="Comma-separated ablation labels.")
    parser.add_argument("--output", default="experiments/results/paper",
                        help="Output directory.")
    parser.add_argument("--no-csv", action="store_true",
                        help="Skip CSV/Markdown writer.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    weather_modes = [w.strip() for w in args.weather.split(",") if w.strip()]
    baseline_labels = [
        p.strip() for p in args.policies.split(",") if p.strip()
    ]
    ablation_labels = [
        p.strip() for p in args.ablation_policies.split(",") if p.strip()
    ]

    summary = run_paper_experiment(
        seeds=args.seeds,
        ticks=args.ticks,
        faults_per_run=args.faults,
        weather_modes=weather_modes,
        baseline_labels=baseline_labels,
        ablation_labels=ablation_labels,
        output_dir=args.output,
        write_csv=not args.no_csv,
    )
    print(f"Output directory: {args.output}")
    print(f"Total runs : {summary['n_total_runs']}")
    print(f"Valid runs : {summary['n_valid_runs']}"
          f" ({summary['valid_rate']*100:.1f} %)")
    print(f"Baseline validity: {summary['baseline_validity']}")
    print(f"Ablation validity: {summary['ablation_validity']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
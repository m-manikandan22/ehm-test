"""paper_experiment.py — Stage 26 one-command paper-grade experiment.

Produces every artefact the paper needs in a single call:

  * ``scenarios.json``            — the seeded scenarios that drove every run
  * ``baseline_results.json`` + ``.csv``
  * ``baseline_table.md``
  * ``ablation_results.json`` + ``.csv``
  * ``ablation_table.md``
  * ``statistics.json`` + ``statistics.md``
  * ``manifest.json`` — environment + provenance manifest
  * ``summary.json``  — top-line counts (n_seeds, n_total_runs, n_valid_runs, valid_rate)

Determinism: every random draw goes through ``utils.seeds.make_rng``;
the scenario generator is deterministic; the controller policies are
deterministic (no random tie-breaking in the rule-based / full_stack
configurations).

Limitations
-----------
* The runner is a *thin* harness — see ``experiments/runner.py``.
* Invalid runs are *excluded* from aggregate statistics (Stage 24).
* No GPU, no distributed run.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Dict, List, Optional

from utils.seeds import make_rng

from experiments.ablation import run_ablation
from experiments.aggregate import per_policy_summary, valid_run_filter
from experiments.experiment_config import ABLATION_CONFIGS, ExperimentConfig
from experiments.runner import run_single
from experiments.scenario import make_scenario
from experiments.tables import build_report, render_markdown
from metrics.statistics import paired_comparison


# Metric keys reported in every CSV row.
_CSV_COLUMNS = (
    "controller_label", "seed", "weather_mode",
    "n_faults", "n_restored", "restoration_rate",
    "avg_restoration_steps", "voltage_violation_count",
    "critical_load_interruption_steps",
    "energy_not_served_mwh",
    "customer_minutes_interrupted",
    "n_steps", "valid",
)


def _git_sha() -> str:
    """Best-effort git SHA. Returns 'UNKNOWN' if not in a git repo."""
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=2,
        )
        return out.decode("ascii", errors="replace").strip()
    except Exception:
        return "UNKNOWN"


def _python_version() -> str:
    return platform.python_version()


def _platform() -> str:
    return platform.platform()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)


def _write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(_CSV_COLUMNS))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in _CSV_COLUMNS})


def _runs_to_csv_rows(runs: List[dict]) -> List[dict]:
    rows = []
    for r in runs:
        m = r.get("metrics") or {}
        v = r.get("validity") or {}
        rows.append({
            "controller_label": r.get("controller_label", ""),
            "seed": r.get("seed", r.get("seed_id", "")),
            "weather_mode": r.get("weather_mode", ""),
            "n_faults": m.get("n_faults", ""),
            "n_restored": m.get("n_restored", ""),
            "restoration_rate": m.get("restoration_rate", ""),
            "avg_restoration_steps": m.get("avg_restoration_steps", ""),
            "voltage_violation_count": m.get("voltage_violation_count", ""),
            "critical_load_interruption_steps":
                m.get("critical_load_interruption_steps", ""),
            "energy_not_served_mwh": m.get("energy_not_served_mwh", ""),
            "customer_minutes_interrupted":
                m.get("total_customer_minutes_interrupted", ""),
            "n_steps": m.get("n_steps", ""),
            "valid": v.get("valid", True),
        })
    return rows


def _run_baseline(
    *,
    seeds: int,
    ticks: int,
    faults_per_run: int,
    weather_modes: List[str],
    baseline_labels: List[str],
) -> List[dict]:
    runs: List[dict] = []
    for seed_id in range(seeds):
        for weather in weather_modes:
            for label in baseline_labels:
                if label not in ABLATION_CONFIGS:
                    continue
                cfg = ABLATION_CONFIGS[label]
                scenario = make_scenario(
                    seed=seed_id, total_steps=ticks,
                    fault_count=faults_per_run, weather_mode=weather,
                )
                result = run_single(config=cfg, scenario=scenario)
                result["seed"] = seed_id
                result["weather_mode"] = weather
                runs.append(result)
    return runs


def _statistics_block(runs: List[dict], anchor_label: str) -> dict:
    """Per-policy summary + paired table (anchor=rule_based)."""
    valid = valid_run_filter(runs)
    per_policy = per_policy_summary(valid)
    tables = build_report(runs=valid, anchor_label=anchor_label)
    return {
        "per_policy": per_policy,
        "paired": tables.get("paired", []),
    }


def run_paper_experiment(
    *,
    seeds: int = 1,
    ticks: int = 50,
    faults_per_run: int = 5,
    weather_modes: Optional[List[str]] = None,
    baseline_labels: Optional[List[str]] = None,
    ablation_labels: Optional[List[str]] = None,
    output_dir: str = "paper_results",
    write_csv: bool = True,
) -> dict:
    """The one-command paper experiment.

    See module docstring for the output schema.
    """
    if weather_modes is None:
        weather_modes = ["normal"]
    if baseline_labels is None:
        baseline_labels = ["random", "rule_based"]
    if ablation_labels is None:
        ablation_labels = list(ABLATION_CONFIGS.keys())

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Generate scenarios
    rng = make_rng(0)
    scenarios: List[dict] = []
    for s in range(seeds):
        for w in weather_modes:
            scen = make_scenario(
                seed=s, total_steps=ticks,
                fault_count=faults_per_run, weather_mode=w,
            )
            d = scen.to_dict()
            d["created_at"] = "synthetic"  # placeholder; deterministic
            d["scenario_seed"] = s
            d["weather_mode"] = w
            scenarios.append(d)

        # The scenarios.json file is a list of dicts so the test helper
    # ``_scenario_faults`` can iterate directly without indirection.
    _write_json(out / "scenarios.json", scenarios)

    # 2. Baseline runs
    baseline_runs = _run_baseline(
        seeds=seeds, ticks=ticks, faults_per_run=faults_per_run,
        weather_modes=weather_modes, baseline_labels=baseline_labels,
    )
    _write_json(out / "baseline_results.json",
                {"runs": baseline_runs, "labels": baseline_labels})
    if write_csv:
        _write_csv(out / "baseline_results.csv",
                   _runs_to_csv_rows(baseline_runs))
    base_tables = build_report(runs=valid_run_filter(baseline_runs),
                                anchor_label="rule_based")
    (out / "baseline_table.md").write_text(
        render_markdown(base_tables, title="Baseline table"), encoding="utf-8",
    )

    # 3. Ablation runs
    ablation_report = run_ablation(
        seeds=seeds, ticks=ticks, faults_per_run=faults_per_run,
        labels=ablation_labels,
    )
    _write_json(out / "ablation_results.json", ablation_report)
    if write_csv:
        abl_rows = []
        for label, pcfg in ablation_report["per_config"].items():
            for metric in pcfg.get("metrics_summary", []):
                abl_rows.append({
                    "controller_label": label,
                    "seed": "",
                    "weather_mode": "",
                    "n_faults": metric.get("n_faults_mean", ""),
                    "n_restored": metric.get("n_restored_mean", ""),
                    "restoration_rate": metric.get("restoration_rate_mean", ""),
                    "avg_restoration_steps":
                        metric.get("avg_restoration_steps_mean", ""),
                    "voltage_violation_count":
                        metric.get("voltage_violation_count_mean", ""),
                    "critical_load_interruption_steps":
                        metric.get("critical_load_interruption_steps_mean", ""),
                    "energy_not_served_mwh":
                        metric.get("energy_not_served_mwh_mean", ""),
                    "customer_minutes_interrupted": "",
                    "n_steps": metric.get("n_steps_mean", ""),
                    "valid": True,
                })
        _write_csv(out / "ablation_results.csv", abl_rows)
    abl_tables = {
        "per_policy": [
            {"controller_label": label, **pcfg.get("metrics_summary", [{}])[0]}
            for label, pcfg in ablation_report["per_config"].items()
        ] if ablation_report["per_config"] else [],
        "paired": [],
    }
    (out / "ablation_table.md").write_text(
        render_markdown(abl_tables, title="Ablation table"),
        encoding="utf-8",
    )

    # 4. Statistics
    statistics = {
        "baseline": _statistics_block(baseline_runs, "rule_based"),
        "ablation": {
            "per_policy": [
                {"controller_label": label,
                 **pcfg.get("metrics_summary", [{}])[0]}
                for label, pcfg in ablation_report["per_config"].items()
            ] if ablation_report["per_config"] else [],
            "paired": [],
        },
    }
    _write_json(out / "statistics.json", statistics)
    (out / "statistics.md").write_text(
        f"# Statistics\n\n"
        f"## Baseline (per-policy)\n\n"
        f"```json\n{json.dumps(statistics['baseline']['per_policy'], indent=2, default=str)}\n```\n\n"
        f"## Ablation (per-policy)\n\n"
        f"```json\n{json.dumps(statistics['ablation']['per_policy'], indent=2, default=str)}\n```\n",
        encoding="utf-8",
    )

    # 5. Manifest
    manifest = {
        "git_sha": _git_sha(),
        "python": _python_version(),
        "platform": _platform(),
        "seeds": int(seeds),
        "ticks": int(ticks),
        "faults_per_run": int(faults_per_run),
        "weather_modes": list(weather_modes),
        "baseline_labels": list(baseline_labels),
        "ablation_labels": list(ablation_labels),
        "n_runs": len(baseline_runs) + ablation_report["n_total_runs"],
    }
    _write_json(out / "manifest.json", manifest)

    # 6. Summary
    all_validity = [r.get("validity", {}).get("valid", True)
                    for r in baseline_runs]
    n_valid = sum(1 for v in all_validity if v)
    summary = {
        "n_seeds": int(seeds),
        "n_total_runs": len(baseline_runs) + ablation_report["n_total_runs"],
        "n_valid_runs": n_valid + ablation_report["n_valid_runs"],
        "valid_rate": (
            (n_valid + ablation_report["n_valid_runs"])
            / max(1, len(baseline_runs) + ablation_report["n_total_runs"])
        ),
    }
    _write_json(out / "summary.json", summary)

    return summary


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="One-command paper-grade experiment runner."
    )
    p.add_argument("--seeds", type=int, default=1)
    p.add_argument("--ticks", type=int, default=50)
    p.add_argument("--faults", type=int, default=5)
    p.add_argument("--output-dir", type=str, default="paper_results")
    p.add_argument("--no-csv", action="store_true",
                   help="Skip CSV outputs.")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    summary = run_paper_experiment(
        seeds=args.seeds, ticks=args.ticks, faults_per_run=args.faults,
        output_dir=args.output_dir, write_csv=not args.no_csv,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
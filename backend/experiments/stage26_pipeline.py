"""stage26_pipeline.py -- Canonical Stage 26 paper-grade driver.

This module produces the exact directory layout specified in
``main.md`` Stage 26::

    <output_dir>/
        raw/             # raw per-run JSON, one file per (policy, seed)
        aggregated/      # aggregated per-policy summary CSV + JSON
        statistics/      # paired-test JSON + Markdown (vs anchor)
        tables/          # TABLE_I..IV Markdown + JSON
        figures/         # PNG/PDF figures
        logs/            # per-step / per-run logs
        manifest.json    # provenance + environment
        summary.md       # human-readable top-line summary

Usage::

    python -m experiments.stage26_pipeline \
        --seeds 10 --ticks 60 --faults 3 \
        --policies random,rule_based,dqn_core_only,full_stack \
        --ablation-policies full_stack,no_lstm,no_twin,no_predictive,no_reward,dqn_core_only \
        --output experiments/results/paper

Stage 37 presets: --stage smoke|medium|final.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import sys
import time
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


_CSV_COLUMNS = (
    "controller_label",
    "seed",
    "weather_mode",
    "n_faults",
    "n_restored",
    "restoration_rate",
    "avg_restoration_steps",
    "actions_taken",
    "illegal_actions_attempted",
    "voltage_violation_count",
    "critical_load_interruption_steps",
    "energy_not_served_mwh",
    "customer_minutes_interrupted",
    "n_steps",
    "valid",
    "invalid_reason",
    "dc_converged",
    "dc_kcl_residual_max",
)


# -------------------------------------------------------------------------
# Provenance helpers
# -------------------------------------------------------------------------

def _git_sha() -> str:
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


def _platform_str() -> str:
    return platform.platform()


def _dependency_versions() -> Dict[str, str]:
    deps: Dict[str, str] = {}
    for pkg in ("numpy", "scipy", "networkx", "pandas", "torch", "matplotlib"):
        try:
            mod = __import__(pkg)
            deps[pkg] = getattr(mod, "__version__", "?")
        except Exception:
            deps[pkg] = "missing"
    return deps


# -------------------------------------------------------------------------
# JSON / CSV writers
# -------------------------------------------------------------------------

def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)


def _runs_to_csv_rows(runs: List[dict]) -> List[dict]:
    rows = []
    for r in runs:
        m = r.get("metrics") or {}
        v = r.get("validity") or {}
        pf = r.get("pf_diagnostic") or {}
        rows.append({
            "controller_label": r.get("controller_label", ""),
            "seed": r.get("seed", r.get("seed_id", "")),
            "weather_mode": r.get("weather_mode", ""),
            "n_faults": m.get("n_faults", ""),
            "n_restored": m.get("n_restored", ""),
            "restoration_rate": m.get("restoration_rate", ""),
            "avg_restoration_steps": m.get("avg_restoration_steps", ""),
            "actions_taken": m.get("actions_taken", ""),
            "illegal_actions_attempted": m.get("illegal_actions_attempted", ""),
            "voltage_violation_count": m.get("voltage_violation_count", ""),
            "critical_load_interruption_steps": m.get(
                "critical_load_interruption_steps", ""
            ),
            "energy_not_served_mwh": m.get("energy_not_served_mwh", ""),
            "customer_minutes_interrupted": m.get(
                "total_customer_minutes_interrupted", ""
            ),
            "n_steps": m.get("n_steps", ""),
            "valid": v.get("valid", True),
            "invalid_reason": v.get("invalid_reason", ""),
            "dc_converged": pf.get("dc_converged", ""),
            "dc_kcl_residual_max": pf.get("dc_kcl_residual_max", ""),
        })
    return rows


def _write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(_CSV_COLUMNS))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in _CSV_COLUMNS})


# -------------------------------------------------------------------------
# Layout writers
# -------------------------------------------------------------------------

def _write_raw(raw_dir: Path, runs: List[dict]) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for r in runs:
        label = r.get("controller_label", "?")
        seed = r.get("seed", r.get("seed_id", 0))
        _write_json(raw_dir / f"{label}__seed{seed}.json", r)


def _write_aggregated(agg_dir: Path, runs: List[dict]) -> None:
    agg_dir.mkdir(parents=True, exist_ok=True)
    summary = per_policy_summary(valid_run_filter(runs))
    _write_json(agg_dir / "per_policy_summary.json", summary)
    rows = []
    for r in summary:
        flat = {"controller_label": r.get("controller_label", "")}
        for k, v in r.items():
            if k == "controller_label":
                continue
            if isinstance(v, (int, float, str)):
                flat[k] = v
        rows.append(flat)
    if rows:
        with open(agg_dir / "per_policy_summary.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)


def _write_statistics(
    stats_dir: Path,
    runs: List[dict],
    *,
    anchor_label: str = "rule_based",
) -> None:
    stats_dir.mkdir(parents=True, exist_ok=True)
    valid = valid_run_filter(runs)
    tables = build_report(runs=valid, anchor_label=anchor_label)
    _write_json(stats_dir / "paired.json", tables)
    (stats_dir / "paired.md").write_text(
        render_markdown(tables, title=f"Paired comparison vs `{anchor_label}`"),
        encoding="utf-8",
    )
    # Extended paired report with Wilcoxon, Cohen's d, BH correction
    try:
        from collections import defaultdict
        from metrics.statistics import paired_test_report
        by_label: Dict[str, list] = defaultdict(list)
        for r in valid:
            by_label[r.get("controller_label", "?")].append(r)
        metrics = (
            "energy_not_served_mwh",
            "critical_load_interruption_steps",
            "total_customer_minutes_interrupted",
            "restoration_rate",
            "n_restored",
        )
        comparisons = []
        for metric in metrics:
            a_vals = [r["metrics"].get(metric, 0)
                      for r in by_label.get(anchor_label, [])]
            a_vals = [v for v in a_vals if v is not None]
            for label, bucket in sorted(by_label.items()):
                if label == anchor_label:
                    continue
                b_vals = [r["metrics"].get(metric, 0) for r in bucket]
                b_vals = [v for v in b_vals if v is not None]
                n = min(len(a_vals), len(b_vals))
                if n < 2:
                    continue
                comparisons.append(
                    (a_vals[:n], b_vals[:n],
                     f"{metric}: {label} vs {anchor_label}")
                )
        if comparisons:
            ext = paired_test_report(comparisons, correction="bh",
                                      alpha=0.05)
            _write_json(stats_dir / "paired_full.json", ext)
    except Exception as exc:
        (stats_dir / "paired_full_error.txt").write_text(
            str(exc), encoding="utf-8",
        )


def _write_tables(
    tables_dir: Path,
    runs: List[dict],
    ablation_report: Optional[dict] = None,
) -> None:
    tables_dir.mkdir(parents=True, exist_ok=True)
    valid = valid_run_filter(runs)
    tables = build_report(runs=valid, anchor_label="rule_based")
    (tables_dir / "TABLE_III_baseline.md").write_text(
        render_markdown(tables, title="TABLE III -- Baseline comparison"),
        encoding="utf-8",
    )

    bench = {
        "primary": {
            "name": "EHM 49-node distribution test feeder",
            "buses": 49,
            "source_bus": "GEN_SOLAR / GEN_WIND / GEN_NUCLEAR / GEN_COAL / GEN_GAS",
            "tie_switches": "see backend/simulation/grid.py",
        },
        "second_benchmark": {
            "name": "IEEE 33-bus test feeder",
            "buses": 33,
            "lines": 37,
            "tie_switches": 5,
            "total_load_kw": 3715,
            "total_load_kvar": 2300,
            "source_bus": "1",
            "voltage_base_kv": 12.66,
            "reference": "Baran & Wu 1989; IEEE PES Distribution System Analysis Subcommittee 1992",
        },
    }
    _write_json(tables_dir / "TABLE_II_benchmark_config.json", bench)

    sys_cfg = {
        "framework": "EHM v3 (Existing Hybrid Microgrid self-healing pipeline)",
        "modules": [
            "Resilience-aware topology planner",
            "Renewable (solar + wind) generation",
            "Hybrid battery + supercapacitor storage",
            "LSTM demand forecaster",
            "Digital twin (Arrhenius ageing)",
            "DQN controller with train/eval separation",
            "FLISR 9-stage pipeline",
            "DC power-flow (KCL-residual-checked) validator",
            "IEEE 1366 reliability metrics",
        ],
        "controllers": sorted({r.get("controller_label", "") for r in runs}),
        "seeds_per_run": max((int(r.get("seed", 0)) for r in runs), default=0) + 1,
    }
    _write_json(tables_dir / "TABLE_I_system_config.json", sys_cfg)

    if ablation_report:
        _write_json(tables_dir / "TABLE_IV_ablation.json", ablation_report)
        abl_md = ["# Ablation Table (Table IV)\n",
                  "| label | n_valid | restoration_rate_mean | restoration_rate_std "
                  "| ENS_mean | ENS_std |\n",
                  "| ----- | ------- | -------------------- | ------------------ "
                  "| -------- | ------- |\n"]
        for label, pcfg in ablation_report.get("per_config", {}).items():
            ms = pcfg.get("metrics_summary", [{}])
            if not ms:
                continue
            row = ms[0]
            abl_md.append(
                f"| {label} | {pcfg.get('n_valid_runs', '?')} "
                f"| {row.get('restoration_rate_mean', '?')} "
                f"| {row.get('restoration_rate_std', '?')} "
                f"| {row.get('energy_not_served_mwh_mean', '?')} "
                f"| {row.get('energy_not_served_mwh_std', '?')} |"
            )
        (tables_dir / "TABLE_IV_ablation.md").write_text(
            "\n".join(abl_md) + "\n", encoding="utf-8",
        )


def _write_figures(figs_dir: Path, runs: List[dict]) -> List[Path]:
    figs_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    try:
        from experiments.figures import baseline_bar_chart  # noqa
    except Exception as exc:
        (figs_dir / "FIGURES_NOT_GENERATED.txt").write_text(
            f"Figures skipped because figures module is unavailable: {exc}\n",
            encoding="utf-8",
        )
        return written
    try:
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt  # noqa
    except Exception as exc:
        (figs_dir / "FIGURES_NOT_GENERATED.txt").write_text(
            f"Figures skipped because matplotlib is unavailable: {exc}\n",
            encoding="utf-8",
        )
        return written
    valid = valid_run_filter(runs)
    summary_list = per_policy_summary(valid)
    # Convert list of dicts to dict keyed by controller_label.
    # Flatten "{key}_mean" suffixed fields back to bare names so
    # ``baseline_bar_chart`` can find them.
    summary_dict = {}
    for row in summary_list:
        flat = {"controller_label": row.get("controller_label", "?")}
        for k, v in row.items():
            if k == "controller_label":
                continue
            if k.endswith("_mean"):
                flat[k[:-5]] = v
            elif k.endswith("_std"):
                flat[k[:-4] + "_std"] = v
            else:
                flat[k] = v
        summary_dict[row.get("controller_label", "?")] = flat
    try:
        # Pick the first numeric metric that's present in every row.
        candidate = None
        for key in ("restoration_rate", "n_restored", "n_faults",
                    "energy_not_served_mwh", "voltage_violation_count"):
            if all(key in row and row[key] is not None
                   for row in summary_dict.values()):
                candidate = key
                break
        if candidate is None:
            raise ValueError("no common numeric metric across policies")
        fig = baseline_bar_chart(summary_dict, metric=candidate)
        path = figs_dir / f"fig4_baseline_{candidate}.png"
        fig.savefig(path, dpi=160, bbox_inches="tight")
        plt.close(fig)
        written.append(path)
    except Exception as exc:
        (figs_dir / "fig4_error.txt").write_text(str(exc), encoding="utf-8")
    return written


def _write_logs(logs_dir: Path, runs: List[dict]) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for r in runs:
        label = r.get("controller_label", "?")
        seed = r.get("seed", 0)
        m = r.get("metrics", {})
        v = r.get("validity", {})
        pf = r.get("pf_diagnostic", {})
        lines.append(
            f"[{label:>13s}] seed={seed:>3d}  "
            f"valid={v.get('valid', True)}  "
            f"reason={v.get('invalid_reason', '')}  "
            f"restoration_rate={m.get('restoration_rate', '')}  "
            f"ENS={m.get('energy_not_served_mwh', '')}  "
            f"dc_converged={pf.get('dc_converged', '')}"
        )
    (logs_dir / "run_summary.log").write_text(
        "\n".join(lines) + "\n", encoding="utf-8",
    )


# -------------------------------------------------------------------------
# Top-level orchestration
# -------------------------------------------------------------------------

def run_stage26(
    *,
    seeds: int,
    ticks: int,
    faults: int,
    policies: List[str],
    ablation_policies: List[str],
    output_dir: str,
    weather_modes: Optional[List[str]] = None,
    skip_figures: bool = False,
) -> Dict:
    if weather_modes is None:
        weather_modes = ["normal"]
    out = Path(output_dir)
    raw_dir = out / "raw"
    agg_dir = out / "aggregated"
    stats_dir = out / "statistics"
    tables_dir = out / "tables"
    figs_dir = out / "figures"
    logs_dir = out / "logs"
    for d in (raw_dir, agg_dir, stats_dir, tables_dir, figs_dir, logs_dir):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Scenarios
    scenarios: List[dict] = []
    for s in range(seeds):
        for w in weather_modes:
            scen = make_scenario(
                seed=s, total_steps=ticks,
                fault_count=faults, weather_mode=w,
            )
            d = scen.to_dict()
            d["scenario_seed"] = s
            d["weather_mode"] = w
            scenarios.append(d)
    _write_json(out / "scenarios.json", scenarios)

    # 2. Runs
    t0 = time.time()
    runs: List[dict] = []
    n_attempted = 0
    for seed_id in range(seeds):
        for weather in weather_modes:
            scen = make_scenario(
                seed=seed_id, total_steps=ticks,
                fault_count=faults, weather_mode=weather,
            )
            for label in policies:
                if label not in ABLATION_CONFIGS:
                    continue
                cfg = ABLATION_CONFIGS[label]
                n_attempted += 1
                result = run_single(
                    config=cfg, scenario=scen, run_seed=seed_id,
                )
                result["seed"] = seed_id
                result["seed_id"] = seed_id
                result["weather_mode"] = weather
                runs.append(result)
    runtime_seconds = time.time() - t0

    # 3. Layout
    _write_raw(raw_dir, runs)
    _write_aggregated(agg_dir, runs)
    _write_statistics(stats_dir, runs, anchor_label="rule_based")

    # Ablation runs
    ablation_report = run_ablation(
        seeds=seeds, ticks=ticks, faults_per_run=faults,
        labels=ablation_policies,
    )
    _write_tables(tables_dir, runs, ablation_report=ablation_report)
    if not skip_figures:
        _write_figures(figs_dir, runs)
    _write_logs(logs_dir, runs)

    n_valid = sum(1 for r in runs if r.get("validity", {}).get("valid", True))
    n_invalid = len(runs) - n_valid
    manifest = {
        "git_sha": _git_sha(),
        "python": _python_version(),
        "platform": _platform_str(),
        "dependencies": _dependency_versions(),
        "seeds": int(seeds),
        "ticks": int(ticks),
        "faults_per_run": int(faults),
        "weather_modes": list(weather_modes),
        "policies": list(policies),
        "ablation_policies": list(ablation_policies),
        "n_runs_attempted": n_attempted,
        "n_runs_valid": n_valid,
        "n_runs_invalid": n_invalid,
        "invalid_rate": n_invalid / max(1, n_attempted),
        "runtime_seconds": runtime_seconds,
        "ablation": {
            "n_total_runs": ablation_report.get("n_total_runs", 0),
            "n_valid_runs":  ablation_report.get("n_valid_runs", 0),
        },
        "output_layout": {
            "raw/":         "one JSON per (policy, seed)",
            "aggregated/":  "per-policy summary CSV + JSON",
            "statistics/":  "paired comparison JSON + Markdown",
            "tables/":      "TABLE_I, II, III, IV Markdown + JSON",
            "figures/":     "PNG figures (or stub if matplotlib missing)",
            "logs/":        "per-run summary log",
            "manifest.json": "this file",
            "summary.md":   "human-readable top-line summary",
        },
    }
    _write_json(out / "manifest.json", manifest)

    summary_lines = [
        "# Paper Experiment Summary (Stage 26)",
        "",
        f"**Seeds:** {seeds}    **Ticks:** {ticks}    "
        f"**Faults/run:** {faults}    **Policies:** {len(policies)}    "
        f"**Ablation labels:** {len(ablation_policies)}",
        "",
        f"**Runs attempted:** {n_attempted}    "
        f"**Valid:** {n_valid}    **Invalid:** {n_invalid}    "
        f"**Invalid rate:** {manifest['invalid_rate']:.2%}",
        "",
        f"**Runtime:** {runtime_seconds:.1f}s "
        f"(~ {runtime_seconds / max(1, n_attempted):.2f}s / run)",
        "",
        "## Layout",
        "",
        "* raw/         -- per-(policy, seed) JSON",
        "* aggregated/  -- per-policy summary CSV + JSON",
        "* statistics/  -- paired comparison JSON + Markdown",
        "* tables/      -- TABLE_I..IV Markdown + JSON",
        "* figures/     -- PNG figures (or stub if matplotlib missing)",
        "* logs/        -- per-run summary log",
        "* manifest.json -- environment, dependencies, provenance",
        "* summary.md    -- this file",
        "",
        "## Manifest",
        "",
        f"* git_sha: `{manifest['git_sha']}`",
        f"* python: `{manifest['python']}`",
        f"* platform: `{manifest['platform']}`",
        f"* dependencies: `{json.dumps(manifest['dependencies'])}`",
        "",
        "## Honest framing",
        "",
        "* Simulation-only (no field validation).",
        "* Synthetic demand / weather / fault scenarios (deterministic).",
        "* Round-trip efficiency and voltage are DC-PF proxies.",
        "* Full results in tables/TABLE_III_baseline.md and TABLE_IV_ablation.md.",
        "",
    ]
    (out / "summary.md").write_text(
        "\n".join(summary_lines), encoding="utf-8",
    )

    return {
        "n_attempted": n_attempted,
        "n_valid": n_valid,
        "n_invalid": n_invalid,
        "runtime_seconds": runtime_seconds,
        "output_dir": str(out),
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Stage 26 paper-grade experiment (canonical layout).",
    )
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--ticks", type=int, default=60)
    p.add_argument("--faults", type=int, default=3)
    p.add_argument(
        "--policies", type=str,
        default="random,rule_based,dqn_core_only,full_stack",
    )
    p.add_argument(
        "--ablation-policies", type=str,
        default=("full_stack,no_lstm,no_twin,no_predictive,no_reward,"
                 "dqn_core_only"),
    )
    p.add_argument("--weather-modes", type=str, default="normal")
    p.add_argument("--output", type=str, default="experiments/results/paper")
    p.add_argument("--no-figures", action="store_true")
    p.add_argument(
        "--stage", type=str,
        choices=("smoke", "medium", "final"),
        default="final",
    )
    args = p.parse_args(argv if argv is not None else sys.argv[1:])

    if args.stage == "smoke":
        seeds, ticks, faults = 2, 20, 1
    elif args.stage == "medium":
        seeds, ticks, faults = min(args.seeds, 5), min(args.ticks, 40), min(args.faults, 2)
    else:
        seeds, ticks, faults = args.seeds, args.ticks, args.faults

    policies = [p.strip() for p in args.policies.split(",") if p.strip()]
    ablation_policies = [
        p.strip() for p in args.ablation_policies.split(",") if p.strip()
    ]
    weather_modes = [w.strip() for w in args.weather_modes.split(",") if w.strip()]

    summary = run_stage26(
        seeds=seeds, ticks=ticks, faults=faults,
        policies=policies, ablation_policies=ablation_policies,
        output_dir=args.output, weather_modes=weather_modes,
        skip_figures=args.no_figures,
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

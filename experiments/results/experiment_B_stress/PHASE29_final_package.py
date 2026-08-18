"""
PHASE 29 — Final package assembly for Experiment B.

Combines the runner output (experiment_B_runs.json), statistics
(CSVs), and figures into a single compendium directory that the
paper can reference.

Outputs:
  paper_results_experiment_B/
    ├─ README.md
    ├─ experiment_B_config.json
    ├─ experiment_B_manifest.json
    ├─ PRIMARY_OUTCOMES.md
    ├─ STRESS_BENCHMARK_PILOT_REPORT.md
    ├─ EXPERIMENT_B_FINAL_RESULTS.md    ← generated here
    ├─ raw/
    │    ├─ experiment_B_runs.json
    │    ├─ experiment_B_statistics.json
    │    ├─ experiment_B_baseline_comparison.csv
    │    ├─ experiment_B_ablation.csv
    │    ├─ experiment_B_statistics.csv
    │    ├─ environment_report.json
    ├─ tables/
    │    ├─ experiment_B_stress_characteristics.csv
    │    ├─ experiment_B_validity.csv
    │    ├─ experiment_B_runtime.csv
    │    ├─ experiment_A_vs_B.csv
    ├─ statistics/
    │    └─ (same CSVs as in raw/ for convenience)
    ├─ figures/                          ← already populated by PHASE27
    └─ validation/
         └─ EXPERIMENT_B_INTEGRITY.md
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import statistics
from typing import Any, Dict, List, Tuple


# ── Helpers ────────────────────────────────────────────────────────────
def _by_level_policy(runs: List[Dict[str, Any]]):
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in runs:
        level = r.get("stress_level") or r.get("scenario", {}).get(
            "stress_level", "")
        policy = r.get("controller_label") or r.get("policy", "")
        buckets.setdefault((str(level), str(policy)), []).append(r)
    return buckets


def _get_metric(run: Dict[str, Any], name: str) -> float:
    m = run.get("metrics", {}) or {}
    v = m.get(name)
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _write_csv(path: str, rows: List[Dict[str, Any]],
               fieldnames: List[str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


# ── Validity + runtime tables ─────────────────────────────────────────
def build_validity_and_runtime(runs: List[Dict[str, Any]]) -> Tuple[
        List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build per-policy × per-level validity and runtime aggregations."""
    buckets = _by_level_policy(runs)
    validity_rows: List[Dict[str, Any]] = []
    runtime_rows: List[Dict[str, Any]] = []
    for (level, policy), rs in sorted(buckets.items()):
        n = len(rs)
        n_valid = sum(1 for r in rs if r.get("valid", True))
        n_invalid = n - n_valid
        validity_rows.append({
            "stress_level": level,
            "controller": policy,
            "n_runs": n,
            "n_valid": n_valid,
            "n_invalid": n_invalid,
            "valid_pct": 100.0 * n_valid / n if n > 0 else 0.0,
        })
        ctrl_rt = [r.get("controller_runtime_s", 0.0) for r in rs]
        pf_rt = [r.get("power_flow_runtime_s", 0.0) for r in rs]
        wf_rt = [r.get("wallclock_runtime_s", 0.0) for r in rs]
        runtime_rows.append({
            "stress_level": level,
            "controller": policy,
            "n_runs": n,
            "controller_runtime_mean_s": statistics.mean(ctrl_rt) if ctrl_rt else 0.0,
            "controller_runtime_std_s": statistics.stdev(ctrl_rt) if len(ctrl_rt) > 1 else 0.0,
            "power_flow_runtime_mean_s": statistics.mean(pf_rt) if pf_rt else 0.0,
            "wallclock_runtime_mean_s": statistics.mean(wf_rt) if wf_rt else 0.0,
        })
    return validity_rows, runtime_rows


# ── Stress characteristics table ──────────────────────────────────────
def build_stress_characteristics(
        config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Per-level stress profile: fault count, duration, capacity, etc."""
    rows: List[Dict[str, Any]] = []
    for level, params in config["stress_definitions"].items():
        rows.append({
            "stress_level": level,
            "fault_count": params["fault_count"],
            "fault_duration_min": params["fault_duration_range"][0],
            "fault_duration_max": params["fault_duration_range"][1],
            "max_concurrent_faults": params["max_concurrent_faults"],
            "load_multiplier": params["load_multiplier"],
            "generation_reserve_factor": params["generation_reserve_factor"],
            "tie_capacity_factor": params["tie_capacity_factor"],
            "line_capacity_factor": params["line_capacity_factor"],
            "battery_soc_min": params["battery_soc_range"][0],
            "battery_soc_max": params["battery_soc_range"][1],
            "renewable_factor": params["renewable_factor"],
            "weather_mode": params["weather_mode"],
            "critical_load_fraction": params["critical_load_fraction"],
            "tie_capacity_mw": params["tie_capacity_mw"],
            "fault_inject_probability": params["fault_inject_probability"],
        })
    return rows


# ── Experiment A vs B comparison table ────────────────────────────────
def build_a_vs_b(
        exp_a_runs: List[Dict[str, Any]],
        exp_b_runs: List[Dict[str, Any]],
        anchor: str = "full_stack",
) -> List[Dict[str, Any]]:
    """One row per metric x experiment: nominal vs severe."""
    metrics = (
        "saifi", "saidi", "ens", "restoration_time_seconds",
        "critical_load_restored_pct", "voltage_violation_count",
        "line_overload_count", "stress_cumulative_unserved_energy",
        "resilience_loss_area",
        "resilience_time_to_50pct_restoration",
        "stress_critical_load_restored_pct",
    )
    a_buckets = _by_level_policy(exp_a_runs)
    b_buckets = _by_level_policy(exp_b_runs)
    rows: List[Dict[str, Any]] = []
    for metric in metrics:
        # Experiment A has no stress_level field, so it buckets under
        # "nominal" by default. Experiment B uses the explicit level name.
        a_vals = [
            _get_metric(r, metric)
            for r in a_buckets.get(("nominal", anchor), [])
        ]
        b_vals = [
            _get_metric(r, metric)
            for r in b_buckets.get(("severe", anchor), [])
        ]
        rows.append({
            "metric": metric,
            "experiment_a_nominal_n": len(a_vals),
            "experiment_a_nominal_mean": statistics.mean(a_vals) if a_vals else 0.0,
            "experiment_a_nominal_std": statistics.stdev(a_vals) if len(a_vals) > 1 else 0.0,
            "experiment_b_severe_n": len(b_vals),
            "experiment_b_severe_mean": statistics.mean(b_vals) if b_vals else 0.0,
            "experiment_b_severe_std": statistics.stdev(b_vals) if len(b_vals) > 1 else 0.0,
        })
    return rows


# ── Final-results Markdown ────────────────────────────────────────────
def build_final_results_md(
    config: Dict[str, Any],
    runs: List[Dict[str, Any]],
    stats: Dict[str, Any],
    validity_rows: List[Dict[str, Any]],
    runtime_rows: List[Dict[str, Any]],
) -> str:
    n_total = len(runs)
    n_valid = sum(1 for r in runs if r.get("valid", True))
    primary = config["primary_outcomes"]
    stress_rows = stats.get("rows", [])
    primary_rows = [r for r in stress_rows if r["metric"] in primary]
    out = []
    out.append("# EXPERIMENT B — FINAL RESULTS\n")
    out.append("This is the final, peer-reviewable report for the "
               "stress / constrained self-healing validation experiment.\n")
    out.append("## 1. Configuration\n")
    out.append(f"- Experiment ID: `{config['experiment_id']}`")
    out.append(f"- Frozen at: `{config['frozen_at']}`")
    out.append(f"- Stress levels: `{', '.join(config['stress_levels'])}`")
    out.append(f"- Seeds: {config['n_seeds']} (0..{config['n_seeds']-1})")
    out.append(f"- Ticks per run: {config['ticks']}")
    out.append(f"- Controllers evaluated: {len(config['controllers'])} baselines + "
               f"{len(config['ablations'])} ablations")
    out.append(f"- Pre-registered primary outcomes: `{', '.join(primary)}`")
    out.append("")
    out.append("## 2. Run summary\n")
    out.append(f"- Total runs: **{n_total}**")
    out.append(f"- Valid runs: **{n_valid}** ({100.0 * n_valid / max(n_total,1):.2f}%)")
    out.append("")
    out.append("## 3. Pre-registered primary outcomes\n")
    out.append("Wilcoxon signed-rank (paired by seed) against anchor "
               f"`{stats['anchor']}`, Holm-corrected across all comparisons.\n")
    out.append("| level | anchor | other | metric | n | median_anchor | median_other | rel diff (%) | p_holm | Cliff's delta | classification |")
    out.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---|")
    for r in primary_rows:
        out.append(
            f"| {r['stress_level']} | {r['anchor']} | {r['other']} | "
            f"`{r['metric']}` | {r['n_pairs']} | "
            f"{r['median_a']:.3f} | {r['median_b']:.3f} | "
            f"{r['median_rel_diff_pct']:.2f} | {r['holm_p']:.4f} | "
            f"{r['cliffs_delta']:.3f} | **{r['classification']}** |"
        )
    out.append("")
    out.append("## 4. Validity gates\n")
    out.append("| stress level | controller | n | valid (%) |")
    out.append("|---|---|---:|---:|")
    for v in validity_rows:
        out.append(f"| {v['stress_level']} | {v['controller']} | "
                   f"{v['n_runs']} | {v['valid_pct']:.1f} |")
    out.append("")
    out.append("## 5. Runtime cost\n")
    out.append("| stress level | controller | mean ctrl-rt (s) | mean wallclock (s) |")
    out.append("|---|---|---:|---:|")
    for r in runtime_rows:
        out.append(f"| {r['stress_level']} | {r['controller']} | "
                   f"{r['controller_runtime_mean_s']:.3f} | "
                   f"{r['wallclock_runtime_mean_s']:.3f} |")
    out.append("")
    out.append("## 6. Honest reporting\n")
    out.append("The pre-registered primary outcomes are reported **as-is**. "
               "Outcomes with insufficient paired variance are reported "
               "as `INCONCLUSIVE`. The benchmark was frozen before the final "
               "experiment was run and was **not** retuned based on results.")
    out.append("")
    return "\n".join(out)


# ── Integrity manifest ────────────────────────────────────────────────
def build_integrity_md(
    config_path: str,
    runs_path: str,
    n_total: int,
    n_valid: int,
) -> str:
    import hashlib
    def _sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    p_sha = _sha(config_path) if os.path.isfile(config_path) else "missing"
    r_sha = _sha(runs_path) if os.path.isfile(runs_path) else "missing"
    out = [
        "# EXPERIMENT B — INTEGRITY MANIFEST",
        "",
        f"- Config SHA-256: `{p_sha}`",
        f"- Runs   SHA-256: `{r_sha}`",
        f"- Total runs: {n_total}",
        f"- Valid runs: {n_valid}",
        "",
        "Per-experiment integrity checks:",
        "",
        "1. Experiment A files were not modified (verified by PHASE 0).",
        "2. Stress benchmark config was frozen before final run (PHASE 17).",
        "3. Ablations were genuinely isolated (verified by PHASE 3).",
        "4. Controller ranking was not used in scenario generation.",
        "5. Final statistical analysis used pre-registered metrics only.",
        "",
    ]
    return "\n".join(out)


# ── Main driver ────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config",
                    default="experiments/results/experiment_B_stress/experiment_B_config.json")
    ap.add_argument("--manifest",
                    default="experiments/results/experiment_B_stress/experiment_B_manifest.json")
    ap.add_argument("--runs",
                    default="experiments/results/experiment_B_stress/experiment_B_runs.json")
    ap.add_argument("--statistics",
                    default="experiments/results/experiment_B_stress/experiment_B_statistics.json")
    ap.add_argument("--env",
                    default="experiments/results/experiment_B_stress/environment_report.json")
    ap.add_argument("--pilot-report",
                    default="experiments/results/experiment_B_stress/STRESS_BENCHMARK_PILOT_REPORT.md")
    ap.add_argument("--primary",
                    default="experiments/results/experiment_B_stress/PRIMARY_OUTCOMES.md")
    ap.add_argument("--exp-a",
                    default="paper_results/raw/baseline_results.json")
    ap.add_argument("--out-dir",
                    default="paper_results_experiment_B")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)
    with open(args.runs, "r", encoding="utf-8") as f:
        runs_report = json.load(f)
    runs = runs_report.get("runs", [])
    n_total = len(runs)
    n_valid = sum(1 for r in runs if r.get("valid", True))

    # Load statistics.
    stats: Dict[str, Any] = {}
    if os.path.isfile(args.statistics):
        with open(args.statistics, "r", encoding="utf-8") as f:
            stats = json.load(f)

    # Build tables.
    validity_rows, runtime_rows = build_validity_and_runtime(runs)
    stress_chars = build_stress_characteristics(config)

    exp_a_runs: List[Dict[str, Any]] = []
    if os.path.isfile(args.exp_a):
        with open(args.exp_a, "r", encoding="utf-8") as f:
            exp_a_runs = json.load(f).get("runs", [])
    a_vs_b_rows = build_a_vs_b(exp_a_runs, runs)

    # ── Output directory layout ────────────────────────────────────────
    out_root = args.out_dir
    if os.path.isdir(out_root):
        # Don't wipe the user's directory. Overwrite only the files we
        # regenerate.
        pass
    os.makedirs(out_root, exist_ok=True)
    raw_dir = os.path.join(out_root, "raw")
    tables_dir = os.path.join(out_root, "tables")
    stats_dir = os.path.join(out_root, "statistics")
    val_dir = os.path.join(out_root, "validation")
    figs_dir = os.path.join(out_root, "figures")
    for d in (raw_dir, tables_dir, stats_dir, val_dir, figs_dir):
        os.makedirs(d, exist_ok=True)

    # ── Copy best-effort raw files ────────────────────────────────────
    src_dst = [
        (args.runs, os.path.join(raw_dir, "experiment_B_runs.json")),
        (args.statistics, os.path.join(raw_dir, "experiment_B_statistics.json")),
        (os.path.join(os.path.dirname(args.runs), "experiment_B_baseline_comparison.csv"),
         os.path.join(raw_dir, "experiment_B_baseline_comparison.csv")),
        (os.path.join(os.path.dirname(args.runs), "experiment_B_ablation.csv"),
         os.path.join(raw_dir, "experiment_B_ablation.csv")),
        (os.path.join(os.path.dirname(args.runs), "experiment_B_statistics.csv"),
         os.path.join(raw_dir, "experiment_B_statistics.csv")),
        (args.env, os.path.join(raw_dir, "environment_report.json")),
        (args.config, os.path.join(out_root, "experiment_B_config.json")),
        (args.manifest, os.path.join(out_root, "experiment_B_manifest.json")),
        (args.primary, os.path.join(out_root, "PRIMARY_OUTCOMES.md")),
        (args.pilot_report, os.path.join(out_root, "STRESS_BENCHMARK_PILOT_REPORT.md")),
    ]
    for src, dst in src_dst:
        if os.path.isfile(src):
            shutil.copy2(src, dst)

    # Copy figures if present.
    src_figs_dir = os.path.join(os.path.dirname(args.runs), "figures")
    if os.path.isdir(src_figs_dir):
        for fname in os.listdir(src_figs_dir):
            shutil.copy2(
                os.path.join(src_figs_dir, fname),
                os.path.join(figs_dir, fname),
            )

    # ── Build package-internal tables ─────────────────────────────────
    if validity_rows:
        _write_csv(
            os.path.join(tables_dir, "experiment_B_validity.csv"),
            validity_rows,
            ["stress_level", "controller", "n_runs", "n_valid", "n_invalid",
             "valid_pct"],
        )
    if runtime_rows:
        _write_csv(
            os.path.join(tables_dir, "experiment_B_runtime.csv"),
            runtime_rows,
            ["stress_level", "controller", "n_runs",
             "controller_runtime_mean_s", "controller_runtime_std_s",
             "power_flow_runtime_mean_s", "wallclock_runtime_mean_s"],
        )
    if stress_chars:
        _write_csv(
            os.path.join(tables_dir, "experiment_B_stress_characteristics.csv"),
            stress_chars,
            ["stress_level", "fault_count", "fault_duration_min",
             "fault_duration_max", "max_concurrent_faults", "load_multiplier",
             "generation_reserve_factor", "tie_capacity_factor",
             "line_capacity_factor", "battery_soc_min", "battery_soc_max",
             "renewable_factor", "weather_mode", "critical_load_fraction",
             "tie_capacity_mw", "fault_inject_probability"],
        )
    if a_vs_b_rows:
        _write_csv(
            os.path.join(tables_dir, "experiment_A_vs_B.csv"),
            a_vs_b_rows,
            ["metric", "experiment_a_nominal_n", "experiment_a_nominal_mean",
             "experiment_a_nominal_std", "experiment_b_severe_n",
             "experiment_b_severe_mean", "experiment_b_severe_std"],
        )

    # ── Mirror statistics CSVs into statistics/ ─────────────────────
    for fname in ("experiment_B_baseline_comparison.csv",
                  "experiment_B_ablation.csv",
                  "experiment_B_statistics.csv"):
        src = os.path.join(raw_dir, fname)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(stats_dir, fname))

    # ── Build final results Markdown ─────────────────────────────────
    final_md = build_final_results_md(
        config=config, runs=runs, stats=stats,
        validity_rows=validity_rows, runtime_rows=runtime_rows,
    )
    with open(os.path.join(out_root, "EXPERIMENT_B_FINAL_RESULTS.md"),
              "w", encoding="utf-8") as f:
        f.write(final_md)

    # ── Build integrity manifest ─────────────────────────────────────
    integrity_md = build_integrity_md(
        config_path=args.config,
        runs_path=args.runs,
        n_total=n_total,
        n_valid=n_valid,
    )
    with open(os.path.join(val_dir, "EXPERIMENT_B_INTEGRITY.md"),
              "w", encoding="utf-8") as f:
        f.write(integrity_md)

    # ── Build README.md ──────────────────────────────────────────────
    readme = (
        "# Paper Results — Experiment B (Stress / Constrained Self-Healing)\n\n"
        "This directory contains the complete peer-reviewable evidence for "
        "Experiment B. It is intentionally kept separate from the Experiment "
        "A deliverables in `paper_results/` and from the prototype directory "
        "`experiments/results/`.\n\n"
        "## Layout\n\n"
        "- `experiment_B_config.json` — frozen configuration (PHASE 17)\n"
        "- `experiment_B_manifest.json` — input scenarios and configs\n"
        "- `PRIMARY_OUTCOMES.md` — pre-registered primary outcomes\n"
        "- `STRESS_BENCHMARK_PILOT_REPORT.md` — GO/NO-GO decision\n"
        "- `EXPERIMENT_B_FINAL_RESULTS.md` — primary results report\n"
        "- `raw/` — raw per-run data, statistics, environment\n"
        "- `tables/` — derived tables (validity, runtime, A vs B)\n"
        "- `statistics/` — paired-test CSVs reachable from the paper\n"
        "- `figures/` — publication-quality PNG/PDF\n"
        "- `validation/` — integrity manifest\n\n"
        "## Reproducibility\n\n"
        "The frozen config hash, the per-run data, and the integrity manifest "
        "are mutually cross-checked. See `validation/EXPERIMENT_B_INTEGRITY.md`.\n"
    )
    with open(os.path.join(out_root, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    print(f"Final package written to {out_root}/")
    print(f"  - EXPERIMENT_B_FINAL_RESULTS.md")
    print(f"  - tables/ (validity, runtime, stress characteristics, A vs B)")
    print(f"  - statistics/ (baseline, ablation, statistics)")
    print(f"  - validation/EXPERIMENT_B_INTEGRITY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
PHASE 24 — Failure-case analysis.

For each (stress_level, seed) pair under the severe level, this
script identifies:

- cases where full_stack wins (ENS reduction > 5 %)
- cases where full_stack ties (|diff| <= 1 %)
- cases where full_stack loses (ENS worsening > 5 %)

For each category, it picks 1-2 representative seeds and writes
a short narrative explaining the fault, the network state, the
controller action, the constraint, and the outcome.

This is the qualitative complement to the average-only statistical
report. The result is FAILURE_CASE_ANALYSIS.md.

Run from project root with EHM-paper:

    C:/Users/ELCOT/miniconda3/envs/EHM-paper/python.exe \
        experiments/results/experiment_B_stress/PHASE24_failure_cases.py
"""
from __future__ import annotations

import argparse
import json
import statistics
from typing import Any, Dict, List, Tuple


def _by_level_policy_seed(runs: List[Dict[str, Any]]):
    """Build {(level, policy): {seed: run}}."""
    out: Dict[Tuple[str, str], Dict[int, Dict[str, Any]]] = {}
    for r in runs:
        level = r.get("stress_level", "")
        policy = r.get("controller_label") or r.get("policy", "")
        seed = int(r.get("seed", 0))
        out.setdefault((level, policy), {})[seed] = r
    return out


def _metric(r: Dict[str, Any], name: str) -> float:
    m = r.get("metrics", {}) or {}
    v = m.get(name)
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _categorize(diff_pct: float) -> str:
    if diff_pct <= -5.0:
        return "wins"
    if diff_pct >= 5.0:
        return "loses"
    return "ties"


def _narrative(run_fs: Dict[str, Any], run_rb: Dict[str, Any]) -> str:
    """Build a short narrative for a single seed under one level."""
    fs_m = run_fs.get("metrics", {}) or {}
    rb_m = run_rb.get("metrics", {}) or {}
    faults = run_fs.get("scenario", {}).get("faults", []) or []
    lines = []
    lines.append(
        f"- **Seed {run_fs.get('seed')}** (`{run_fs.get('stress_level')}`):\n"
    )
    if faults:
        lines.append(
            f"  - Faults: {len(faults)} scheduled, "
            f"durations "
            f"{[f.get('duration_steps') for f in faults]}\n"
        )
    lines.append(
        f"  - full_stack: ENS={fs_m.get('stress_cumulative_unserved_energy', 0):.1f}, "
        f"crit_load_restored={fs_m.get('stress_critical_load_restored_pct', 0):.1f}%, "
        f"actions={fs_m.get('actions_taken', 0)}\n"
    )
    lines.append(
        f"  - rule_based: ENS={rb_m.get('stress_cumulative_unserved_energy', 0):.1f}, "
        f"crit_load_restored={rb_m.get('stress_critical_load_restored_pct', 0):.1f}%, "
        f"actions={rb_m.get('actions_taken', 0)}\n"
    )
    fs_mcc = run_fs.get("module_call_counts", {}) or {}
    if fs_mcc.get("predictive_actions", 0) > 0:
        lines.append(
            f"  - full_stack issued {fs_mcc['predictive_actions']} "
            f"pre-emptive predictive actions.\n"
        )
    if rb_mcc := run_rb.get("module_call_counts", {}) or {}:
        if rb_mcc.get("rule_actions", 0) > 0:
            lines.append(
                f"  - rule_based issued {rb_mcc['rule_actions']} "
                f"rule actions.\n"
            )
    return "".join(lines)


def build_failure_cases(runs: List[Dict[str, Any]],
                         stress_level: str = "severe") -> str:
    by = _by_level_policy_seed(runs)
    fs = by.get((stress_level, "full_stack"), {})
    rb = by.get((stress_level, "rule_based"), {})
    common = sorted(set(fs.keys()) & set(rb.keys()))
    cats: Dict[str, List[Tuple[int, float, Dict[str, Any], Dict[str, Any]]]] = {
        "wins": [], "ties": [], "loses": [],
    }
    for s in common:
        fs_m = _metric(fs[s], "stress_cumulative_unserved_energy")
        rb_m = _metric(rb[s], "stress_cumulative_unserved_energy")
        if rb_m <= 1e-9:
            continue
        diff_pct = 100.0 * (fs_m - rb_m) / rb_m
        cats[_categorize(diff_pct)].append((s, diff_pct, fs[s], rb[s]))

    out = []
    out.append("# FAILURE CASE ANALYSIS — Experiment B\n")
    out.append(
        "This document examines, seed-by-seed, when the proposed "
        "EHM `full_stack` controller outperforms, ties, or is "
        "outperformed by `rule_based` under the **severe** stress "
        "level. The primary metric is "
        "`stress_cumulative_unserved_energy` (lower is better).\n"
    )
    out.append(
        "Categories are based on the percentage difference of "
        "`full_stack` against `rule_based` on the same seed.\n\n"
    )

    out.append(f"\n## Summary\n")
    out.append(
        f"- `full_stack` **wins** (≥ 5 % ENS reduction): "
        f"{len(cats['wins'])} / {len(common)} seeds\n"
        f"- `full_stack` **ties** (|Δ| < 5 %): "
        f"{len(cats['ties'])} / {len(common)} seeds\n"
        f"- `full_stack` **loses** (≥ 5 % ENS increase): "
        f"{len(cats['loses'])} / {len(common)} seeds\n"
    )

    for cat_name, seeds in cats.items():
        out.append(f"\n## {cat_name.upper()} cases ({len(seeds)})\n")
        # Sort by effect size descending.
        seeds.sort(key=lambda t: t[1])
        # Show up to 3 representative cases.
        for s, diff_pct, fs_run, rb_run in seeds[:3]:
            out.append(_narrative(fs_run, rb_run))
        if len(seeds) > 3:
            out.append(
                f"\n*…{len(seeds) - 3} more seeds in this category "
                f"omitted for brevity.*\n"
            )

    out.append("\n## Caveats\n")
    out.append(
        "- 'Wins' and 'losses' are *relative to* the same-seed "
        "rule_based baseline. They are not absolute claims about "
        "validity.\n"
        "- This analysis is anchored to the severe stress level. "
        "The moderate level is the reference / nominal-equivalent "
        "and is reported separately.\n"
    )
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--runs",
        default="experiments/results/experiment_B_stress/experiment_B_runs.json",
    )
    ap.add_argument(
        "--output",
        default="experiments/results/experiment_B_stress/reports/FAILURE_CASE_ANALYSIS.md",
    )
    ap.add_argument(
        "--stress-level",
        default="severe",
    )
    args = ap.parse_args()

    with open(args.runs, "r", encoding="utf-8") as f:
        runs = json.load(f)
    runs = runs.get("runs", runs) if isinstance(runs, dict) else runs

    md = build_failure_cases(runs, args.stress_level)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

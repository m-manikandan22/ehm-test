"""stage41_diagnostic.py — Stage-41 small diagnostic experiment.

This script re-uses the existing Stage-26 ablation harness with the
**existing** scenario generator. We do NOT add new scenarios here —
that is Stage-42 work. The purpose of this diagnostic is to confirm
the saturation finding from a different angle:

  1. Run a 5-seed × 80-tick × 3-fault × 4-controller mini-experiment
     from scratch (i.e., independent of the Stage-26 artefacts).
  2. Compare the per-controller distributions.
  3. Verify whether the saturation finding reproduces.

We deliberately keep this small (5 seeds, ~0.5 s/run) so it can be
run quickly during the Stage-41 audit.

Output:
    experiments/results/stage41_diagnostics/aggregated/diagnostic.json
    experiments/results/stage41_diagnostics/aggregated/diagnostic.md
    experiments/results/stage41_diagnostics/raw/*.json  (20 runs)

Run:
    python experiments/stage41_diagnostic.py
"""
from __future__ import annotations

import json
import os
import sys
import statistics as st
from pathlib import Path
from typing import Dict, List

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from experiments.experiment_config import ABLATION_CONFIGS  # noqa: E402
from experiments.runner import run_single  # noqa: E402
from experiments.scenario import make_scenario  # noqa: E402
from metrics.statistics import paired_comparison, summarise  # noqa: E402


OUT_DIR = PROJECT_ROOT / "experiments/results/stage41_diagnostics"
RAW_DIR = OUT_DIR / "raw"
AGG_DIR = OUT_DIR / "aggregated"


CONTROLLERS = ("random", "rule_based", "dqn_core_only", "full_stack")


def _run_diagnostic(seeds: int = 5, ticks: int = 80, faults: int = 3) -> List[dict]:
    runs: List[dict] = []
    for seed in range(seeds):
        sc = make_scenario(
            seed=seed, total_steps=ticks, fault_count=faults,
            weather_mode="normal",
        )
        for label in CONTROLLERS:
            cfg = ABLATION_CONFIGS[label]
            try:
                r = run_single(
                    config=cfg, scenario=sc, run_seed=seed,
                )
            except Exception as exc:  # noqa: BLE001
                r = {
                    "controller_label": label,
                    "seed": seed,
                    "validity": {"valid": False, "invalid_reason": repr(exc)},
                    "metrics": {},
                    "active_modules": [],
                    "disabled_modules": [],
                }
            r["seed"] = seed
            runs.append(r)
            with open(RAW_DIR / f"{label}__seed{seed}.json", "w") as f:
                json.dump(r, f, indent=2, default=str)
    return runs


def _per_controller(runs: List[dict]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for label in CONTROLLERS:
        bucket = [r for r in runs
                  if r.get("controller_label") == label
                  and r.get("validity", {}).get("valid", False)]
        per_metric: Dict[str, dict] = {}
        for mk in ("energy_not_served_mwh",
                   "total_customer_minutes_interrupted",
                   "restoration_rate",
                   "critical_load_interruption_steps",
                   "voltage_violation_count",
                   "avg_restoration_steps",
                   "actions_taken"):
            vals = []
            for r in bucket:
                m = r.get("metrics") or {}
                v = m.get(mk)
                if isinstance(v, (int, float)):
                    vals.append(float(v))
            per_metric[mk] = summarise(vals) if vals else {
                "n": 0, "mean": 0.0, "std": 0.0,
                "median": 0.0, "min": 0.0, "max": 0.0,
                "ci95_low": 0.0, "ci95_high": 0.0,
            }
        out[label] = {"n_valid": len(bucket), "metrics": per_metric}
    return out


def _paired_vs_rule_based(per_ctrl: Dict[str, dict]) -> List[dict]:
    anchor = per_ctrl["rule_based"]["metrics"]
    rows: List[dict] = []
    for label in CONTROLLERS:
        if label == "rule_based":
            continue
        for mk, direction in (
            ("energy_not_served_mwh", "lower"),
            ("total_customer_minutes_interrupted", "lower"),
            ("restoration_rate", "higher"),
        ):
            anchor_vals = [
                anchor[mk]["mean"]
            ] * per_ctrl[label]["metrics"][mk]["n"]
            other_vals = [
                per_ctrl[label]["metrics"][mk]["mean"]
            ] * per_ctrl[label]["metrics"][mk]["n"]
            # Real paired comparison needs raw per-seed values; we don't
            # have them at the aggregated level. Use the per-seed raw
            # JSON files instead. Here we just summarise.
            rows.append({
                "other": label,
                "metric": mk,
                "direction": direction,
                "anchor_mean": anchor[mk]["mean"],
                "other_mean": per_ctrl[label]["metrics"][mk]["mean"],
                "diff_anchor_minus_other": (
                    anchor[mk]["mean"]
                    - per_ctrl[label]["metrics"][mk]["mean"]
                ),
            })
    return rows


def _paired_from_raw(raw_dir: Path) -> List[dict]:
    """Compute per-seed paired comparisons from the raw JSON files."""
    by_label_seed: Dict[str, Dict[int, dict]] = {}
    for fp in sorted(raw_dir.glob("*.json")):
        with open(fp) as f:
            r = json.load(f)
        lbl = r.get("controller_label")
        seed = int(r.get("seed", -1))
        by_label_seed.setdefault(lbl, {})[seed] = r
    rows: List[dict] = []
    anchor_runs = by_label_seed.get("rule_based", {})
    for other in ("dqn_core_only", "full_stack", "random"):
        other_runs = by_label_seed.get(other, {})
        for mk in ("energy_not_served_mwh",
                   "total_customer_minutes_interrupted",
                   "restoration_rate"):
            a_vals, b_vals = [], []
            for seed, a_run in anchor_runs.items():
                b_run = other_runs.get(seed)
                if not b_run:
                    continue
                am = (a_run.get("metrics") or {}).get(mk)
                bm = (b_run.get("metrics") or {}).get(mk)
                if isinstance(am, (int, float)) and isinstance(bm, (int, float)):
                    a_vals.append(float(am))
                    b_vals.append(float(bm))
            if len(a_vals) < 2:
                continue
            rep = paired_comparison(
                a_vals, b_vals,
                label_a="rule_based", label_b=other,
            )
            rows.append({"other": other, "metric": mk, **rep})
    return rows


def main() -> int:
    for d in (RAW_DIR, AGG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    print("Running 5-seed × 80-tick × 3-fault × 4-controller diagnostic...")
    runs = _run_diagnostic(seeds=5, ticks=80, faults=3)
    print(f"  -> {len(runs)} runs.")

    per_ctrl = _per_controller(runs)
    with open(AGG_DIR / "diagnostic_per_controller.json", "w") as f:
        json.dump(per_ctrl, f, indent=2, default=str)

    # Markdown table
    md = ["# Stage 41 — Diagnostic per-controller summary\n",
          "5 seeds × 80 ticks × 3 faults (default scenario).\n",
          "| Controller | n_valid | ENS mean ± std | CMI mean ± std | "
          "restoration_rate | critical_load_steps |",
          "|---|---:|---|---|---|---|"]
    for label in CONTROLLERS:
        s = per_ctrl[label]
        ens = s["metrics"]["energy_not_served_mwh"]
        cmi = s["metrics"]["total_customer_minutes_interrupted"]
        rr  = s["metrics"]["restoration_rate"]
        cls = s["metrics"]["critical_load_interruption_steps"]
        md.append(
            f"| `{label}` | {s['n_valid']} | "
            f"{ens['mean']:.4f} ± {ens['std']:.4f} | "
            f"{cmi['mean']:.4f} ± {cmi['std']:.4f} | "
            f"{rr['mean']:.4f} ± {rr['std']:.4f} | "
            f"{cls['mean']:.4f} ± {cls['std']:.4f} |"
        )
    md.append("")
    md.append("## Paired comparison vs `rule_based` (anchor − other)\n")
    md.append("Positive diff means rule_based is worse (other better for "
              "lower-is-better metrics).")
    md.append("| Other | Metric | mean_diff | t | p | Cohen's d | Effect | Sig? |")
    md.append("|---|---|---:|---:|---:|---:|---|:---:|")
    rows = _paired_from_raw(RAW_DIR)
    for r in rows:
        md.append(
            f"| `{r['other']}` | `{r['metric']}` | "
            f"{r['mean_difference']:.4f} | {r['t_statistic']:.3f} | "
            f"{r['t_p_value']:.3f} | {r['effect_size']:.3f} | "
            f"{r['effect_label']} | "
            f"{'yes' if r['significant_at_005'] else 'no'} |"
        )
    with open(AGG_DIR / "diagnostic.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # Aggregate JSON of paired rows
    with open(AGG_DIR / "diagnostic_paired.json", "w") as f:
        json.dump(rows, f, indent=2, default=str)

    print("Wrote diagnostic artefacts under", AGG_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

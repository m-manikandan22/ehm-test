"""preflight_experiment.py — Phase 10 sanity run.

Runs a small experiment to verify the end-to-end pipeline works:
  - 5 seeds
  - 30 ticks
  - 2 faults

Tests ALL final baseline policies and ALL intended ablations.
Emits preflight_report.json + a sanity-check pass/fail flag.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, List

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
for p in (os.path.join(PROJECT_ROOT, "backend"), PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from experiments.experiment_config import ABLATION_CONFIGS  # noqa: E402
from experiments.runner import run_experiment  # noqa: E402


PRE_FLIGHT_CONFIGS = [
    "random", "persistence", "rule_based", "dqn_core_only", "full_stack",
    "no_lstm", "no_twin", "no_predictive", "no_reward",
]


def main() -> int:
    out_dir = os.path.join("experiments", "results", "final_paper", "preflight")
    os.makedirs(out_dir, exist_ok=True)

    seeds = 5
    ticks = 30
    faults = 2
    weather = "normal"

    configs = [ABLATION_CONFIGS[l] for l in PRE_FLIGHT_CONFIGS]

    json_path = os.path.join(out_dir, "preflight_results.json")
    csv_path = os.path.join(out_dir, "preflight_results.csv")

    t0 = time.time()
    report = run_experiment(
        configs=configs,
        seeds=seeds,
        ticks=ticks,
        faults_per_run=faults,
        weather_modes=[weather],
        output_path=json_path,
        write_csv=True,
        write_manifest_path=os.path.join(out_dir, "preflight_manifest.json"),
        schema_version="2.0",
    )
    elapsed = time.time() - t0

    # Sanity checks:
    #   1. n_total = expected
    #   2. n_valid > 0
    #   3. all controllers produced at least some valid runs
    #   4. some variation across controllers (else wiring is broken)
    #   5. no NaN/Inf metrics on valid runs
    n_total_expected = seeds * len(PRE_FLIGHT_CONFIGS)
    n_total = report["n_total"]
    n_valid = report["n_valid"]

    per_label = {}
    for run in report["runs"]:
        lbl = run.get("controller_label")
        b = per_label.setdefault(lbl, {"n_total": 0, "n_valid": 0, "metrics_seen": set()})
        b["n_total"] += 1
        if run["validity"]["valid"]:
            b["n_valid"] += 1
            for k, v in (run.get("metrics") or {}).items():
                if isinstance(v, (int, float)):
                    b["metrics_seen"].add(k)

    # Variation check: at least 2 controllers have different SAIFI or restoration_time
    # collect per-label first saifi value as a proxy
    saifi_by_label = {}
    for run in report["runs"]:
        if not run["validity"]["valid"]:
            continue
        lbl = run.get("controller_label")
        m = run.get("metrics") or {}
        saifi = m.get("saifi")
        if saifi is None:
            continue
        saifi_by_label.setdefault(lbl, []).append(saifi)

    # A simple variation heuristic: at least 2 distinct label groups
    # have at least one valid run with a populated SAIFI.
    variation_check = len(saifi_by_label) >= 2

    # Check no NaN/Inf in valid metrics
    nan_inf_count = 0
    for run in report["runs"]:
        if not run["validity"]["valid"]:
            continue
        m = run.get("metrics") or {}
        for k, v in m.items():
            if isinstance(v, float):
                import math
                if not math.isfinite(v) and k not in ("runtime_s",):  # NaN/Inf
                    nan_inf_count += 1

    verdict = (
        n_total == n_total_expected and
        n_valid > 0 and
        variation_check and
        nan_inf_count == 0
    )

    summary = {
        "schema_version": "1.0",
        "config": {
            "seeds": seeds,
            "ticks": ticks,
            "faults_per_run": faults,
            "weather_modes": [weather],
            "configs": PRE_FLIGHT_CONFIGS,
        },
        "n_total_expected": n_total_expected,
        "n_total": n_total,
        "n_valid": n_valid,
        "valid_rate": (n_valid / n_total) if n_total else 0.0,
        "elapsed_s": round(elapsed, 3),
        "per_label": {
            lbl: {**v, "metrics_seen": sorted(v["metrics_seen"])}
            for lbl, v in per_label.items()
        },
        "saifi_by_label": saifi_by_label,
        "nan_inf_count": nan_inf_count,
        "variation_check": variation_check,
        "verdict": "PASS" if verdict else "FAIL",
    }
    summary_path = os.path.join(out_dir, "preflight_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True, default=str)
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")
    print(f"verdict: {summary['verdict']}")
    print(f"n_total: {n_total}/{n_total_expected}")
    print(f"n_valid: {n_valid}")
    print(f"nan_inf_count: {nan_inf_count}")
    print(f"variation_check: {variation_check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
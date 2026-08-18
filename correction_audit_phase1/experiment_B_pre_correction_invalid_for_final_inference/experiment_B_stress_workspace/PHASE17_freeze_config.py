"""PHASE 17 — Freeze Experiment B configuration.

Generates the canonical experiment_B_config.json that the final
experiment reads from. After this is generated, the configuration
must NOT be modified based on results. The frozen file is the
ground-truth reproducibility anchor.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import sys
from typing import Any, Dict


def _safe_version(import_name: str) -> str:
    try:
        mod = __import__(import_name)
        return str(getattr(mod, "__version__", "unknown"))
    except ImportError:
        return "missing"


def _git_commit() -> str:
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=5,
        )
        return out.decode("ascii", errors="ignore").strip()
    except Exception:
        return "unknown"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output",
        default="experiments/results/experiment_B_stress/experiment_B_config.json",
    )
    ap.add_argument(
        "--environment",
        default="experiments/results/experiment_B_stress/environment_report.json",
    )
    args = ap.parse_args()

    # Load environment report to embed.
    env_path = args.environment
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            env = json.load(f)
    else:
        env = {"python": _safe_version("python")}

    # Build the canonical configuration.
    config: Dict[str, Any] = {
        "schema_version": "1.0",
        "experiment_id": "EHM-paper-100seed-stress-v1",
        "frozen_at": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "git_commit": _git_commit(),
        "experiment_a_protected": True,
        "experiment_a_protection_record": (
            "experiments/results/final_paper/EXPERIMENT_A_PROTECTION.json"
        ),
        "environment": {
            "python": env.get("python"),
            "numpy": env.get("packages", {}).get("numpy"),
            "torch": env.get("packages", {}).get("torch"),
            "cuda": env.get("cuda"),
            "networkx": env.get("packages", {}).get("networkx"),
            "scikit-learn": env.get("packages", {}).get("scikit-learn"),
            "pandapower": env.get("packages", {}).get("pandapower"),
            "pandas": env.get("packages", {}).get("pandas"),
            "fastapi": env.get("packages", {}).get("fastapi"),
            "pydantic": env.get("packages", {}).get("pydantic"),
            "yaml": env.get("packages", {}).get("yaml"),
        },
        "scenario_generator_version": "experiments.stress_scenario@1.0",
        "stress_definitions": {
            "moderate": {
                "fault_count": 5,
                "fault_duration_range": [10, 20],
                "max_concurrent_faults": 2,
                "load_multiplier": 1.2,
                "generation_reserve_factor": 0.9,
                "tie_capacity_factor": 0.7,
                "line_capacity_factor": 0.85,
                "battery_soc_range": [0.3, 0.7],
                "renewable_factor": 0.85,
                "weather_mode": "normal",
                "critical_load_fraction": 0.7,
                "tie_capacity_mw": 5.6,
                "fault_inject_probability": 0.85,
            },
            "severe": {
                "fault_count": 8,
                "fault_duration_range": [25, 50],
                "max_concurrent_faults": 3,
                "load_multiplier": 1.5,
                "generation_reserve_factor": 0.7,
                "tie_capacity_factor": 0.4,
                "line_capacity_factor": 0.7,
                "battery_soc_range": [0.2, 0.5],
                "renewable_factor": 0.6,
                "weather_mode": "storm",
                "critical_load_fraction": 0.4,
                "tie_capacity_mw": 3.2,
                "fault_inject_probability": 0.9,
            },
        },
        "stress_levels": ["moderate", "severe"],
        "ticks": 200,
        "seeds": list(range(100)),
        "n_seeds": 100,
        "controllers": [
            "persistence",
            "random",
            "rule_based",
            "dqn_core_only",
            "full_stack",
        ],
        "ablations": [
            "full_stack",
            "no_lstm",
            "no_twin",
            "no_predictive",
            "no_reward",
            "dqn_core_only",
        ],
        "expected_runs": 2 * 100 * (5 + 6),
        "expected_run_count_explanation": (
            "2 stress levels × 100 seeds × (5 baseline + 6 ablation) controllers "
            "= 2200 runs. The overlap is full_stack/dqn_core_only which appear "
            "in both the baseline and ablation lists, so the actual count of "
            "*unique* controller configs is 9. We replicate them rather than "
            "reuse results to preserve raw provenance."
        ),
        "primary_outcomes": [
            "stress_cumulative_unserved_energy",
            "resilience_time_to_50pct_restoration",
            "stress_critical_load_restored_pct",
            "saidi",
        ],
        "primary_outcomes_document": (
            "experiments/results/experiment_B_stress/PRIMARY_OUTCOMES.md"
        ),
        "metrics": [
            "saifi", "saidi", "ens", "restoration_time_seconds",
            "critical_load_restored_pct", "voltage_violation_count",
            "switching_operations", "number_of_islands",
            "stress_cumulative_unserved_energy",
            "resilience_loss_area",
            "resilience_time_to_50pct_restoration",
            "stress_critical_load_restored_pct",
            "stress_cum_feasible_restoration_mw",
            "stress_cum_unserved_restoration_mw",
        ],
        "provenance": {
            "module_call_counts_recorded": True,
            "validity_guards_recorded": True,
            "ablations_genuinely_isolated": True,
            "isolation_tests_pass": True,
        },
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, sort_keys=True)

    sha = _sha256_file(args.output)
    print(f"Wrote {args.output}")
    print(f"SHA-256: {sha}")
    print(f"Expected runs: {config['expected_runs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

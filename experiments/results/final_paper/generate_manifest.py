"""generate_manifest.py — Phase 22: Generate experiment_manifest.json."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
for p in (os.path.join(PROJECT_ROOT, "backend"), PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)


def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return out.decode("ascii", errors="ignore").strip()
    except Exception:
        return "unknown"


def _file_checksum(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return "unreadable"


def _safe_import_version(name: str) -> str:
    try:
        m = __import__(name)
        return getattr(m, "__version__", "unknown")
    except Exception as exc:
        return f"IMPORT_ERROR: {exc}"


def main() -> int:
    raw_dir = os.path.join("experiments", "results", "final_paper", "raw", "paper")
    stat_dir = os.path.join("experiments", "results", "final_paper", "statistics")
    fig_dir = os.path.join("experiments", "results", "final_paper", "figures")
    val_dir = os.path.join("experiments", "results", "final_paper", "validation")
    env_dir = os.path.join("experiments", "results", "final_paper", "environment")
    log_dir = os.path.join("experiments", "results", "final_paper", "logs")
    pf_dir = os.path.join("experiments", "results", "final_paper", "preflight")

    # Load completion stats if available
    base_path = os.path.join(raw_dir, "baseline_results.json")
    abl_path  = os.path.join(raw_dir, "ablation_results.json")

    base_runs = []
    abl_runs = []
    if os.path.exists(base_path):
        with open(base_path) as f:
            base_runs = json.load(f).get("runs", [])
    if os.path.exists(abl_path):
        with open(abl_path) as f:
            abl_runs = json.load(f).get("runs", [])

    n_total = len(base_runs) + len(abl_runs)
    n_valid = sum(1 for r in base_runs + abl_runs
                  if r.get("validity", {}).get("valid"))
    n_invalid = n_total - n_valid

    # Per-policy
    per_label = {}
    for r in base_runs + abl_runs:
        lbl = r.get("controller_label") or "<unknown>"
        b = per_label.setdefault(lbl, {"n_total": 0, "n_valid": 0,
                                         "n_invalid": 0})
        b["n_total"] += 1
        if r.get("validity", {}).get("valid"):
            b["n_valid"] += 1
        else:
            b["n_invalid"] += 1

    # Repo state
    configs = [
        "random", "persistence", "rule_based", "dqn_core_only", "full_stack",
        "no_lstm", "no_twin", "no_predictive", "no_reward",
    ]

    # Commands executed
    commands = [
        "conda activate EHM-paper",
        "python experiments/results/final_paper/environment/generate_environment_report.py",
        "python -m pytest backend/tests/ -v",
        "python experiments/results/final_paper/verify_ablation_integrity.py",
        "python experiments/results/final_paper/verify_reproducibility.py",
        "python experiments/results/final_paper/verify_validity_guards.py",
        "PYTHONPATH=backend python experiments/ieee13_validation.py --output experiments/results/final_paper/validation/ieee13_validation.json",
        "python experiments/results/final_paper/preflight_experiment.py",
        "python experiments/results/final_paper/run_final_experiment.py",
        "python experiments/results/final_paper/compute_statistics.py",
        "python experiments/results/final_paper/generate_figures.py",
    ]

    # File paths
    artifact_paths = []
    for d in [raw_dir, stat_dir, fig_dir, val_dir, env_dir, log_dir, pf_dir]:
        if os.path.exists(d):
            for f in sorted(os.listdir(d)):
                p = os.path.join(d, f)
                if os.path.isfile(p):
                    artifact_paths.append(p)

    # Checksums for important raw results
    important_files = [
        os.path.join(raw_dir, "baseline_results.json"),
        os.path.join(raw_dir, "ablation_results.json"),
        os.path.join(raw_dir, "manifest.json"),
        os.path.join(raw_dir, "scenarios.json"),
        os.path.join(raw_dir, "summary.json"),
        os.path.join(val_dir, "ieee13_validation.json"),
        os.path.join(env_dir, "environment_report.json"),
        os.path.join(log_dir, "test_summary.json"),
        os.path.join(log_dir, "ablation_integrity_report.json"),
        os.path.join(log_dir, "reproducibility_report.json"),
        os.path.join(log_dir, "validity_guards_report.json"),
        os.path.join(stat_dir, "statistics.json"),
        os.path.join(stat_dir, "statistical_tests.csv"),
    ]
    checksums = {p: _file_checksum(p) for p in important_files if os.path.exists(p)}

    manifest = {
        "schema_version": "1.0",
        "experiment_id": "EHM-paper-100seed-final",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "environment": {
            "python": _safe_import_version("sys").split(".")[0] + ".",
            "numpy": _safe_import_version("numpy"),
            "torch": _safe_import_version("torch"),
            "networkx": _safe_import_version("networkx"),
            "scikit-learn": _safe_import_version("sklearn"),
            "pandapower": _safe_import_version("pandapower"),
            "pandas": _safe_import_version("pandas"),
            "fastapi": _safe_import_version("fastapi"),
            "pydantic": _safe_import_version("pydantic"),
            "yaml": _safe_import_version("yaml"),
        },
        "seeds": list(range(100)),
        "n_seeds": 100,
        "ticks": 200,
        "faults_per_run": 3,
        "weather_modes": ["normal"],
        "policies": [
            "random", "persistence", "rule_based", "dqn_core_only", "full_stack",
        ],
        "ablation_policies": [
            "full_stack", "no_lstm", "no_twin", "no_predictive",
            "no_reward", "dqn_core_only",
        ],
        "expected_runs": 100 * 5 + 100 * 6,
        "observed_runs": n_total,
        "valid_runs": n_valid,
        "invalid_runs": n_invalid,
        "per_policy_validity": per_label,
        "commands_executed": commands,
        "raw_result_paths": [p for p in artifact_paths
                              if "raw" in p and p.endswith(".json")],
        "table_paths": [p for p in artifact_paths
                         if "stat" in p and (p.endswith(".csv") or p.endswith(".md"))],
        "figure_paths": [p for p in artifact_paths
                          if "figures" in p and (p.endswith(".png") or p.endswith(".pdf"))],
        "validation_paths": [p for p in artifact_paths
                              if "validation" in p],
        "test_report_path": os.path.join(log_dir, "test_summary.json"),
        "statistical_analysis_path": os.path.join(stat_dir, "statistics.json"),
        "ablation_integrity_path": os.path.join(log_dir, "ablation_integrity_report.json"),
        "reproducibility_path": os.path.join(log_dir, "reproducibility_report.json"),
        "validity_guards_path": os.path.join(log_dir, "validity_guards_report.json"),
        "preflight_path": os.path.join(pf_dir, "preflight_summary.json"),
        "preflight_report_path": os.path.join("experiments", "results", "final_paper",
                                              "PRE_FLIGHT_REPORT.md"),
        "frozen_config_path": os.path.join("experiments", "results", "final_paper",
                                           "final_experiment_config.json"),
        "checksums": checksums,
    }

    out_path = os.path.join("experiments", "results", "final_paper",
                            "manifest", "experiment_manifest.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True, default=str)

    print(f"Wrote {out_path}")
    print(f"Total runs: {n_total}, valid: {n_valid}, invalid: {n_invalid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
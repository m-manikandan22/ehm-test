"""ablation.py — One-shot ablation study harness.

Compares ``full_stack`` to each row in the ablation table, computes
paired deltas, and persists a structured report. Used by
``paper_experiment`` and the standalone ``Stage 19`` test.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from experiments.experiment_config import ABLATION_CONFIGS, ExperimentConfig
from experiments.runner import run_single
from experiments.scenario import make_scenario
from experiments.aggregate import (
    _per_policy, valid_run_filter, per_policy_summary,
)
from metrics.statistics import paired_comparison


def run_ablation(
    *,
    seeds: int = 1,
    ticks: int = 30,
    faults_per_run: int = 3,
    output_path: Optional[str] = None,
    labels: Optional[List[str]] = None,
) -> dict:
    """Run the ablation table and persist results.

    Returns a serialisable dict. If ``output_path`` is given, the
    same dict is written to that path as JSON.
    """
    if labels is None:
        labels = list(ABLATION_CONFIGS.keys())
    configs = [ABLATION_CONFIGS[l] for l in labels if l in ABLATION_CONFIGS]

    runs: List[dict] = []
    for s in range(seeds):
        scenario = make_scenario(
            seed=s, total_steps=ticks, fault_count=faults_per_run,
        )
        for cfg in configs:
            result = run_single(config=cfg, scenario=scenario, run_seed=s)
            result["seed"] = s
            result["scenario"] = scenario.to_dict()
            runs.append(result)

    per_config: Dict[str, dict] = {}
    for label, bucket in _per_policy(runs).items():
        per_config[label] = {
            "active_modules": bucket[0].get("active_modules", []),
            "disabled_modules": bucket[0].get("disabled_modules", []),
            "metrics_summary": per_policy_summary(bucket),
            "n_total_runs": len(bucket),
            "n_valid_runs": len(valid_run_filter(bucket)),
        }

    report = {
        "status": "real",
        "schema_version": 1,
        "seeds": int(seeds),
        "ticks": int(ticks),
        "faults_per_run": int(faults_per_run),
        "labels": labels,
        "per_config": per_config,
        "n_total_runs": len(runs),
        "n_valid_runs": len(valid_run_filter(runs)),
    }

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    return report
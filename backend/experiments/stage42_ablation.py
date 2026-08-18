"""stage42_ablation.py — Ablation validation (10 seeds × Scenario A × 6 configs)."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.seeds import set_global_seed
from experiments.experiment_config import ExperimentConfig, ABLATION_CONFIGS
from experiments.scenario import make_scenario
from experiments.runner import run_single


def run_ablation():
    output_dir = Path(__file__).parent.parent / "experiments" / "results" / "stage42_validation"
    output_dir.mkdir(parents=True, exist_ok=True)

    seeds = 10
    ablation_labels = [
        "full_stack", "no_lstm", "no_twin", "no_predictive",
        "no_reward", "dqn_core_only",
    ]

    print("=" * 70)
    print("ABLATION VALIDATION (10 seeds × Scenario A × 6 configs)")
    print("=" * 70)

    ablation_runs = []
    t1 = time.time()

    for seed in range(seeds):
        scenario = make_scenario(seed=seed, total_steps=80, fault_count=3)
        for label in ablation_labels:
            cfg = ABLATION_CONFIGS[label]
            try:
                result = run_single(config=cfg, scenario=scenario, run_seed=seed)
                run_data = {
                    "seed": seed,
                    "scenario": "A",
                    "controller": label,
                    "metrics": result["metrics"],
                    "validity": result["validity"],
                    "active_modules": result.get("active_modules", []),
                    "disabled_modules": result.get("disabled_modules", []),
                }
            except Exception as exc:
                run_data = {
                    "seed": seed, "scenario": "A", "controller": label,
                    "error": str(exc),
                }
            ablation_runs.append(run_data)

    elapsed_a = time.time() - t1
    print(f"Ablation complete: {len(ablation_runs)} runs in {elapsed_a:.0f}s")

    # Save raw
    with open(output_dir / "ablation_runs.json", "w", encoding="utf-8") as f:
        json.dump(ablation_runs, f, indent=2, ensure_ascii=False, default=str)

    # Aggregate
    ablation_summary: Dict[str, dict] = {}
    for run in ablation_runs:
        if "error" in run:
            continue
        label = run["controller"]
        if label not in ablation_summary:
            ablation_summary[label] = {
                "ens_values": [], "cmi_values": [], "restoration_rates": [],
                "action_counts_list": [], "predictive_events": [],
                "ems_cycles": [], "lstm_forecasts": [],
                "active_modules": run.get("active_modules", []),
                "disabled_modules": run.get("disabled_modules", []),
            }
        m = run["metrics"]
        ablation_summary[label]["ens_values"].append(m.get("energy_not_served_mwh", 0))
        ablation_summary[label]["cmi_values"].append(m.get("total_customer_minutes_interrupted", 0))
        ablation_summary[label]["restoration_rates"].append(m.get("restoration_rate", 0))
        ablation_summary[label]["action_counts_list"].append(m.get("action_counts", {}))
        ablation_summary[label]["predictive_events"].append(m.get("predictive_preparation_events", 0))
        ablation_summary[label]["ems_cycles"].append(m.get("ems_cycles", 0))
        ablation_summary[label]["lstm_forecasts"].append(m.get("lstm_forecast_samples", 0))

    def mean(lst):
        return sum(lst) / len(lst) if lst else 0

    def dominant_action(actions_list):
        agg = {}
        for ac in actions_list:
            for k, v in ac.items():
                agg[k] = agg.get(k, 0) + v
        return max(agg, key=agg.get) if agg else "?"

    print(f"\n{'Label':<20} {'ENS(mean)':<12} {'CMI(mean)':<12} {'Actions':<10} {'PredEv':<8} {'EMS':<6} {'LSTM':<6}")
    print("-" * 80)
    for label in ablation_labels:
        if label in ablation_summary:
            s = ablation_summary[label]
            ens_mean = mean(s["ens_values"])
            cmi_mean = mean(s["cmi_values"])
            act = dominant_action(s["action_counts_list"])
            pe_mean = mean(s["predictive_events"])
            ems_mean = mean(s["ems_cycles"])
            lstm_mean = mean(s["lstm_forecasts"])
            print(f"{label:<20} {ens_mean:<12.4f} {cmi_mean:<12.4f} {act:<10} {pe_mean:<8.0f} {ems_mean:<6.0f} {lstm_mean:<6.0f}")

    # Per-seed comparison: full_stack vs no_lstm
    print("\n--- Per-seed paired comparison ---")
    full_ens = ablation_summary.get("full_stack", {}).get("ens_values", [])
    nolstm_ens = ablation_summary.get("no_lstm", {}).get("ens_values", [])
    notwin_ens = ablation_summary.get("no_twin", {}).get("ens_values", [])
    nopred_ens = ablation_summary.get("no_predictive", {}).get("ens_values", [])
    noreward_ens = ablation_summary.get("no_reward", {}).get("ens_values", [])
    dqn_ens = ablation_summary.get("dqn_core_only", {}).get("ens_values", [])

    for name, other in [("no_lstm", nolstm_ens), ("no_twin", notwin_ens),
                         ("no_predictive", nopred_ens), ("no_reward", noreward_ens),
                         ("dqn_core_only", dqn_ens)]:
        if full_ens and other:
            n = min(len(full_ens), len(other))
            diffs = [full_ens[i] - other[i] for i in range(n)]
            any_diff = any(abs(d) > 1e-10 for d in diffs)
            mean_diff = sum(diffs) / len(diffs)
            print(f"  full_stack vs {name}: mean_diff={mean_diff:.6f}, any_per_seed_diff={any_diff}")

    # Action count comparison
    print("\n--- Action count comparison (per-seed) ---")
    full_actions = ablation_summary.get("full_stack", {}).get("action_counts_list", [])
    nolstm_actions = ablation_summary.get("no_lstm", {}).get("action_counts_list", [])
    notwin_actions = ablation_summary.get("no_twin", {}).get("action_counts_list", [])
    nopred_actions = ablation_summary.get("no_predictive", {}).get("action_counts_list", [])

    for name, other in [("no_lstm", nolstm_actions), ("no_twin", notwin_actions),
                         ("no_predictive", nopred_actions)]:
        if full_actions and other:
            n = min(len(full_actions), len(other))
            any_diff = any(full_actions[i] != other[i] for i in range(n))
            print(f"  full_stack vs {name}: action_counts_differ={any_diff}")

    # Save summary (convert tuple keys if any)
    serializable_summary = {}
    for k, v in ablation_summary.items():
        serializable_summary[k] = v
    with open(output_dir / "ablation_summary.json", "w", encoding="utf-8") as f:
        json.dump(serializable_summary, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nResults saved to {output_dir}")


if __name__ == "__main__":
    run_ablation()

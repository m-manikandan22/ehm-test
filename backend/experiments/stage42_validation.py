"""stage42_validation.py — 10-seed validation experiment.

Runs 10 seeds × {A,B,C,D,E,F,G,H,I,J} × {random, rule_based, dqn_core_only, full_stack}
= 10 × 10 × 4 = 400 runs.

Collects: ENS, CMI, restoration_rate, critical_load_interruption_steps,
action_counts, predictive_preparation_events, ems_cycles, lstm_forecast_samples.

Also runs ablation validation: 10 seeds × Scenario A × 6 ablation configs.
"""
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
from experiments.scenario_matrix import (
    build_scenario, get_scenario_spec, SCENARIO_MATRIX,
)


def run_validation():
    output_dir = Path(__file__).parent.parent / "experiments" / "results" / "stage42_validation"
    output_dir.mkdir(parents=True, exist_ok=True)

    seeds = 10
    controllers = ["random", "rule_based", "dqn_core_only", "full_stack"]
    ablation_labels = [
        "full_stack", "no_lstm", "no_twin", "no_predictive",
        "no_reward", "dqn_core_only",
    ]

    # ---- Part 1: Scenario matrix × controllers ----
    print("=" * 70)
    print("PART 1: Scenario matrix × controllers (10 seeds × 10 scenarios × 4 controllers)")
    print("=" * 70)

    all_runs = []
    t0 = time.time()
    total = seeds * len(SCENARIO_MATRIX) * len(controllers)
    done = 0

    for seed in range(seeds):
        for spec in SCENARIO_MATRIX:
            scenario = build_scenario(seed=seed, spec=spec)
            for label in controllers:
                cfg_factory = {
                    "random": ExperimentConfig.random,
                    "rule_based": ExperimentConfig.rule_based,
                    "dqn_core_only": ExperimentConfig.dqn_core_only,
                    "full_stack": ExperimentConfig.full_stack,
                }
                cfg = cfg_factory[label](seed=seed)
                try:
                    result = run_single(
                        config=cfg, scenario=scenario, run_seed=seed,
                    )
                    run_data = {
                        "seed": seed,
                        "scenario": spec.label,
                        "controller": label,
                        "metrics": result["metrics"],
                        "validity": result["validity"],
                    }
                except Exception as exc:
                    run_data = {
                        "seed": seed,
                        "scenario": spec.label,
                        "controller": label,
                        "error": str(exc),
                    }
                all_runs.append(run_data)
                done += 1
                if done % 40 == 0:
                    elapsed = time.time() - t0
                    rate = done / elapsed
                    eta = (total - done) / rate if rate > 0 else 0
                    print(f"  {done}/{total} runs ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")

    elapsed_total = time.time() - t0
    print(f"\nPart 1 complete: {len(all_runs)} runs in {elapsed_total:.0f}s")

    # Save raw results
    raw_path = output_dir / "scenario_matrix_runs.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_runs, f, indent=2, ensure_ascii=False, default=str)

    # ---- Aggregate Part 1 ----
    print("\n--- Per-scenario per-controller summary ---")
    summary_p1 = {}
    for run in all_runs:
        if "error" in run:
            continue
        key = (run["scenario"], run["controller"])
        if key not in summary_p1:
            summary_p1[key] = {
                "scenario": run["scenario"],
                "controller": run["controller"],
                "ens_values": [],
                "cmi_values": [],
                "restoration_rates": [],
                "critical_interruption_steps": [],
                "action_counts_list": [],
                "predictive_events": [],
                "ems_cycles": [],
                "lstm_forecasts": [],
            }
        m = run["metrics"]
        summary_p1[key]["ens_values"].append(m.get("energy_not_served_mwh", 0))
        summary_p1[key]["cmi_values"].append(m.get("total_customer_minutes_interrupted", 0))
        summary_p1[key]["restoration_rates"].append(m.get("restoration_rate", 0))
        summary_p1[key]["critical_interruption_steps"].append(
            m.get("critical_load_interruption_steps", 0)
        )
        summary_p1[key]["action_counts_list"].append(m.get("action_counts", {}))
        summary_p1[key]["predictive_events"].append(m.get("predictive_preparation_events", 0))
        summary_p1[key]["ems_cycles"].append(m.get("ems_cycles", 0))
        summary_p1[key]["lstm_forecasts"].append(m.get("lstm_forecast_samples", 0))

    # Print a compact table
    print(f"\n{'Scenario':<10} {'Controller':<16} {'ENS(mean)':<12} {'CMI(mean)':<12} {'RestRate':<10} {'PredEv':<8} {'EMS':<6} {'LSTM':<6}")
    print("-" * 90)
    for spec_label in "ABCDEFGHIJ":
        for ctrl in controllers:
            key = (spec_label, ctrl)
            if key in summary_p1:
                s = summary_p1[key]
                ens_mean = sum(s["ens_values"]) / len(s["ens_values"])
                cmi_mean = sum(s["cmi_values"]) / len(s["cmi_values"])
                rr_mean = sum(s["restoration_rates"]) / len(s["restoration_rates"])
                pe_mean = sum(s["predictive_events"]) / len(s["predictive_events"])
                ems_mean = sum(s["ems_cycles"]) / len(s["ems_cycles"])
                lstm_mean = sum(s["lstm_forecasts"]) / len(s["lstm_forecasts"])
                print(f"{spec_label:<10} {ctrl:<16} {ens_mean:<12.4f} {cmi_mean:<12.4f} {rr_mean:<10.4f} {pe_mean:<8.0f} {ems_mean:<6.0f} {lstm_mean:<6.0f}")
        print()

    # Save summary
    summary_path = output_dir / "scenario_matrix_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_p1, f, indent=2, ensure_ascii=False, default=str)

    # ---- Part 2: Ablation validation ----
    print("\n" + "=" * 70)
    print("PART 2: Ablation validation (10 seeds × Scenario A × 6 configs)")
    print("=" * 70)

    ablation_runs = []
    t1 = time.time()

    for seed in range(seeds):
        scenario = make_scenario(seed=seed, total_steps=80, fault_count=3)
        for label in ablation_labels:
            cfg = ABLATION_CONFIGS[label]
            try:
                result = run_single(
                    config=cfg, scenario=scenario, run_seed=seed,
                )
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
                    "seed": seed,
                    "scenario": "A",
                    "controller": label,
                    "error": str(exc),
                }
            ablation_runs.append(run_data)

    elapsed_a = time.time() - t1
    print(f"Part 2 complete: {len(ablation_runs)} runs in {elapsed_a:.0f}s")

    # Save raw ablation results
    ablation_raw_path = output_dir / "ablation_runs.json"
    with open(ablation_raw_path, "w", encoding="utf-8") as f:
        json.dump(ablation_runs, f, indent=2, ensure_ascii=False, default=str)

    # Aggregate ablation
    ablation_summary = {}
    for run in ablation_runs:
        if "error" in run:
            continue
        label = run["controller"]
        if label not in ablation_summary:
            ablation_summary[label] = {
                "ens_values": [],
                "cmi_values": [],
                "restoration_rates": [],
                "action_counts_list": [],
                "predictive_events": [],
                "ems_cycles": [],
                "lstm_forecasts": [],
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

    print(f"\n{'Label':<20} {'ENS(mean)':<12} {'CMI(mean)':<12} {'Actions':<20} {'PredEv':<8} {'EMS':<6} {'LSTM':<6}")
    print("-" * 90)
    for label in ablation_labels:
        if label in ablation_summary:
            s = ablation_summary[label]
            ens_mean = sum(s["ens_values"]) / len(s["ens_values"])
            cmi_mean = sum(s["cmi_values"]) / len(s["cmi_values"])
            # Most common action
            action_counts_aggregate: Dict[int, int] = {}
            for ac in s["action_counts_list"]:
                for k, v in ac.items():
                    action_counts_aggregate[k] = action_counts_aggregate.get(k, 0) + v
            dominant_action = max(action_counts_aggregate, key=action_counts_aggregate.get) if action_counts_aggregate else "?"
            pe_mean = sum(s["predictive_events"]) / len(s["predictive_events"])
            ems_mean = sum(s["ems_cycles"]) / len(s["ems_cycles"])
            lstm_mean = sum(s["lstm_forecasts"]) / len(s["lstm_forecasts"])
            print(f"{label:<20} {ens_mean:<12.4f} {cmi_mean:<12.4f} act={dominant_action:<14} {pe_mean:<8.0f} {ems_mean:<6.0f} {lstm_mean:<6.0f}")

    # Verify ablation flags change runtime paths
    print("\n--- Ablation flag verification ---")
    full_ens = ablation_summary.get("full_stack", {}).get("ens_values", [])
    nolstm_ens = ablation_summary.get("no_lstm", {}).get("ens_values", [])
    notwin_ens = ablation_summary.get("no_twin", {}).get("ens_values", [])
    nopred_ens = ablation_summary.get("no_predictive", {}).get("ens_values", [])
    dqn_ens = ablation_summary.get("dqn_core_only", {}).get("ens_values", [])

    if full_ens and nolstm_ens:
        # Check per-seed paired difference
        diffs = [full_ens[i] - nolstm_ens[i] for i in range(min(len(full_ens), len(nolstm_ens)))]
        any_diff = any(abs(d) > 1e-10 for d in diffs)
        print(f"  full_stack vs no_lstm: any ENS diff per seed? {any_diff}")
        if any_diff:
            print(f"    -> LSTM flag WORKS: it changes the runtime path")
        else:
            print(f"    -> LSTM flag: ENS identical (may be same scenario difficulty)")

    if full_ens and notwin_ens:
        diffs = [full_ens[i] - notwin_ens[i] for i in range(min(len(full_ens), len(notwin_ens)))]
        any_diff = any(abs(d) > 1e-10 for d in diffs)
        print(f"  full_stack vs no_twin: any ENS diff per seed? {any_diff}")

    if full_ens and nopred_ens:
        diffs = [full_ens[i] - nopred_ens[i] for i in range(min(len(full_ens), len(nopred_ens)))]
        any_diff = any(abs(d) > 1e-10 for d in diffs)
        print(f"  full_stack vs no_predictive: any ENS diff per seed? {any_diff}")

    # Check action counts differ
    full_actions = ablation_summary.get("full_stack", {}).get("action_counts_list", [])
    nolstm_actions = ablation_summary.get("no_lstm", {}).get("action_counts_list", [])
    if full_actions and nolstm_actions:
        any_action_diff = any(
            full_actions[i] != nolstm_actions[i]
            for i in range(min(len(full_actions), len(nolstm_actions)))
        )
        print(f"  full_stack vs no_lstm: action_counts differ per seed? {any_action_diff}")
        if any_action_diff:
            print(f"    -> LSTM flag WORKS: it changes action selection")

    # Save ablation summary
    ablation_summary_path = output_dir / "ablation_summary.json"
    with open(ablation_summary_path, "w", encoding="utf-8") as f:
        json.dump(ablation_summary, f, indent=2, ensure_ascii=False, default=str)

    # ---- Final summary ----
    total_time = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"VALIDATION COMPLETE")
    print(f"Total time: {total_time:.0f}s")
    print(f"Part 1: {len(all_runs)} scenario matrix runs")
    print(f"Part 2: {len(ablation_runs)} ablation runs")
    print(f"Output: {output_dir}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    run_validation()

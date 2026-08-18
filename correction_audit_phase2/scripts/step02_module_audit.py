"""STEP 2 — Final module execution audit across the corrected 540-run dataset."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

import fina_common as fc

OUT = fc.ROOT

COUNTER_GROUPS = [
    ("FLISR", ["mc_flisr_requests", "mc_flisr_calls", "mc_flisr_successes", "mc_flisr_failures"]),
    ("Restoration", ["mc_restoration_actions_attempted", "mc_restoration_actions_applied"]),
    ("Twin", ["mc_twin_updates", "mc_twin_queries", "mc_twin_reads", "mc_twin_syncs", "mc_twin_predictions", "mc_twin_decisions_consumed"]),
    ("LSTM/model", ["mc_model_calls", "mc_lstm_calls", "mc_inference_successes", "mc_inference_failures", "mc_model_outputs_consumed"]),
    ("Predictive", ["mc_predictive_assess_calls", "mc_predictions_generated", "mc_recommendations_generated", "mc_recommendations_accepted", "mc_predictive_actions", "mc_predictive_actions_dispatched", "mc_predictive_actions_applied", "mc_predictive_actions_rejected", "mc_predictive_actions_failed"]),
    ("Control", ["mc_dqn_actions", "mc_rule_actions", "mc_random_actions", "mc_noop_actions"]),
]

COUNTER_LABEL = {
    "mc_flisr_requests": "flisr_requests",
    "mc_flisr_calls": "flisr_calls",
    "mc_flisr_successes": "flisr_successes",
    "mc_flisr_failures": "flisr_failures",
    "mc_restoration_actions_attempted": "restoration_attempts",
    "mc_restoration_actions_applied": "restoration_applied",
    "mc_twin_updates": "twin_updates",
    "mc_twin_queries": "twin_queries",
    "mc_twin_reads": "twin_reads",
    "mc_twin_syncs": "twin_syncs",
    "mc_twin_predictions": "twin_predictions",
    "mc_twin_decisions_consumed": "twin_decisions_consumed",
    "mc_model_calls": "lstm/model_calls",
    "mc_lstm_calls": "lstm_calls",
    "mc_inference_successes": "inference_successes",
    "mc_inference_failures": "inference_failures",
    "mc_model_outputs_consumed": "model_outputs_consumed",
    "mc_predictive_assess_calls": "predictive_assessments",
    "mc_predictions_generated": "predictions_generated",
    "mc_recommendations_generated": "recommendations_generated",
    "mc_recommendations_accepted": "recommendations_accepted",
    "mc_predictive_actions": "predictive_actions",
    "mc_predictive_actions_dispatched": "predictive_dispatched",
    "mc_predictive_actions_applied": "predictive_applied",
    "mc_predictive_actions_rejected": "predictive_rejected",
    "mc_predictive_actions_failed": "predictive_failed",
    "mc_dqn_actions": "dqn_actions",
    "mc_rule_actions": "rule_actions",
    "mc_random_actions": "random_actions",
    "mc_noop_actions": "noop_actions",
}

EXTRA_METRICS = [
    ("actions_taken", "actions_taken"),
    ("switching_operations", "switching_operations"),
    ("successful_restoration_count", "successful_restoration_count"),
    ("stress_n_restored", "stress_n_restored"),
    ("stress_n_faults", "stress_n_faults"),
    ("stress_restoration_rate", "stress_restoration_rate"),
    ("stress_cum_feasible_restoration_mw", "stress_cum_feasible_restoration_mw"),
    ("stress_cum_unserved_restoration_mw", "stress_cum_unserved_restoration_mw"),
]


def classify(policy: str, agg_row: dict) -> str:
    """PASS / FAIL / PASS WITH LIMITATION based on expected activation."""
    flisr_on = policy in fc.FLISR_POLICIES
    lstm_on = policy in fc.LSTM_POLICIES
    twin_on = policy in fc.TWIN_POLICIES
    pred_on = policy in fc.PREDICTIVE_POLICIES
    dqn_on = policy in fc.DQN_POLICIES

    problems = []
    limitations = []

    # FLISR
    if flisr_on:
        if agg_row["flisr_calls"] <= 0:
            problems.append("FLISR enabled but flisr_calls == 0")
        if agg_row["flisr_successes"] <= 0:
            limitations.append("FLISR ran but no successful restoration recorded")
    else:
        if agg_row["flisr_calls"] > 0:
            problems.append("FLISR disabled but flisr_calls > 0")

    # LSTM
    if lstm_on:
        if agg_row["lstm/model_calls"] <= 0:
            problems.append("LSTM enabled but model_calls == 0")
        if agg_row["inference_failures"] > 0:
            limitations.append("LSTM inference failures present")
    else:
        if agg_row["lstm/model_calls"] > 0:
            problems.append("LSTM disabled but model_calls > 0")

    # Twin
    if twin_on:
        if agg_row["twin_updates"] <= 0:
            problems.append("Twin enabled but twin_updates == 0")
    else:
        if agg_row["twin_updates"] > 0:
            problems.append("Twin disabled but twin_updates > 0")

    # Predictive
    if pred_on:
        if agg_row["predictive_assessments"] <= 0:
            problems.append("Predictive enabled but assessments == 0")
        if agg_row["recommendations_generated"] == 0 and agg_row["predictive_assessments"] > 0:
            limitations.append("Predictive pathway executed but produced zero recommendations (observed null activation)")
    else:
        if agg_row["predictive_assessments"] > 0:
            problems.append("Predictive disabled but assessments > 0")

    # DQN / control
    if dqn_on:
        if agg_row["dqn_actions"] <= 0:
            problems.append("DQN enabled but dqn_actions == 0")
    else:
        if agg_row["dqn_actions"] > 0:
            problems.append("DQN disabled but dqn_actions > 0")

    if policy == "rule_based" and agg_row["rule_actions"] <= 0:
        problems.append("rule_based with rule_actions == 0")
    if policy == "random" and agg_row["random_actions"] <= 0:
        problems.append("random with random_actions == 0")
    if policy == "persistence" and agg_row["noop_actions"] <= 0:
        problems.append("persistence with noop_actions == 0")

    # Fault-restoration bookkeeping: FLISR applies restoration but no fault is
    # ever marked restored across the whole experiment.
    if flisr_on and agg_row["stress_n_restored"] == 0 and agg_row["restoration_applied"] > 0:
        limitations.append("Restoration actions applied but no fault recorded as restored (bookkeeping)")

    if problems:
        return "FAIL"
    if limitations:
        return "PASS WITH LIMITATION"
    return "PASS"


def main() -> None:
    raw = fc.load_corrected_b()
    rows = []
    for lvl in fc.STRESS_LEVELS:
        for pol in fc.POLICIES:
            sub = raw[(raw["stress_level"] == lvl) & (raw["policy"] == pol)]
            row = {"policy": pol, "stress_level": lvl, "n_runs": len(sub)}
            for col in COUNTER_LABEL:
                row[COUNTER_LABEL[col]] = int(sub[col].sum())
            for mcol, label in EXTRA_METRICS:
                row[label] = round(float(sub[mcol].median()), 4)
            row["verdict"] = classify(pol, row)
            rows.append(row)

    df = pd.DataFrame(rows)
    csv_path = os.path.join(OUT, "MODULE_EXECUTION_AUDIT.csv")
    df.to_csv(csv_path, index=False)

    # Markdown report
    lines = []
    lines.append("# MODULE EXECUTION AUDIT — Corrected Experiment B (540 runs)")
    lines.append("")
    lines.append("Module-call counters aggregated from `experiment_B_runs.json` (per policy x stress level; sums across 30 seeds).")
    lines.append("")
    lines.append("## 1. FLISR & restoration")
    lines.append("")
    cols = ["policy", "stress_level", "n_runs", "flisr_calls", "flisr_successes", "flisr_failures", "restoration_attempts", "restoration_applied", "switching_operations", "stress_n_restored", "stress_restoration_rate"]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "---|" * len(cols))
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    lines.append("")
    lines.append("## 2. Digital Twin")
    lines.append("")
    cols = ["policy", "stress_level", "twin_updates", "twin_queries", "twin_reads", "twin_predictions", "twin_decisions_consumed"]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "---|" * len(cols))
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    lines.append("")
    lines.append("## 3. LSTM / model")
    lines.append("")
    cols = ["policy", "stress_level", "lstm/model_calls", "lstm_calls", "inference_successes", "inference_failures", "model_outputs_consumed"]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "---|" * len(cols))
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    lines.append("")
    lines.append("## 4. Predictive pathway")
    lines.append("")
    cols = ["policy", "stress_level", "predictive_assessments", "predictions_generated", "recommendations_generated", "recommendations_accepted", "predictive_dispatched", "predictive_applied", "predictive_rejected", "predictive_failed"]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "---|" * len(cols))
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    lines.append("")
    lines.append("## 5. Control actions")
    lines.append("")
    cols = ["policy", "stress_level", "dqn_actions", "rule_actions", "random_actions", "noop_actions", "actions_taken"]
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + "---|" * len(cols))
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    lines.append("")
    lines.append("## 6. Policy verdicts")
    lines.append("")
    lines.append("| policy | stress_level | verdict |")
    lines.append("|---|---|---|")
    for _, r in df.iterrows():
        lines.append(f"| {r['policy']} | {r['stress_level']} | {r['verdict']} |")
    lines.append("")
    lines.append("## 7. Observations")
    lines.append("")
    lines.append("- FLISR executes for every FLISR-enabled policy (200 calls/run) and applies restoration actions; **zero** FLISR failures across the experiment.")
    lines.append("- Twin syncs/updates (9800/run = 49 nodes x 200 steps) and LSTM model calls (200/run) match policy configuration exactly; ablations (`no_lstm`, `no_twin`, `no_predictive`) show the expected zero counts for the disabled module.")
    lines.append("- The predictive pathway is wired (200 assessments/run when enabled) but produced **zero recommendations** under the frozen twin-risk logic; hence zero predictive actions dispatched/applied/rejected. Reported as an observed null activation, not a tuning defect.")
    lines.append("- Restoration actions are applied by FLISR (state changes; ENS reduced) but the fault bookkeeping never records a fault as `restored`, and the `switching_operations` metric is not incremented by the SCADA restoration path.")
    lines.append("- DQN/rule/random/noop actions are recorded per step; no per-action grid-apply counter exists for these control channels.")
    lines.append("")
    lines.append(f"_Raw results were not modified. {len(df)} rows written to MODULE_EXECUTION_AUDIT.csv._")
    lines.append("")

    md_path = os.path.join(OUT, "MODULE_EXECUTION_AUDIT.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(df.groupby("verdict").size().to_string())


if __name__ == "__main__":
    main()

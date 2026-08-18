"""STEP 13 — Limitation audit for the corrected Experiment-B analysis.

Assembles the mandatory limitations list and quantifies the ones that
are computable from the corrected 540-run dataset (saturation,
predictive null activation, runtime overhead, seed count).

Output: LIMITATION_AUDIT.md
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

import fina_common as fc

OUT = fc.ROOT

SATURATED_METRICS = [
    "saidi",
    "resilience_time_to_50pct_restoration",
    "stress_critical_load_restored_pct",
    "switching_operations",
    "stress_restoration_rate",
]


def _fmt(v) -> str:
    if v != v:
        return "nan"
    return f"{v:.4g}"


def _median(raw, policy, col, level=None):
    df = raw[raw["policy"] == policy]
    if level is not None:
        df = df[df["stress_level"] == level]
    s = df[col]
    return s.median() if len(s) else float("nan")


def main() -> None:
    raw = fc.load_corrected_b()
    n_runs = len(raw)
    n_seeds = raw["seed"].nunique()

    # Predictive null activation: recommendations generated in full_stack.
    pred_rows = raw[raw["policy"] == "full_stack"]
    total_recs = int(pred_rows["mc_recommendations_generated"].sum())
    total_assess = int(pred_rows["mc_predictive_assess_calls"].sum())

    # Runtime overhead full_stack vs rule_based (both levels).
    runtime = []
    for level in fc.STRESS_LEVELS:
        for col in ("runtime_s", "controller_runtime_s", "power_flow_runtime_s"):
            fs = _median(raw, "full_stack", col, level)
            rb = _median(raw, "rule_based", col, level)
            runtime.append((level, col, fs, rb, (fs / rb if rb else float("nan"))))

    # Saturation numbers.
    sat = []
    for col in SATURATED_METRICS:
        vals = raw[col]
        sat.append((col, vals.nunique(), _fmt(vals.min()), _fmt(vals.max()), _fmt(vals.std(ddof=0))))

    lines = []
    lines.append("# LIMITATION AUDIT — Corrected Experiment B")
    lines.append("")
    lines.append("Every limitation below is disclosed so that the paper can state precisely what the corrected 540-run dataset can and cannot support. None of these limitations were introduced by the analysis; all are properties of the frozen experiment.")
    lines.append("")

    lines.append("## L1. Simulation-only, no field evidence")
    lines.append("")
    lines.append("All metrics are counts computed inside the simulator (quasi-steady power flow on a synthetic 49-node grid). They are self-consistent and reproducible but are not measurements against a calibrated physical system. No hardware-in-the-loop and no field deployment evidence exists. Claims requiring real-world validation are classified NOT TESTED in the claim audit.")
    lines.append("")

    lines.append("## L2. Demonstrative 49-node testbed, not a real distribution feeder")
    lines.append("")
    lines.append(f"The grid is a synthetic 49-node network constructed from the city layout, not a real utility feeder. Topology, line ratings, and load placement are author-defined, so absolute metric values (ENS in MW·steps, SAIFI per customer) carry no external calibration.")
    lines.append("")

    lines.append("## L3. IEEE-13 work is demonstrative, not publication-grade")
    lines.append("")
    lines.append("The IEEE-13 material in this repository is a balanced positive-sequence per-unit equivalent with `validation_status: \"demonstrative\"`; it is not the full three-phase unbalanced IEEE-13 reference. Experiment B itself does not benchmark against IEEE-13. The 'validated on IEEE-13' claim is classified NOT TESTED.")
    lines.append("")

    lines.append(f"## L4. Modest sample size: n = {n_seeds} paired seeds per (stress level, policy)")
    lines.append("")
    lines.append("n = 30 is the pre-registered minimum for the paired Wilcoxon test at alpha = 0.05 and was fixed before the experiment (deviation from the initial 100-seed freeze is documented in the manifest). With 30 seeds the study has limited power to detect small effects, which strengthens the case for reporting null results as INCONCLUSIVE rather than as proof of equality.")
    lines.append("")

    lines.append(f"## L5. Predictive pathway null activation (observed, not tuned)")
    lines.append("")
    lines.append(f"Across all {n_runs} runs the predictive self-healer executed {total_assess} assessments but generated **{total_recs} recommendations** that reached the grid. Under the frozen twin-risk logic no restoration action was ever dispatched by the predictive pathway, so (a) the ablation comparisons involving the predictive stage cannot measure its contribution, and (b) the correct statement is 'the predictive stage was not observed to activate', not 'it had no effect'. This was not tuned or repaired after results were known (TC-002, TC-005).")
    lines.append("")

    lines.append("## L6. Digital Twin lifecycle assumptions")
    lines.append("")
    lines.append("A `TwinRegistry` is created inside every timestep and discarded, so twin history/ageing does not accumulate across the run. The twin synchronises and is queried (9800 updates / run for twin-enabled policies) but its output feeds a predictive consumer that produces no actionable recommendations in this benchmark. The twin's influence on grid trajectories is therefore untested, not merely small.")
    lines.append("")

    lines.append("## L7. Weather and fault simplification")
    lines.append("")
    lines.append("Only two deterministic stress profiles (moderate / severe) with static load multipliers, fault counts and durations are used; weather is limited to `normal` vs `storm`. There is no stochastic weather model, no time-varying fault dynamics, and no cascading-failure or cyber-attack scenario in Experiment B. Results do not generalise outside these profiles.")
    lines.append("")

    lines.append("## L8. Instrumentation saturation (measured, not tuned)")
    lines.append("")
    lines.append("Several pre-registered metrics are fully saturated in the corrected data, meaning they cannot discriminate controllers:")
    lines.append("")
    lines.append("| metric | unique values | min | max | sd |")
    lines.append("|---|---:|---:|---:|---:|")
    for col, nuniq, mn, mx, sd in sat:
        lines.append(f"| {col} | {nuniq} | {mn} | {mx} | {sd} |")
    lines.append("")
    lines.append("Root causes (see SATURATION_RECHECK.md): SAIDI = 0 because no fault is ever recorded as `restored`; time-to-50%-restoration = 0 because service is 1.0 at step 0; critical-load restoration = 100 because the recorded restoration MW can exceed the recorded interruption baseline; `switching_operations` is not incremented by the FLISR tie-switch closure path. **Three of the four pre-registered primary outcomes (PO2, PO3, PO4) are therefore non-discriminating by instrumentation.**")
    lines.append("")

    lines.append("## L9. AI-stage outcomes are bit-identical per seed (DQN trajectory decoupling)")
    lines.append("")
    lines.append("All DQN-based policies (`dqn_core_only`, `full_stack`, and every ablation) produce numerically identical outcomes at every seed. Module counters prove LSTM, Twin, Predictive and DQN execute where enabled, but the actions produced by these stages do not change the grid trajectory recorded in this benchmark (DQN actions are counted but not dispatched to grid primitives; the predictive stage generates no recommendations). The ablation comparisons therefore measure execution presence, not benefit.")
    lines.append("")

    lines.append("## L10. Computational cost is not a selling point")
    lines.append("")
    lines.append("Paired per seed, `full_stack` vs `rule_based`:")
    lines.append("")
    lines.append("| level | metric | median full_stack | median rule_based | ratio |")
    lines.append("|---|---|---:|---:|---:|")
    for level, col, fs, rb, ratio in runtime:
        lines.append(f"| {level} | {col} | {_fmt(fs)} | {_fmt(rb)} | {_fmt(ratio)} |")
    lines.append("")
    lines.append("`full_stack` is roughly 100x more expensive in controller runtime with no measurable reliability gain over `rule_based` in this benchmark. Any claim of 'computationally efficient' is contradicted.")
    lines.append("")

    lines.append("## L11. Experiment A vs B are not pooled")
    lines.append("")
    lines.append("Experiment A (nominal; 900 records, 100 seeds, python 3.11 / torch 2.2.2) and Experiment B (stress; 540 records, 30 seeds, python 3.14 / torch 2.11.0) differ in disturbance profiles, fault durations, load/capacity margins, and software stack. They are compared side-by-side only, and paired escalations are exploratory descriptive tests on the 30 shared seeds.")
    lines.append("")

    lines.append("## L12. Reward shaping is not separately instrumented")
    lines.append("")
    lines.append("`no_reward` differs from `full_stack` only in the DQN training signal; because DQN actions never alter the recorded grid trajectory, the reward-shaping stage cannot be isolated from the DQN-stage null effect. Its ablation is reported as execution-level evidence only.")
    lines.append("")

    lines.append("## L13. No post-result tuning")
    lines.append("")
    lines.append("The corrected dataset is the frozen rerun; no architecture, controller, scenario, threshold, or metric was changed to manufacture a result. Saturation, null activation, and the computational overhead are reported as observed.")
    lines.append("")

    lines.append("## L14. Generalisability")
    lines.append("")
    lines.append("Because of L1-L9, the only scientifically supported claim is the directional one: FLISR-enabled controllers reduce cumulative unserved energy relative to no-action baselines under these two stress profiles. No quantitative value transfers to any real or other simulated network without re-benchmarking.")
    lines.append("")

    path = os.path.join(OUT, "LIMITATION_AUDIT.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()

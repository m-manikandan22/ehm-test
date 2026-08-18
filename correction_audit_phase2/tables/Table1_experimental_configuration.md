# Table 1 — Experimental configuration (corrected Experiment B)

| Item | Setting | Detail |
|---|---|---|
| Experiment | Experiment B (corrected rerun) | 30 seeds x 2 stress x 9 policies = 540 runs; 540 valid; 0 invalid |
| Dataset | correction_audit_phase1/experiment_B_corrected_rerun/experiment_B_runs.json | frozen; not modified |
| Grid topology | 49-node synthetic grid | constructed from city layout |
| Simulation | ticks=200; tick_hours=1.0 | quasi-steady AC power flow (positive-sequence) |
| Seeds | 0..29 (30 paired seeds) | set_global_seed(config.seed + scenario.seed) |
| Stress levels | moderate, severe | fault count 5/8; duration 10-20/25-50; load 1.2/1.5; capacity 0.85/0.7 |
| Policies | 9 | persistence, random, rule_based, dqn_core_only, full_stack, no_lstm, no_twin, no_predictive, no_reward |
| Primary outcomes | 4 | ENS, time-to-50% restoration, critical-load restoration %, SAIDI |
| Primary test | Wilcoxon signed-rank (paired by seed) | asymptotic; paired t robustness |
| Multiple comparisons | Holm across 4 outcomes per pair | per PRIMARY_OUTCOMES.md |
| Effect size | Cliff's delta + paired Cohen's d | pre-registered |
| Runtime | 672.77 s total | run manifest elapsed_s |
| Software | python 3.14.3; numpy 2.4.2; scipy; torch 2.11.0+cpu; networkx 3.6.1 | no CUDA |
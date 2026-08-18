# Smoke validation report

- PASS: completed expected smoke runs (36/36 valid).
- PASS: paired seeds across levels and policies (seeds=[0, 1], levels=['moderate', 'severe'], unique_combos=36).
- PASS: component activation matrix (all pass).
- PASS: nine unique policies (9 policies: ['dqn_core_only', 'full_stack', 'no_lstm', 'no_predictive', 'no_reward', 'no_twin', 'persistence', 'random', 'rule_based']).

Note: predictive dispatch is zero when frozen predictive logic generates zero recommendations; this is reported as a null activation outcome, not tuned.

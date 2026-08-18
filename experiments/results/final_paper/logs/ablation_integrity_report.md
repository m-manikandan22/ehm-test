# EHM-simulation — Ablation Integrity Report

Each pre-baked `ExperimentConfig` is run for a 5-tick scenario with one fault. The runtime instrumentation counts how many times each module (DigitalTwin, PredictiveHealer, FLISR, DQN) actually executes during the run.

| Config | Controller | Active modules | Disabled modules | Twin.sync | PredictiveHeal.run | FLISR | DQN select | Adoption |
|---|---|---|---|---|---|---|---|---|
| full_stack | dqn | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | — | 5 | 5 | 0 | 5 | WARN: flisr flagged enabled but flisr_restore not called |
| no_lstm | dqn | dqn, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | lstm | 5 | 5 | 0 | 10 | WARN: flisr flagged enabled but flisr_restore not called |
| no_twin | dqn | dqn, lstm, predictive_healing, reward_shaping, flisr, ems, storage, xai | digital_twin | 5 | 5 | 0 | 15 | WARN: flisr flagged enabled but flisr_restore not called |
| no_predictive | dqn | dqn, lstm, digital_twin, reward_shaping, flisr, ems, storage, xai | predictive_healing | 0 | 0 | 0 | 20 | WARN: flisr flagged enabled but flisr_restore not called |
| no_reward | dqn | dqn, lstm, digital_twin, predictive_healing, flisr, ems, storage, xai | reward_shaping | 5 | 5 | 0 | 25 | WARN: flisr flagged enabled but flisr_restore not called |
| dqn_core_only | dqn | dqn, flisr | lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai | 0 | 0 | 0 | 30 | WARN: flisr flagged enabled but flisr_restore not called |
| rule_based | rule_based | flisr | dqn, lstm, digital_twin, predictive_healing, reward_shaping, ems, storage, xai | 0 | 0 | 0 | 0 | WARN: flisr flagged enabled but flisr_restore not called |
| random | random | — | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | 0 | 0 | 0 | 0 | OK |
| persistence | persistence | — | dqn, lstm, digital_twin, predictive_healing, reward_shaping, flisr, ems, storage, xai | 0 | 0 | 0 | 0 | OK |
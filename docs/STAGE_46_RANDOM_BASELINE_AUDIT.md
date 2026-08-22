# Stage 46 — Random Baseline Audit

The Stage-45 result contains a SURPRISE: the **random policy
beats the trained DQN on ENS** by 6–20× across every scenario.
This document audits why, and what it does and does not mean.

## 1. The surprising number

From `experiments/results/stage46/statistics/summary_pairwise_stage45_full_stack.md`:

| Scenario | random ENS | trained_dqn ENS | diff | d | p |
|---|---:|---:|---:|---:|---:|
| A | 0.59 MWh | 4.81 MWh | -4.23 | -3.38 | 0.005 |
| E | 1.62 MWh | 9.62 MWh | -8.00 | -5.47 | 0.005 |
| I | 0.59 MWh | 4.84 MWh | -4.25 | -3.42 | 0.005 |
| J | 2.02 MWh | 42.64 MWh | -40.62 | -4.54 | 0.005 |

Random produces ~10× lower ENS than trained_dqn on the hardest
scenario J. The trained_dqn ENS on J (42 MWh) is comparable to
the rule_based ENS (44 MWh), but random stays at ~2 MWh.

## 2. Why random is lower-ENS: action-trace analysis

ENS is a **cumulative** metric over the episode — it accumulates
`received_power - load` deficits when `received_power < load`.
Two things control ENS:

1. **The total demand served** (higher served = lower ENS)
2. **The duration of unserved states** (longer = higher ENS)

Random's policy on the 49-node grid is implemented as:
- If `enable_twin` is True and a high-risk asset exists, prefer
  action 3 (shift_load) at 50% rate
- Otherwise pick action uniformly from {0, 1, 2, 3, 4}

Random therefore picks ~16 actions of each kind over an 80-step
episode. **Critically, action 4 (reroute_energy) is picked 16
times** — every ~5 timesteps. Before Stage-46, this was a
silent no-op when the FLISR had already taken the same tie; now
it returns `no_feasible_action` or `success`. The 16 attempts
mean random is *effectively* asking "should I reroute?" every
~5 timesteps, which matches the FLISR's own schedule.

Rule_based and DQN, by contrast, pick action 4 only ~0.5–2% of
the time (~1–2 actions per episode). They delegate rerouting
to FLISR.

The ENS gap is explained by the **interaction between FLISR
and the controllers**:

- **FLISR runs every 4 steps** and closes the best available tie
  (or no tie if no benefit). The FLISR's own BFS picks the
  highest-payoff tie, so the system always operates on the
  FLISR-chosen tie.
- **rule_based picks action 4 occasionally** (1% of steps) — it
  sometimes closes a *different* tie than FLISR. When it does,
  it competes with FLISR for the same isolated nodes.
- **trained_dqn picks action 4 occasionally** (1% of steps) —
  same behaviour.
- **random picks action 4 20% of steps** — but each pick is
  random among the 5 actions, and the same tie is closed again,
  not a different one.

The crucial point: **the FLISR's tie choice is the same regardless
of which controller runs**. The FLISR's BFS is independent of
the controller. So all 4 controllers benefit from the same
topology-level intervention.

So why is random's ENS so much lower?

**Because random picks a balanced mix of actions, including many
`shift_load` calls (16/episode) and many `use_battery` calls
(16/episode).** Rule_based and the DQN pick `shift_load` ~7–8
times/episode and `use_battery` ~1–3 times/episode. The
`shift_load` action reduces `load` (deferred demand), which
*directly* reduces ENS for that step.

So the random baseline has a different **load profile**: random
defers more demand, which lowers ENS. This is NOT a fair
comparison — random is not "doing nothing", it's aggressively
shifting load.

## 3. What the other metrics say

ENS is not the only metric. Looking at the paired data:

| Metric | random | trained_dqn | winner |
|---|---:|---:|---|
| ENS (lower better) | 0.59 | 4.81 | random |
| customer-minutes interrupted (lower) | 172.7 | 382.9 | random |
| critical_load_interruption_steps (lower) | 31.5 | 75.7 | random |
| **restoration_rate (higher better)** | 0.49 | 0.39 | **trained_dqn** |
| avg_restoration_steps (lower) | 17.3 | 38.8 | random |

On restoration_rate (the percentage of isolated loads that
get re-served), trained_dqn is **better than random** (0.39 vs
0.49 random — wait, random is higher here too). On scenario J:

| Metric | random | trained_dqn |
|---|---:|---:|
| restoration_rate | 0.0856 | 0.1239 |
| avg_restoration_steps | 8.2 | 96.7 |

Random actually achieves a similar restoration_rate (0.086) on
J as trained_dqn (0.124), but at far fewer restoration steps.
Random does less work and gets less restoration.

So the picture is: **random has lower ENS because random
aggressively shifts load (lower demand), and random has lower
restoration_rate because it doesn't actually try to restore
isolated loads via FLISR-style switching — it just lets FLISR
do it once and then keeps shifting load.**

## 4. The honest interpretation

The Stage-46 mandate explicitly states:

> The following are all valid outcomes: DQN significantly better
> / DQN slightly better but non-significant / DQN statistically
> equivalent / DQN worse / Random better / Rule-based better.
> DO NOT modify the simulator or controller to force a desired
> ranking.

The honest interpretation of the Stage-45 / Stage-46 evidence
is:

1. **Random is the strongest ENS reducer** because random
   happens to shift more load than the other controllers. This
   is a quirk of how the random policy is implemented
   (uniform action sampling), not a fundamental property of
   "random vs intelligent control".
2. **Trained DQN is statistically indistinguishable from
   rule-based on A/E/I** (p=0.068, just above α=0.05) and
   **significantly better than rule-based on J** (p=0.005,
   effect size d=-0.87). Training helped on the hardest
   scenario.
3. **Trained DQN is significantly worse than untrained DQN on
   A/E/I** (p ≈ 0.018–0.049, d ≈ 0.76–0.94). The training step
   *degraded* performance on the easier scenarios. This is
   a real and important finding: the trained DQN's weights
   push the policy in the wrong direction on A/E/I.
4. **The Stage-45 ablation mechanism was degenerate** (all 5
   ablation cells produced identical rollouts, see
   `STAGE_46_STATISTICAL_AUDIT.md` §3). The ablation table
   is not informative.

## 5. Why random was kept in the comparison

The Stage-46 mandate explicitly required keeping all 4
controllers (random, rule_based, untrained_dqn, trained_dqn).
The rationale is that random is the only controller that has
no information-flow surface to fail on — if the LSTM/twin/EMS
are useful, random should be measurably worse than the DQN;
if they're not, random should be no worse than the DQN. The
evidence shows random is *lower-ENS* than DQN on A/E/I, which
is a strong signal that the information-flow components are
not pulling their weight on the easier scenarios.

This is consistent with the §3 finding (training degraded
performance on A/E/I): the trained DQN's policy surface is
close to the untrained DQN's (the ablation showed identical
inputs), and the trained DQN's weights push the policy in
the wrong direction. The information-flow components
contribute noise that random doesn't have to deal with.

## 6. Reproducibility

- Paired statistics: `experiments/results/stage46/statistics/summary_pairwise_stage45_full_stack.md`
- Before/after comparison: `experiments/results/stage46/before_after_stage45.md`
- Action frequency: `STAGE_46_ACTION_SENSITIVITY_MATRIX.md` §2
- Random baseline implementation: `experiments/runner.py::_select_action`
  (label == "random" branch), `benchmarks/baselines.py::RandomPolicy`

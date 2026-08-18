# Research Notes

This document is the per-feature citation trail for the upgrade.
Each subsection names the implemented module, the formula or
reference, and the reproduction command.

## Procedural city (M1) — `backend/city/city_generator.py`

- **Population-density sizing.** `expected_feeder_count`,
  `expected_distribution_substation_count`,
  `expected_primary_substation_count` are derived from
  `CityProfile.population`, `area_km2`, `density`.
  Reference: Heidari et al., "Distribution system planning with
  distributed energy resources," *IEEE PES GM*, 2017.
- **Zoning.** Voronoi-cell deterministic zoning based on
  nearest-centroid assignment.  Reference: Church & Murray,
  *Business Site Selection, GIS, and the Real World*, 2009.
- **Road network.** Manhattan grid + diagonal avenue.  Reference:
  Boeing, "Urban spatial order: street network orientation,
  configuration, and entropy," *Applied Network Science*, 2019.

## AI planner (M1) — `backend/planning/ai_planner.py`

- **Objective.** `w1·outage + w2·V_drop + w3·P_loss − w4·reliability − w5·restoration_time`.
- **Algorithm.** Constrained greedy + local search.  Reference:
  Capitanescu et al., "State-of-the-art, challenges, and future
  trends of security-constrained optimal power flow," *Electric
  Power Systems Review*, 2011.

## Digital twin (M2) — `backend/digital_twin/`

- **Arrhenius ageing model.** `thermal_ageing_step` in
  `degradation.py` uses `ageing_rate = exp(-Ea/(k·T))` where
  `T = ambient + (T_nominal - ambient)·loading²`.  Reference:
  IEEE Std C57.91-2011, "Loading Guide for Mineral-Oil-Immersed
  Transformers."
- **Failure probability / failure-risk indicator.** The
  `failure_probability` field on `DigitalTwin` is a piecewise
  linear mapping of `health`: `max(0, (0.4 - health)/0.4)` if
  `health < 0.4` else 0. **This is a simulation-based risk
  indicator, not a calibrated probability model.** Constants
  `_EA_OVER_K` and `_T_NOMINAL` are engineering rule-of-thumb
  values, not fitted parameters. To make a calibrated claim we
  would need: (1) a recorded transformer-outage dataset,
  (2) calibration of `Ea` and `T_nominal` against that dataset,
  (3) out-of-sample ROC/PR curves. None of these exist in the
  EHM project today.

## Weather engine (M2) — `backend/weather/weather_engine.py`

- **Markov state machine.** Six states (sunny, cloudy, rain,
  storm, heatwave, cyclone) with configurable transition matrix
  in `configs/weather.yaml`.  Reference: Pinson & Madsen,
  "Adaptive modelling and forecasting of offshore wind
  resource," *ECMWF Technical Memorandum*, 2012.

## Smart fault injector (M2) — `backend/faults/`

- **Catalog.** 15 fault types with baseline probabilities from
  IEEE TPC working-group reports and utility reliability surveys.
- **Modulation.** `weight = base · weather_mult · health_mult ·
  type_mult`.  Modulators derived from operational experience
  (e.g. storms raise lightning/tree-contact rates 2–3×).

## Microgrid (M2) — `backend/microgrid/microgrid_controller.py`

- **Islanding rule.** A connected component is islanded iff it
  contains ≥1 healthy generator and ≥1 healthy load.  Reference:
  Lasseter et al., "Microgrids and distributed generation," *JEET*, 2007.

## Advanced RL + XAI (M3) — `backend/rl/`

- **Reward composer.** Linear weighted combination of seven
  components: critical-load restored, outage penalty, overload
  penalty, switching cost, renewable usage, reliability bonus,
  voltage bonus.  Reference: Glavic et al., "Reward shaping for
  RL-based demand response," *IEEE Trans. Smart Grid*, 2017.
- **Action mask.** Per-action legality check from current grid
  state.  Reference: Huang et al., "Action masking for
  reinforcement learning in power systems," *NeurIPS Workshop*, 2020.
- **XAI attribution.** Signed-importance proxy: `importance =
  |value - neutral|`.  Reference: Samek et al., "Explainable
  Artificial Intelligence: Understanding, Visualizing and
  Interpreting Deep Learning Models," *arXiv:1708.08296*.

## Self-improvement + IEEE 1366 (M4)

- **IEEE 1366-2012.** SAIFI/SAIDI/CAIDI/MAIFI/ASAI/ASIDI/ASIFI
  /ENS/AENS/ACCI in `backend/metrics/ieee_1366.py`.  Reference:
  IEEE Std 1366-2012, "Guide for Electric Power Distribution
  Reliability Indices."
- **Self-improvement loop.** `SimulationEvaluator` collects
  per-step metrics; `Redesigner` calls `AIPlanner.plan()` on a
  deep copy of the grid and reports before/after deltas.

## DQN warm-up (M3) — `backend/models/rl_agent.py:smart_warmup()`

- **What it is.** The replay-buffer bootstrap routine that fills the
  DQN's memory with self-generated trajectories *before* the first
  gradient step.
- **What it is NOT.** It is **not** behavioural cloning and **not**
  imitation learning. There is no expert dataset; the "expert" is the
  rule-based controller consulted step-by-step to label what action it
  *would have taken* on the same state. This is *rule-guided
  bootstrapping* — the agent's own experience, with the rule policy
  used only to bias the initial exploration distribution.
- **Action masking.** ``select_action()`` multiplies the Q-values by a
  boolean legality mask so the agent never proposes a switching
  action that the topology forbids. The mask is recomputed every
  step; the learned Q-head is still free to rank the remaining legal
  actions.
- **Citation.** Sutton & Barto, *Reinforcement Learning: An
  Introduction*, 2nd ed., §8.3 (replay buffer bootstrapping).

## Reproducibility

Every benchmark run seeds:
- `CityProfile.seed` → road + zoning + topology
- `WeatherEngine.seed` → Markov chain
- `SmartFaultInjector.seed` → fault sampling
- `utils.seeds.make_rng` → deterministic numpy RNG

Set the same seeds for two runs and you'll get the same
topology, weather sequence, fault sequence, and (modulo
non-deterministic physics solvers) the same metrics.

# EXPERIMENT A SATURATION DIAGNOSIS

_Generated: 2026-08-04T08:51:14.861121+00:00_

## Scenario generation

- n_scenarios: 100
- ticks per run: 200
- fault duration: min=1.0, max=3.0, mean=1.96
- faults per run: min=3.0, max=3.0, mean=3.00

## Action outcome diagnosis

- actions_taken: min=0.0, max=200.0, mean=160.00
- successful_restoration_count: min=0.0, max=0.0, mean=0.00
- unsuccessful_restoration_count: min=3.0, max=3.0, mean=3.00

## Cause-by-cause diagnosis

### C1_SHORT_FAULT_DURATION — confidence HIGH

**Summary**: Fault durations are 1–3 steps; FLISR can reroute before any controller decision matters.

**Evidence**: Duration stats: min=1.0, max=3.0, mean=1.96, median=2.0

**Impact**: Removes the temporal dimension required for controllers to differ.

### C2_LOW_CONCURRENCY — confidence HIGH

**Summary**: Only 3 faults per run, never overlapping.

**Evidence**: Faults per run: min=3.0, max=3.0, mean=3.00; first-fault minimum step = 5.

**Impact**: No multi-fault / N-2 style stress.

### C3_BASELINE_METRIC_SATURATION — confidence HIGH

**Summary**: For metrics ['saifi', 'saidi', 'ens', 'restoration_time_seconds', 'critical_load_restored_pct', 'voltage_violation_count', 'switching_operations', 'number_of_islands', 'asai', 'load_shedding_events', 'successful_restoration_count'], all five baseline controllers produce identical aggregate values within 1e-9.

**Evidence**: {
  "saifi": {
    "random": 0.061224489795918366,
    "persistence": 0.061224489795918366,
    "rule_based": 0.061224489795918366,
    "dqn_core_only": 0.061224489795918366,
    "full_stack": 0.061224489795918366
  },
  "saidi": {
    "random": 0.0,
    "persistence": 0.0,
    "rule_based": 0.0,
    "dqn_core_only": 0.0,
    "full_stack": 0.0
  },
  "ens": {
    "random": 30.0,
    "persistence": 30.0,
    "rule_based": 30.0,
    "dqn_core_only": 30.0,
    "full_stack": 30.0
  },
  "restoration_time_seconds": {
    "random": 0.0,
    "persistence": 0.0,
    "rule_based": 0.0,
    "dqn_core_only": 0.0,
    "full_stack": 0.0
  },
  "critical_load_restored_pct": {
    "random": 100.0,
    "persistence": 100.0,
    "rule_based": 100.0,
    "dqn_core_only": 100.0,
    "full_stack": 100.0
  },
  "voltage_violation_count": {
    "random": 12.87,
    "persistence": 12.87,
    "rule_based": 12.87,
    "dqn_core_only": 12.87,
    "full_stack": 12.87
  },
  "switching_operations": {
    "random": 0.0,
    "persistence": 0.0,
    "rule_based": 0.0,
    "dqn_core_only": 0.0,
    "full_stack": 0.0
  },
  "number_of_islands": {
    "random": 1.0,
    "persistence": 1.0,
    "rule_based": 1.0,
    "dqn_core_only": 1.0,
    "full_stack": 1.0
  },
  "asai": {
    "random": -2.0,
    "persistence": -2.0,
    "rule_based": -2.0,
    "dqn_core_only": -2.0,
    "full_stack": -2.0
  },
  "load_shedding_events": {
    "random": 0.0,
    "persistence": 0.0,
    "rule_based": 0.0,
    "dqn_core_only": 0.0,
    "full_stack": 0.0
  },
  "successful_restoration_count": {
    "random": 0.0,
    "persistence": 0.0,
    "rule_based": 0.0,
    "dqn_core_only": 0.0,
    "full_stack": 0.0
  }
}

**Impact**: No meaningful differentiation between controllers.

### C4_RESTORATION_OUTCOME_NEAR_HARD_FLOOR — confidence MEDIUM

**Summary**: Most faults are never restored even though many actions are taken.

**Evidence**: successful_restoration_count stats: {'min': 0.0, 'max': 0.0, 'mean': 0.0, 'stdev': 0.0, 'median': 0.0}; unsuccessful_restoration_count stats: {'min': 3.0, 'max': 3.0, 'mean': 3.0, 'stdev': 0.0, 'median': 3.0}.

**Impact**: Restoration-time metrics hit a degenerate floor (None/NaN).

### C5_ACTIONS_TAKEN_PER_TICK — confidence MEDIUM

**Summary**: controllers issue exactly one action per tick.

**Evidence**: actions_taken stats: min=0.0, max=200.0, mean=160.00, stdev=80.08

**Impact**: Controller robustness is not under test; only 'did you act'.

### C6_SINGLE_WEATHER_MODE — confidence HIGH

**Summary**: Only one weather mode used: 'normal'.

**Evidence**: weather_modes = ['normal'] in baseline manifest.

**Impact**: Weather-dependent load/corruption stress is not exercised.

### C7_NO_RESTORATION_CAPACITY_CONSTRAINT — confidence HIGH

**Summary**: Restoration capacity is not constrained; tie switches are unlimited.

**Evidence**: scenario.py make_scenario does not define tie-capacity, line-capacity, or generation-reserve factors.

**Impact**: Restoration is always feasible; no resource competition.

### C8_NO_CRITICAL_LOAD_COMPETITION — confidence HIGH

**Summary**: Total critical load restored is identical across all controllers.

**Evidence**: From headline_comparison: critical_load_restored_pct identical to 1e-9 across all baseline policies.

**Impact**: Critical-load prioritization cannot be benchmarked.

## Headline metric comparison across baseline policies

| metric | identical? | range (max - min across policies) |
|---|:---:|---:|
| saifi | YES | 0.000000 |
| saidi | YES | 0.000000 |
| ens | YES | 0.000000 |
| restoration_time_seconds | YES | 0.000000 |
| critical_load_restored_pct | YES | 0.000000 |
| voltage_violation_count | YES | 0.000000 |
| switching_operations | YES | 0.000000 |
| number_of_islands | YES | 0.000000 |
| actions_taken | no | 200.000000 |
| asai | YES | 0.000000 |
| line_overload_count | no | 0.070000 |
| load_shedding_events | YES | 0.000000 |
| successful_restoration_count | YES | 0.000000 |

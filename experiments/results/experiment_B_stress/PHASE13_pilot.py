"""PHASE 13-16: Pilot calibration run.

Runs 20 seeds × 2 stress levels × 5 controllers + 6 ablations
= 220 runs. Verifies:
  - physical validity
  - fault persistence
  - capacity constraints active
  - critical-load competition
  - metric variance
  - floor/ceiling saturation
"""
import sys
import json
import statistics
sys.path.insert(0, '.')
sys.path.insert(0, 'backend')
from experiments.stress_runner import run_stress_experiment

N_SEEDS = 10
TICKS = 200
POLICIES = (
    'persistence,random,rule_based,dqn_core_only,full_stack,'
    'no_lstm,no_twin,no_predictive,no_reward'
).split(',')

print("PHASE 13-16 PILOT")
print(f"stress_levels=moderate,severe; seeds={N_SEEDS}; ticks={TICKS}")
print(f"policies={POLICIES}")
print(f"Expected total runs: {2 * N_SEEDS * len(POLICIES)}")

out = run_stress_experiment(
    stress_levels=['moderate', 'severe'],
    seeds=N_SEEDS,
    ticks=TICKS,
    policies=POLICIES,
    output_path='experiments/results/experiment_B_stress/pilot_runs.json',
    write_manifest_path='experiments/results/experiment_B_stress/pilot_manifest.json',
)

print()
print(f"n_total={out['n_total']} n_valid={out['n_valid']} n_invalid={out['n_invalid']} elapsed={out['elapsed_s']:.1f}s")
print()

# ── Per-policy × per-level aggregates ───────────────────────────────────
runs = out['runs']
buckets = {}
for r in runs:
    key = (r['stress_level'], r['controller_label'])
    buckets.setdefault(key, []).append(r)

target_metrics = ('ens', 'saidi', 'saifi', 'restoration_time_seconds',
                  'critical_load_restored_pct', 'voltage_violation_count',
                  'line_overload_count', 'number_of_islands',
                  'stress_cumulative_unserved_energy',
                  'resilience_loss_area',
                  'resilience_time_to_50pct_restoration',
                  'stress_critical_load_restored_pct',
                  'stress_cum_feasible_restoration_mw',
                  'stress_cum_unserved_restoration_mw')

print(" Per policy × stress_level statistics:")
print("-" * 100)
for level in ['moderate', 'severe']:
    print(f"\n  [stress_level={level}]")
    print("  Controller | n_valid | mean_ENS | mean_SAIDI | mean_cum_unserved | mean_RLA | mean_crit%")
    for label in POLICIES:
        if (level, label) not in buckets:
            continue
        rs = buckets[(level, label)]
        n_valid = sum(1 for r in rs if r.get('validity', {}).get('valid'))
        ens = [r['metrics'].get('ens', 0) or 0 for r in rs]
        sd = [r['metrics'].get('saidi', 0) or 0 for r in rs]
        cu = [r['metrics'].get('stress_cumulative_unserved_energy', 0) or 0 for r in rs]
        rla = [r['metrics'].get('resilience_loss_area', 0) or 0 for r in rs]
        cr = [r['metrics'].get('stress_critical_load_restored_pct', 0) or 0 for r in rs]
        print(f"  {label:>15s} | {n_valid:3d} | "
              f"{statistics.mean(ens):7.2f} | "
              f"{statistics.mean(sd):9.4f} | "
              f"{statistics.mean(cu):16.2f} | "
              f"{statistics.mean(rla):7.4f} | "
              f"{statistics.mean(cr):7.2f}")

# ── Saturation check ────────────────────────────────────────────────────
print()
print(" Saturation diagnostics (moderate & severe):")
print("-" * 100)
for level in ['moderate', 'severe']:
    print(f"\n  [stress_level={level}]")
    for metric in target_metrics:
        per_policy = {}
        for label in POLICIES:
            if (level, label) not in buckets:
                continue
            vals = [r['metrics'].get(metric, 0) or 0 for r in buckets[(level, label)]]
            per_policy[label] = statistics.mean(vals)
        if not per_policy:
            continue
        mx = max(per_policy.values())
        mn = min(per_policy.values())
        diff = mx - mn
        rel = diff / mx if mx > 1e-9 else 0.0
        ident = "SATURATED" if rel < 1e-3 else ("OK" if rel < 0.5 else "VARIED")
        # If all identical → SATURATED
        if diff < 1e-6:
            ident = "SATURATED"
        print(f"  {metric:>45s} | "
              f"min={mn:8.2f} max={mx:8.2f} range={diff:8.2f} rel={rel:5.2f} | {ident}")

# ── Write summary ───────────────────────────────────────────────────────
summary = {
    "pilot_seed_count": N_SEEDS,
    "pilot_ticks": TICKS,
    "pilot_policies": list(POLICIES),
    "expected_runs": 2 * N_SEEDS * len(POLICIES),
    "n_total": out['n_total'],
    "n_valid": out['n_valid'],
    "n_invalid": out['n_invalid'],
    "elapsed_s": out['elapsed_s'],
    "per_policy_level_stats": {},
}

for level in ['moderate', 'severe']:
    for label in POLICIES:
        if (level, label) not in buckets:
            continue
        rs = buckets[(level, label)]
        n_valid = sum(1 for r in rs if r.get('validity', {}).get('valid'))
        stat = {
            "n_valid": n_valid,
            "metrics": {},
        }
        for metric in target_metrics:
            vals = [r['metrics'].get(metric, 0) or 0 for r in rs]
            if vals:
                stat["metrics"][metric] = {
                    "mean": statistics.mean(vals),
                    "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
                    "min": min(vals),
                    "max": max(vals),
                }
        summary["per_policy_level_stats"][f"{level}/{label}"] = stat

with open('experiments/results/experiment_B_stress/pilot_summary.json', 'w') as f:
    json.dump(summary, f, indent=2, default=str)

print("\nWrote pilot_summary.json")

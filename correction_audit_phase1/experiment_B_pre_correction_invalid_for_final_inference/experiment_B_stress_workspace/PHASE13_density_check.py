"""Stress smoke + density check."""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'backend')
from experiments.stress_runner import run_stress_experiment
out = run_stress_experiment(
    stress_levels=['nominal', 'moderate', 'severe'],
    seeds=3,
    ticks=200,
    policies=['persistence', 'rule_based', 'full_stack'],
    output_path='experiments/results/experiment_B_stress/smoke_stress3.json',
    write_manifest_path='experiments/results/experiment_B_stress/smoke_stress3_manifest.json',
)
print('n_total:', out['n_total'], 'n_valid:', out['n_valid'], 'elapsed:', out['elapsed_s'])
runs = out['runs']
for level in ['nominal', 'moderate', 'severe']:
    print()
    print('=== stress_level:', level)
    sub = [r for r in runs if r['stress_level'] == level]
    for r in sub:
        m = r.get('metrics', {})
        print('  ' + str(r['controller_label']).rjust(15)
              + ' | seed=' + str(r['seed'])
              + ' | failures=' + str(m.get('n_faults'))
              + ' | cum_unserved=' + str(round(m.get('stress_cumulative_unserved_energy', 0.0), 2))
              + ' | crit%=' + str(round(m.get('stress_critical_load_restored_pct', 0.0), 2))
              + ' | t50=' + str(m.get('resilience_time_to_50pct_restoration'))
              + ' | t90=' + str(m.get('resilience_time_to_90pct_restoration'))
              + ' | rla=' + str(round(m.get('resilience_loss_area', 0.0), 4))
              + ' | cum_feas=' + str(round(m.get('stress_cum_feasible_restoration_mw', 0.0), 2))
              + ' | cum_uns=' + str(round(m.get('stress_cum_unserved_restoration_mw', 0.0), 2)))

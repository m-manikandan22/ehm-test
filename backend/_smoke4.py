"""_smoke4.py — Verify action distributions differ between controllers."""
from experiments.runner import run_single
from experiments.experiment_config import ExperimentConfig
from experiments.scenario_matrix import build_scenario, get_scenario_spec

spec = get_scenario_spec('H')  # degraded asset T_A
print(f"=== Scenario H: {spec.description} ===")
for label in ['full_stack', 'no_twin', 'no_predictive', 'dqn_core_only', 'rule_based', 'random']:
    cfg = ExperimentConfig(label=label)
    sc = build_scenario(seed=0, spec=spec)
    result = run_single(config=cfg, scenario=sc, run_seed=0)
    m = result['metrics']
    ac = m['action_counts']
    # Sort action ids for readability
    ac_str = ' '.join(f'a{k}={v}' for k, v in sorted(ac.items()))
    print(f'  {label:18s} {ac_str}')

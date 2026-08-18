"""_smoke3.py — Test scenarios with different demand/renewable multipliers."""
from experiments.runner import run_single
from experiments.experiment_config import ExperimentConfig
from experiments.scenario_matrix import build_scenario, get_scenario_spec

# Try several scenarios
for slabel in ['A', 'B', 'E', 'H', 'I']:
    spec = get_scenario_spec(slabel)
    print(f"\n=== Scenario {slabel}: {spec.description} ===")
    for label in ['full_stack', 'no_lstm', 'no_twin', 'no_predictive', 'no_ems', 'dqn_core_only', 'rule_based', 'random']:
        cfg = ExperimentConfig(label=label)
        sc = build_scenario(seed=0, spec=spec)
        result = run_single(config=cfg, scenario=sc, run_seed=0)
        m = result['metrics']
        ens = m['energy_not_served_mwh']
        cmi = m['total_customer_minutes_interrupted']
        ppe = m['predictive_preparation_events']
        ems = m['ems_cycles']
        print(f'  {label:18s} ENS={ens:.4f} CMI={cmi:.2f} ppe={ppe} ems={ems}')

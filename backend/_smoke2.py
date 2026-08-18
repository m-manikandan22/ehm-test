"""_smoke2.py — Stage-42 smoke test: scenario H (degraded asset)."""
from experiments.runner import run_single
from experiments.experiment_config import ExperimentConfig
from experiments.scenario_matrix import build_scenario, get_scenario_spec

for label in ['full_stack', 'no_predictive', 'no_twin', 'dqn_core_only', 'rule_based', 'random']:
    cfg = ExperimentConfig(label=label)
    spec = get_scenario_spec('H')  # degraded asset
    sc = build_scenario(seed=0, spec=spec)
    result = run_single(config=cfg, scenario=sc, run_seed=0)
    m = result['metrics']
    ens = m['energy_not_served_mwh']
    cmi = m['total_customer_minutes_interrupted']
    ppe = m['predictive_preparation_events']
    ems = m['ems_cycles']
    print(f'{label:18s} ENS={ens:.4f} CMI={cmi:.2f} ppe={ppe} ems={ems}')

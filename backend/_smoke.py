"""_smoke.py — quick smoke test of Stage-42 info-flow wiring."""
from experiments.runner import run_single
from experiments.experiment_config import ExperimentConfig
from experiments.scenario import make_scenario

for label in ['full_stack', 'no_lstm', 'no_twin', 'no_predictive', 'no_ems', 'dqn_core_only', 'rule_based', 'random']:
    cfg = ExperimentConfig(label=label)
    sc = make_scenario(seed=0, total_steps=10, fault_count=1)
    result = run_single(config=cfg, scenario=sc, run_seed=0)
    m = result['metrics']
    ens = m['energy_not_served_mwh']
    cmi = m['total_customer_minutes_interrupted']
    rest = m['restoration_rate']
    ppe = m['predictive_preparation_events']
    ems = m['ems_cycles']
    lstm_n = m['lstm_forecast_samples']
    valid = result['validity']['valid']
    print(f'{label:18s} ENS={ens:.4f} CMI={cmi:.2f} rest={rest} ppe={ppe} ems={ems} lstm_n={lstm_n} valid={valid}')

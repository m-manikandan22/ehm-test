"""Stage 46.1 probe — Q-value sensitivity of the frozen checkpoint to
the LSTM / twin / storage features on a real scenario step.

Read-only diagnostic: loads the frozen checkpoint, builds one
deterministic scenario state, and compares Q(full_state) vs
Q(ablated_state) for the extended-feature block (positions 72-77).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch

from utils.seeds import set_global_seed
from simulation.grid import SmartGrid
from models.rl_agent import (
    DQNAgent, build_extended_state, EXTENDED_STATE_DIM,
)

CKPT = "experiments/checkpoints/dqn_stage44.pt"


def build_scenario_state(scenario_label: str, seed: int, step: int):
    from experiments.stage44_validation import (
        _build_scenario_for_seed, _apply_scenario_to_grid,
    )
    scenario = _build_scenario_for_seed(scenario_label, seed)
    set_global_seed(seed)
    grid = SmartGrid(seed=seed)
    _apply_scenario_to_grid(grid, scenario)
    try:
        grid.update_power_flow()
    except Exception:
        pass
    for t in range(step):
        for fault in scenario.faults:
            if fault.timestep == t:
                try:
                    grid.inject_failure(fault.target)
                except Exception:
                    pass
        try:
            grid.step()
        except Exception:
            pass
        try:
            grid.update_power_flow()
        except Exception:
            pass
    return grid, scenario


def q_values(agent, state):
    with torch.no_grad():
        q = agent.policy_net(torch.tensor(np.array(state, dtype=np.float32)).unsqueeze(0))
        return q[0].numpy()


def main():
    agent = DQNAgent.load_checkpoint(CKPT, state_dim=EXTENDED_STATE_DIM, eval_mode=True)
    print("agent state_dim:", agent.state_dim)

    from models.lstm_model import DemandForecaster
    fc = DemandForecaster()
    constant_forecast = float(fc.predict([[0.5, 0.4, 0.0]] * 10))

    for scen_label, seed, step in [("A", 0, 10), ("A", 0, 30), ("E", 0, 10), ("J", 0, 10)]:
        grid, scenario = build_scenario_state(scen_label, seed, step)
        rl_state = grid.get_rl_state()
        grid_state = grid.get_state()
        battery_soc = 0.0
        supercap_soc = 0.0
        for n in grid.nodes.values():
            if str(getattr(n, "node_type", "")) == "house":
                battery_soc = max(battery_soc, float(getattr(n, "battery_level", 0.0) or 0.0))
                supercap_soc = max(supercap_soc, float(getattr(n, "supercap_level", 0.0) or 0.0))

        full = build_extended_state(
            rl_state,
            predicted_load=constant_forecast,
            battery_soc=battery_soc,
            supercap_soc=supercap_soc,
            twin_max_risk=0.0, twin_mean_risk=0.0, twin_high_frac=0.0,
        )
        no_lstm = build_extended_state(
            rl_state,
            predicted_load=0.5,
            battery_soc=battery_soc,
            supercap_soc=supercap_soc,
            twin_max_risk=0.0, twin_mean_risk=0.0, twin_high_frac=0.0,
        )
        no_twin = build_extended_state(
            rl_state,
            predicted_load=constant_forecast,
            battery_soc=battery_soc,
            supercap_soc=supercap_soc,
            twin_max_risk=0.5, twin_mean_risk=0.3, twin_high_frac=0.1,
        )
        q_full = q_values(agent, full)
        q_no_lstm = q_values(agent, no_lstm)
        q_no_twin = q_values(agent, no_twin)

        print(f"\n=== {scen_label} seed={seed} step={step} | len(rl_state)={len(rl_state)} ===")
        print(f"  feat72 full={full[72]:.6f} no_lstm={no_lstm[72]:.6f} diff={full[72]-no_lstm[72]:+.6f}")
        print(f"  soc 73/74: battery={battery_soc:.3f} supercap={supercap_soc:.3f}")
        print(f"  Q_full    = {np.round(q_full, 6)}  argmax={int(q_full.argmax())}")
        print(f"  Q_no_lstm = {np.round(q_no_lstm, 6)}  argmax={int(q_no_lstm.argmax())}")
        print(f"  dQ_lstm   = {np.round(q_full - q_no_lstm, 6)}  norm={np.linalg.norm(q_full - q_no_lstm):.3e}")
        print(f"  Q_no_twin = {np.round(q_no_twin, 6)}  argmax={int(q_no_twin.argmax())}")
        print(f"  dQ_twin   = {np.round(q_full - q_no_twin, 6)}  norm={np.linalg.norm(q_full - q_no_twin):.3e}")


if __name__ == "__main__":
    main()
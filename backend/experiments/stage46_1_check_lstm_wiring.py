"""Stage 46.1 quick check — does the repaired harness now feed a
varying, real-history LSTM forecast to the DQN (and is the no_lstm
cell still the 0.5 sentinel)?
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.seeds import set_global_seed
from simulation.grid import SmartGrid
from models.rl_agent import build_extended_state, EXTENDED_STATE_DIM
from experiments.stage44_validation import (
    _build_scenario_for_seed, _apply_scenario_to_grid,
    _Stage44DQNAdapter, _build_dqn_agent, _get_shared_forecaster,
)
from models.rl_agent import DQNAgent

CKPT = "experiments/checkpoints/dqn_stage44.pt"


def main():
    scenario = _build_scenario_for_seed("A", 0)
    set_global_seed(0)
    grid = SmartGrid(seed=0)
    _apply_scenario_to_grid(grid, scenario)
    try:
        grid.update_power_flow()
    except Exception:
        pass

    agent = _build_dqn_agent(checkpoint=CKPT, seed=0)
    full = _Stage44DQNAdapter(agent, enable_lstm=True, enable_twin=True)
    nolm = _Stage44DQNAdapter(agent, enable_lstm=False, enable_twin=True)

    from collections import deque
    hist = deque(maxlen=10)
    full.set_lstm_history(hist)
    nolm.set_lstm_history(hist)
    weather_proxy = 0.2

    from experiments.info_flow import _aggregate_grid_load_and_gen

    fc_vals = []
    nol_vals = []
    for t in range(15):
        for fault in scenario.faults:
            if fault.timestep == t:
                try:
                    grid.inject_failure(fault.target)
                except Exception:
                    pass
        try:
            grid.update_power_flow()
        except Exception:
            pass
        _l, _g = _aggregate_grid_load_and_gen(grid)
        hist.append((_l, _g, weather_proxy))
        f_full = full._predicted_load()
        f_nol = nolm._predicted_load()
        fc_vals.append(f_full)
        nol_vals.append(f_nol)
        try:
            grid.step()
        except Exception:
            pass
        try:
            grid.update_power_flow()
        except Exception:
            pass

    print("full_stack forecasts (real history):", [round(v, 4) for v in fc_vals])
    print("no_lstm forecasts (sentinel):       ", [round(v, 4) for v in nol_vals])
    print("unique full_stack forecasts:", len(set(fc_vals)), "| range:", min(fc_vals), "-", max(fc_vals))
    print("max |full - no_lstm|:", max(abs(a - b) for a, b in zip(fc_vals, nol_vals)))
    print("varying:", len(set(fc_vals)) > 1)
    print("differs from sentinel:", max(abs(a - 0.5) for a in fc_vals) > 1e-6)


if __name__ == "__main__":
    main()
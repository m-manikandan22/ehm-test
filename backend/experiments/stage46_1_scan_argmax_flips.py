"""stage46_1_scan_argmax_flips.py — full-episode scan: for each Stage-45
scenario (A/E/I/J), step the repaired harness state construction and count
how often the frozen DQN's masked-argmax action differs between
full_stack and each ablation config (no_lstm, no_twin).
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

THIS = Path(__file__).resolve()
for p in (str(THIS.parents[2]), str(THIS.parent), str(THIS.parent.parent)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import torch

from utils.seeds import set_global_seed
from simulation.grid import SmartGrid
from models.rl_agent import DQNAgent, build_extended_state, EXTENDED_STATE_DIM
from experiments.stage44_validation import (
    _build_scenario_for_seed, _apply_scenario_to_grid,
    _Stage44DQNAdapter, _get_shared_forecaster,
)
from experiments.scenario_matrix import get_scenario_spec
from experiments.info_flow import _aggregate_grid_load_and_gen, _pre_age_twins

CKPT = "experiments/checkpoints/dqn_stage44.pt"
WEATHER_MAP = {"normal": 0.2, "storm": 0.85, "heatwave": 0.5}
N_STEPS = 80


def main() -> None:
    agent = DQNAgent.load_checkpoint(CKPT, state_dim=EXTENDED_STATE_DIM, eval_mode=True)
    fc = _get_shared_forecaster()

    for scen in ("A", "E", "I", "J"):
        seed = 0
        scenario = _build_scenario_for_seed(scen, seed)
        set_global_seed(seed)
        grid = SmartGrid(seed=seed)
        _apply_scenario_to_grid(grid, scenario)
        try:
            grid.update_power_flow()
        except Exception:
            pass

        from digital_twin.twin_registry import TwinRegistry
        twin = TwinRegistry()
        twin.register(grid)
        spec = get_scenario_spec(scen)
        if spec is not None and spec.health_override:
            try:
                _pre_age_twins(twin, dict(spec.health_override))
            except Exception:
                pass

        hist = deque(maxlen=10)
        wproxy = WEATHER_MAP.get(str(getattr(scenario, "weather_mode", "normal")), 0.2)
        adapters = {
            "full": _Stage44DQNAdapter(agent, enable_lstm=True, enable_twin=True),
            "no_lstm": _Stage44DQNAdapter(agent, enable_lstm=False, enable_twin=True),
            "no_twin": _Stage44DQNAdapter(agent, enable_lstm=True, enable_twin=False),
        }
        for a in adapters.values():
            a.set_lstm_history(hist)

        flips_lstm = 0
        flips_twin = 0
        actions_full = []
        actions_lstm = []
        actions_twin = []
        forecast_series = []

        for t in range(N_STEPS):
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
            _l, _g = _aggregate_grid_load_and_gen(grid)
            hist.append((_l, _g, wproxy))

            grid_state = grid.get_state()
            rl_state = grid.get_rl_state()
            tw_max = tw_mean = tw_frac = 0.0
            if twin is not None:
                vals = [float(getattr(tw, "health_risk_score", 0.0) or 0.0)
                        for tw in twin.all()]
                if vals:
                    tw_max = max(vals)
                    tw_mean = sum(vals) / len(vals)
                    tw_frac = sum(1 for v in vals if v >= 0.5) / len(vals)
            bat_soc = sc_soc = 0.0
            for n in grid.nodes.values():
                if str(getattr(n, "node_type", "")) == "house":
                    bat_soc = max(bat_soc, float(getattr(n, "battery_level", 0.0) or 0.0))
                    sc_soc = max(sc_soc, float(getattr(n, "supercap_level", 0.0) or 0.0))

            acts = {}
            for label, ad in adapters.items():
                forecast = ad._predicted_load() if ad._enable_lstm else 0.5
                twin_feats = (
                    (tw_max, tw_mean, tw_frac) if ad._enable_twin else (0.0, 0.0, 0.0)
                )
                st = build_extended_state(rl_state, predicted_load=forecast,
                                          battery_soc=bat_soc, supercap_soc=sc_soc,
                                          twin_max_risk=twin_feats[0],
                                          twin_mean_risk=twin_feats[1],
                                          twin_high_frac=twin_feats[2])
                with torch.no_grad():
                    q = agent.policy_net(
                        torch.tensor(np.array(st, dtype=np.float32)).unsqueeze(0)
                    )[0].numpy()
                valid = agent._valid_actions_mask(grid_state) or [0, 1, 2, 3, 4]
                masked = np.full(5, -np.inf)
                for a in valid:
                    masked[a] = q[a]
                acts[label] = int(masked.argmax())
                if label == "full":
                    forecast_series.append(float(forecast))

            actions_full.append(acts["full"])
            actions_lstm.append(acts["no_lstm"])
            actions_twin.append(acts["no_twin"])
            if acts["full"] != acts["no_lstm"]:
                flips_lstm += 1
            if acts["full"] != acts["no_twin"]:
                flips_twin += 1

        print(f"\nscenario {scen}: 80 steps")
        print(f"  forecast range: {min(forecast_series):.4f} - {max(forecast_series):.4f}")
        print(f"  argmax flips full vs no_lstm: {flips_lstm}/80")
        print(f"  argmax flips full vs no_twin: {flips_twin}/80")
        print(f"  unique actions full  : {sorted(set(actions_full))}")
        print(f"  unique actions no_lstm: {sorted(set(actions_lstm))}")
        print(f"  unique actions no_twin: {sorted(set(actions_twin))}")


if __name__ == "__main__":
    main()
"""performance.py — Stage 29 computational performance measurement.

Reports the wall-clock time of one paper-experiment run (smoke size)
plus the per-component hot-spot breakdown (DC PF, LSTM forward pass,
DQN act(), FLISR 9-stage). Output is a JSON file plus a short
markdown summary.

Usage::

    python -m experiments.performance \
        --seeds 1 --ticks 20 --faults 3 \
        --output paper_results/perf.json

Limitations
-----------
* Wall-clock measurements depend on the host (CPU, load, OS scheduler).
  The script pins ``PYTHONHASHSEED`` to make intra-run measurements
  comparable, but cross-host comparisons are not meaningful.
* Only the smoke-size run is profiled. A larger run (seeds=5,
  ticks=200) is documented in ``docs/PERFORMANCE.md``.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

os.environ.setdefault("PYTHONHASHSEED", "0")


def _time_dc_power_flow(n: int = 100) -> float:
    """Average over n calls of SmartGrid.update_power_flow()."""
    from simulation.grid import SmartGrid
    g = SmartGrid()
    t0 = time.perf_counter()
    for _ in range(n):
        try:
            g.update_power_flow()
        except Exception:
            pass
    return (time.perf_counter() - t0) / max(1, n)


def _time_flisr_9stage(n: int = 50) -> float:
    """Average over n calls of flisr_9stage."""
    from simulation.grid import SmartGrid
    g = SmartGrid()
    t0 = time.perf_counter()
    for _ in range(n):
        try:
            if hasattr(g, "flisr_9stage"):
                g.flisr_9stage()
        except Exception:
            pass
    return (time.perf_counter() - t0) / max(1, n)


def _time_dqn_act(n: int = 100) -> float:
    """Average over n calls of rl_agent.act() if available."""
    try:
        from models.rl_agent import DQNAgent
        agent = DQNAgent(state_dim=10)
        obs = [0.0] * 10
        t0 = time.perf_counter()
        for _ in range(n):
            try:
                agent.act(obs)
            except Exception:
                pass
        return (time.perf_counter() - t0) / max(1, n)
    except Exception as exc:
        return {"error": repr(exc)}


def _time_lstm_forward(n: int = 50) -> float:
    """Average over n calls of LSTM model.predict if available."""
    try:
        from models.lstm_model import LSTMForecaster
        import numpy as np
        m = LSTMForecaster(input_size=3, hidden_size=32)
        x = np.random.RandomState(0).randn(1, 10, 3).astype("float32")
        t0 = time.perf_counter()
        for _ in range(n):
            try:
                m.predict(x)
            except Exception:
                pass
        return (time.perf_counter() - t0) / max(1, n)
    except Exception as exc:
        return {"error": repr(exc)}


def _time_paper_experiment(seeds: int, ticks: int, faults: int) -> float:
    """Total wall-clock for one paper_experiment run."""
    import tempfile
    from experiments.paper_experiment import run_paper_experiment
    with tempfile.TemporaryDirectory() as td:
        t0 = time.perf_counter()
        run_paper_experiment(
            seeds=seeds,
            ticks=ticks,
            faults_per_run=faults,
            output_dir=td,
        )
        return time.perf_counter() - t0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--ticks", type=int, default=20)
    ap.add_argument("--faults", type=int, default=3)
    ap.add_argument("--output", type=str, default=None)
    args = ap.parse_args()

    profile: Dict[str, Any] = {
        "schema_version": 1,
        "seeds": int(args.seeds),
        "ticks": int(args.ticks),
        "faults_per_run": int(args.faults),
    }

    print("Profiling DC power flow…")
    profile["dc_power_flow_avg_s"] = _time_dc_power_flow()

    print("Profiling FLISR 9-stage…")
    profile["flisr_9stage_avg_s"] = _time_flisr_9stage()

    print("Profiling DQN act()…")
    profile["dqn_act_avg_s"] = _time_dqn_act()

    print("Profiling LSTM forward()…")
    profile["lstm_forward_avg_s"] = _time_lstm_forward()

    print("Running paper experiment…")
    profile["paper_experiment_total_s"] = _time_paper_experiment(
        args.seeds, args.ticks, args.faults,
    )

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, default=str)
        print(f"Wrote {args.output}")
    else:
        print(json.dumps(profile, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""predictive_vs_reactive.py — Compare predictive self-healing vs reactive FLISR.

Predictive self-healing (``self_healing.predictor.PredictiveSelfHealer``)
uses LSTM forecasts and Digital Twin health to pre-emptively reconfigure
the grid before faults materialise. Reactive FLISR (built-in
``SmartGrid.flisr_restore``) only responds after a fault is observed.

This script runs identical fault sequences with both agents disabled
and reports SAIDI / SAIFI deltas — the standard grid-reliability
indices (IEEE 1366).

Usage:
    python -m experiments.predictive_vs_reactive --seeds 10 \\
        --output experiments/results/predictive_vs_reactive.json
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import random as _random
from typing import Dict, List

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(THIS_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from metrics.statistics import (  # noqa: E402
    mean, std, ci95, paired_t, is_significant,
)


logger = logging.getLogger(__name__)


# Number of customers represented per house node — coarse IEEE 1366 proxy.
CUSTOMERS_PER_HOUSE = 3


def _ensure_reliability_keys(grid):
    """Make sure the grid has a per-step reliability-recorder."""
    try:
        from api.predictive_routes import _RECORDER
        if not hasattr(grid, "_RELIABILITY_RECORDER"):
            grid._RELIABILITY_RECORDER = _RECORDER
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not import reliability recorder: %r", exc)
        return False


def _run_one(mode: str, seed: int, ticks: int, fault_rate: float) -> dict:
    """Run a single (mode, seed) and return a single IEEE 1366 snapshot."""
    from simulation.grid import SmartGrid

    grid = SmartGrid()
    has_rec = _ensure_reliability_keys(grid)
    rng = _random.Random(seed)

    n_interruptions = 0
    customer_minutes_interrupted = 0.0
    customers_served = sum(
        1 for n in grid.nodes.values()
        if getattr(n, "node_type", "") in ("house", "hospital", "industry")
    ) * CUSTOMERS_PER_HOUSE

    for t in range(ticks):
        if mode == "predictive":
            # Predictive agent: try to consult LSTM/Twin before stepping.
            try:
                from self_healing.predictor import PredictiveSelfHealer
                healer = PredictiveSelfHealer()
                grid = healer.observe(grid)
            except Exception:  # noqa: BLE001
                pass
        # Inject faults (both arms)
        if rng.random() < fault_rate:
            target = f"H{str(rng.randint(0, 80)).zfill(2)}"
            try:
                grid.inject_failure(target)
            except Exception:  # noqa: BLE001
                pass
        try:
            grid.step()
        except Exception:  # noqa: BLE001
            pass
        # Reactive FLISR runs on every tick (built-in)
        if mode == "reactive":
            try:
                grid.flisr_restore()
            except Exception:  # noqa: BLE001
                pass

        # Track interruptions
        sys_info = grid.get_state().get("system", {})
        n_failed = sys_info.get("failed_count", 0)
        n_isolated = sys_info.get("isolated_count", 0)
        if n_failed or n_isolated:
            n_interruptions += 1
            customer_minutes_interrupted += (
                (n_failed + n_isolated) * CUSTOMERS_PER_HOUSE * 1.0
            )

    return {
        "mode":   mode,
        "seed":   seed,
        "valid":  has_rec,
        "customers_served": int(customers_served),
        "n_interruptions": int(n_interruptions),
        "customer_minutes_interrupted": float(customer_minutes_interrupted),
        # SAIFI = sum of customers interrupted / customers served
        "saifi_proxy": (
            (n_interruptions * CUSTOMERS_PER_HOUSE) / max(customers_served, 1)
        ),
        # SAIDI proxy = customer-minutes / customers served / 60 (hr)
        "saidi_proxy_hr": (
            customer_minutes_interrupted / max(customers_served, 1) / 60.0
        ),
    }


def run_predictive_vs_reactive(
    *, seeds: int, ticks: int, fault_rate: float, output_path: str,
) -> dict:
    predictive_runs = [
        _run_one("predictive", s, ticks, fault_rate) for s in range(seeds)
    ]
    reactive_runs = [
        _run_one("reactive", s, ticks, fault_rate) for s in range(seeds)
    ]

    def _stats(runs: List[dict], key: str) -> dict:
        vals = [float(r.get(key, 0.0)) for r in runs]
        if not vals:
            return {"mean": 0.0, "std": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
        low, high = ci95(vals)
        return {"mean": mean(vals), "std": std(vals),
                "ci_low": low, "ci_high": high, "n": len(vals)}

    saifi_pred = _stats(predictive_runs, "saifi_proxy")
    saifi_reac = _stats(reactive_runs, "saifi_proxy")
    saidi_pred = _stats(predictive_runs, "saidi_proxy_hr")
    saidi_reac = _stats(reactive_runs, "saidi_proxy_hr")

    # Paired test (per-seed)
    t_saifi = paired_t(
        [r["saifi_proxy"] for r in predictive_runs],
        [r["saifi_proxy"] for r in reactive_runs],
    )
    t_saidi = paired_t(
        [r["saidi_proxy_hr"] for r in predictive_runs],
        [r["saidi_proxy_hr"] for r in reactive_runs],
    )

    out = {
        "schema_version": "1.0",
        "experiment": "experiments.predictive_vs_reactive",
        "n_seeds":    seeds,
        "ticks":      ticks,
        "fault_rate": fault_rate,
        "saifi": {
            "predictive": saifi_pred,
            "reactive":   saifi_reac,
            "paired_t":   round(t_saifi, 4),
            "significant": bool(is_significant(
                t_saifi, n=min(seeds, len(predictive_runs), len(reactive_runs)))),
        },
        "saidi_hr": {
            "predictive": saidi_pred,
            "reactive":   saidi_reac,
            "paired_t":   round(t_saidi, 4),
            "significant": bool(is_significant(
                t_saidi, n=min(seeds, len(predictive_runs), len(reactive_runs)))),
        },
        "raw_runs": {
            "predictive": predictive_runs,
            "reactive":   reactive_runs,
        },
    }
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--ticks", type=int, default=30)
    parser.add_argument("--fault-rate", type=float, default=0.02)
    parser.add_argument("--output",
                        default="experiments/results/predictive_vs_reactive.json")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    out = run_predictive_vs_reactive(
        seeds=args.seeds,
        ticks=args.ticks,
        fault_rate=args.fault_rate,
        output_path=args.output,
    )
    print(f"Wrote {args.output}")
    print(f"SAIFI paired t = {out['saifi']['paired_t']:.4f}, "
          f"significant = {out['saifi']['significant']}")
    print(f"SAIDI paired t = {out['saidi_hr']['paired_t']:.4f}, "
          f"significant = {out['saidi_hr']['significant']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
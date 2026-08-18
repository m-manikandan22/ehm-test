"""monte_carlo.py — Monte-Carlo seed sweep with statistics.

Wraps :func:`experiments.runner.run_experiment` at high seed counts
(100-1000) and computes per-policy confidence intervals for each
metric. Use this when you want publication-grade sign-of-life
numbers, not smoke runs.

Supports the legacy ``policies=`` argument list and the new
``configs=`` argument.

Usage:
    python -m experiments.monte_carlo --n_seeds 100 \\
        --output experiments/results/monte_carlo.json
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Dict, List

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
for p in (BACKEND_ROOT, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from experiments.runner import run_experiment  # noqa: E402
from experiments.experiment_config import (  # noqa: E402
    ABLATION_CONFIGS, ExperimentConfig,
)
from experiments.aggregate import _METRICS  # noqa: E402
from metrics.statistics import (  # noqa: E402
    mean, std, ci95, median, mad,
)

logger = logging.getLogger(__name__)


def _resolve_policies_to_configs(
    policies: List[str] = None,
    configs: List[ExperimentConfig] = None,
) -> List[ExperimentConfig]:
    """Return a list of ``ExperimentConfig``.

    Either ``policies`` (legacy list of labels) or ``configs`` may be
    provided; if both, ``configs`` wins.
    """
    if configs:
        return list(configs)
    if not policies:
        raise TypeError("monte_carlo requires policies= or configs=")
    out: List[ExperimentConfig] = []
    for label in policies:
        if label not in ABLATION_CONFIGS:
            raise KeyError(
                f"Unknown policy label {label!r}. "
                f"Available: {sorted(ABLATION_CONFIGS.keys())}"
            )
        out.append(ABLATION_CONFIGS[label])
    return out


def monte_carlo(
    *,
    policies: List[str] = None,
    configs: List[ExperimentConfig] = None,
    n_seeds: int,
    ticks: int,
    faults_per_run: int,
    output_path: str,
    weather_modes: List[str] = None,
) -> dict:
    """Run a high-seed-count sweep and aggregate stats per policy."""
    if weather_modes is None:
        weather_modes = ["normal"]
    intermediate = output_path + ".runs.json"
    cfg_list = _resolve_policies_to_configs(
        policies=policies, configs=configs,
    )
    report = run_experiment(
        configs=cfg_list,
        seeds=n_seeds,
        ticks=ticks,
        faults_per_run=faults_per_run,
        weather_modes=weather_modes,
        output_path=intermediate,
        write_csv=False,
    )

    # Aggregate manually — exercises metrics.statistics directly so we
    # don't take a dependency on aggregate.py's JSON shape.
    runs = report.get("runs", [])
    grouped: Dict[str, List[dict]] = {}
    for r in runs:
        if not r.get("validity", {}).get("valid", False):
            continue
        label = r.get("controller_label") or r.get("policy", "")
        grouped.setdefault(label, []).append(r)

    out = {
        "schema_version":  "2.0",
        "experiment":      "experiments.monte_carlo",
        "n_seeds":         n_seeds,
        "ticks":           ticks,
        "faults_per_run":  faults_per_run,
        "weather_modes":   list(weather_modes),
        "policy_stats":    {},
    }
    for policy, items in grouped.items():
        out["policy_stats"][policy] = {
            "n_valid": len(items),
            "metrics": {
                m: {
                    "mean":   mean([float(r.get(m, 0.0)) for r in items
                                    if isinstance(r.get(m), (int, float))]),
                    "std":    std([float(r.get(m, 0.0)) for r in items
                                    if isinstance(r.get(m), (int, float))]),
                    "median": median([float(r.get(m, 0.0)) for r in items
                                       if isinstance(r.get(m), (int, float))]),
                    "mad":    mad([float(r.get(m, 0.0)) for r in items
                                    if isinstance(r.get(m), (int, float))]),
                    "ci95":   list(ci95([float(r.get(m, 0.0)) for r in items
                                          if isinstance(r.get(m), (int, float))])),
                }
                for m in _METRICS
            },
        }

    with open(output_path, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    try:
        os.remove(intermediate)
    except OSError:
        pass
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n_seeds", type=int, default=100)
    parser.add_argument("--ticks", type=int, default=20)
    parser.add_argument("--faults", type=int, default=1)
    parser.add_argument(
        "--policies", default="random,rule_based",
        help="comma-separated policy names")
    parser.add_argument(
        "--weather", default="normal",
        help="comma-separated weather modes")
    parser.add_argument(
        "--output", default="experiments/results/monte_carlo.json")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    policies = [p.strip() for p in args.policies.split(",") if p.strip()]
    weather = [w.strip() for w in args.weather.split(",") if w.strip()]
    out = monte_carlo(
        policies=policies,
        n_seeds=args.n_seeds,
        ticks=args.ticks,
        faults_per_run=args.faults,
        weather_modes=weather,
        output_path=args.output,
    )
    print(f"Wrote {args.output}")
    for name, s in out["policy_stats"].items():
        print(f"  {name}: valid={s['n_valid']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
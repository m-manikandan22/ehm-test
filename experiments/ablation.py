"""ablation.py — Drop-one-component ablation harness.

For each ablation configuration, runs ``runner.run_experiment`` with
the corresponding ``ExperimentConfig``. Each configuration has its
own boolean toggles (``enable_lstm``, ``enable_twin``,
``enable_predictive_healing``, ``enable_reward_shaping``) and the
runner genuinely honours them — flipping a flag alters runtime
behaviour, not just the label.

The output JSON includes:

  - ``per_config``: a summary per configuration with
    ``active_modules`` and ``disabled_modules`` so the reader can
    verify the configuration matches the description.
  - ``delta_vs_full``: each metric, expressed as a fraction of the
    full-stack value. This is the "each subsystem contributes how
    much?" answer.
  - ``status``: ``"real"`` once the runner is wired to use the
    actual ``ExperimentConfig`` booleans (PHASE 2 in the master plan).

Usage:
    python -m experiments.ablation --seeds 5 \\
        --output experiments/results/ablation.json
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

from metrics.statistics import mean as _stat_mean  # noqa: E402

from experiments.experiment_config import (  # noqa: E402
    ABLATION_CONFIGS, ExperimentConfig,
)
from experiments.runner import run_experiment  # noqa: E402


logger = logging.getLogger(__name__)


# The configurations we run for the ablation study. Order matters:
# ``full_stack`` is the reference; the others are each "minus one
# subsystem" variants.
ABLATION_CONFIG_LABELS: List[str] = [
    "full_stack",
    "no_lstm",
    "no_twin",
    "no_predictive",
    "no_reward",
    "dqn_core_only",
]


def _configs_for(labels: List[str], seed: int) -> List[ExperimentConfig]:
    out: List[ExperimentConfig] = []
    for label in labels:
        cfg = ABLATION_CONFIGS[label]
        # Build a fresh config so each call uses the seed passed in.
        out.append(ExperimentConfig(
            enable_dqn=cfg.enable_dqn,
            enable_lstm=cfg.enable_lstm,
            enable_twin=cfg.enable_twin,
            enable_predictive_healing=cfg.enable_predictive_healing,
            enable_reward_shaping=cfg.enable_reward_shaping,
            enable_flisr=cfg.enable_flisr,
            enable_ems=cfg.enable_ems,
            enable_storage=cfg.enable_storage,
            enable_xai=cfg.enable_xai,
            seed=seed, label=label,
        ))
    return out


def run_ablation(*, seeds: int, ticks: int, faults_per_run: int,
                  output_path: str,
                  labels: List[str] = None) -> dict:
    """Run each ablation configuration; return the aggregate report.

    Each configuration produces its own ``runner.json`` next to the
    final report so the raw evidence is preserved. The summary
    ``delta_vs_full`` is computed only over metrics that appear in
    every configuration, and only over valid runs.
    """
    if labels is None:
        labels = list(ABLATION_CONFIG_LABELS)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    base, _ = os.path.splitext(output_path)
    intermediate_paths: Dict[str, str] = {}

    for label in labels:
        intermediate_paths[label] = f"{base}.{label}.json"
        logger.info("Running ablation configuration '%s'", label)
        run_experiment(
            configs=_configs_for([label], seed=ABLATION_CONFIGS[label].seed),
            seeds=seeds, ticks=ticks, faults_per_run=faults_per_run,
            weather_modes=["normal"],
            output_path=intermediate_paths[label],
            write_csv=False,
        )

    # ── Aggregate ────────────────────────────────────────────────────
    per_config: Dict[str, Dict[str, object]] = {}
    raw_runs: Dict[str, List[dict]] = {}
    for label in labels:
        with open(intermediate_paths[label]) as f:
            raw = json.load(f)
        runs = raw.get("runs", [])
        valid = [r for r in runs if r.get("validity", {}).get("valid")]
        raw_runs[label] = valid
        # Pull the first run to grab the active/disabled modules list.
        cfg_dict = {}
        if valid:
            cfg_dict = valid[0].get("config", {}) or {}
        per_config[label] = {
            "n_runs":            len(runs),
            "n_valid":           len(valid),
            "valid_rate":        (len(valid) / len(runs)) if runs else 0.0,
            "active_modules":    cfg_dict.get("active_modules", []),
            "disabled_modules":  cfg_dict.get("disabled_modules", []),
        }

    # ── delta_vs_full ─────────────────────────────────────────────────
    # Mean of each metric, per config. Then compute
    #   (mean_x - mean_full) / max(|mean_full|, eps)
    # for every metric.
    metric_keys: List[str] = []
    for runs in raw_runs.values():
        for run in runs:
            for k in (run.get("metrics") or {}).keys():
                if k not in metric_keys and k != "faults":
                    metric_keys.append(k)

    means: Dict[str, Dict[str, float]] = {}
    for label, runs in raw_runs.items():
        means[label] = {}
        for k in metric_keys:
            vals = []
            for run in runs:
                v = (run.get("metrics") or {}).get(k)
                if isinstance(v, (int, float)):
                    vals.append(float(v))
            means[label][k] = _stat_mean(vals) if vals else float("nan")

    delta: Dict[str, Dict[str, float]] = {}
    full = means.get("full_stack", {})
    for label, m in means.items():
        if label == "full_stack":
            continue
        delta[label] = {}
        for k, v in m.items():
            ref = full.get(k)
            if ref is None or ref != ref:        # nan guard
                delta[label][k] = float("nan")
            elif abs(ref) < 1e-12:
                delta[label][k] = float("inf") if v > 0 else 0.0
            else:
                delta[label][k] = (v - ref) / abs(ref)

    out = {
        "schema_version":   "2.0",
        "experiment":       "experiments.ablation",
        "n_seeds":          seeds,
        "ticks":            ticks,
        "faults_per_run":   faults_per_run,
        "labels":           labels,
        "per_config":       per_config,
        # Legacy alias: ``ablations`` is what
        # ``tests/test_experiments_framework.py`` looks for.
        "ablations":        {
            label: {
                "label":      label,
                "n_runs":     info["n_runs"],
                "n_valid":    info["n_valid"],
                "valid_rate": info["valid_rate"],
            }
            for label, info in per_config.items()
        },
        "means":            means,
        "delta_vs_full":    delta,
        "status":           "real",
        "notes": [
            "Each ablation label corresponds to a genuine "
            "ExperimentConfig; the runner honours the boolean toggles. "
            "Inspect 'active_modules' / 'disabled_modules' to verify.",
        ],
    }

    with open(output_path, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True, default=str)
    return out


def _valid_rate(report: dict) -> float:
    runs = report.get("runs", [])
    if not runs:
        return 0.0
    valid = sum(1 for r in runs if r.get("valid"))
    return valid / len(runs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--ticks", type=int, default=20)
    parser.add_argument("--faults", type=int, default=1)
    parser.add_argument("--output",
                        default="experiments/results/ablation.json")
    parser.add_argument(
        "--labels", default=",".join(ABLATION_CONFIG_LABELS),
        help="Comma-separated ablation labels.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    labels = [s.strip() for s in args.labels.split(",") if s.strip()]
    out = run_ablation(
        seeds=args.seeds,
        ticks=args.ticks,
        faults_per_run=args.faults,
        output_path=args.output,
        labels=labels,
    )
    print(f"Wrote {args.output}")
    for name, s in out["per_config"].items():
        print(f"  {name}: valid={s['n_valid']}/{s['n_runs']} "
              f"active={s['active_modules']} disabled={s['disabled_modules']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
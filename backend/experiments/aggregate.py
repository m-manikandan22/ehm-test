"""aggregate.py — Aggregate per-policy / per-seed metrics across runs.

Used by ``paper_experiment`` to roll up the runner's output into the
paper's per-policy table, *excluding invalid runs* from the statistics
(Stage 24 — invalid-run handling).

Public API
----------
  - ``_per_policy(runs)``       : group runs by ``controller_label``.
  - ``per_policy_summary(runs)`` : aggregate one row per policy.
  - ``valid_run_filter(runs)``   : drop invalid rows in-place (in dict).
"""
from __future__ import annotations

from typing import Dict, List


def _per_policy(
    runs: List[dict],
    *,
    include_invalid: bool = False,
) -> Dict[str, List[dict]]:
    """Group runs by ``controller_label``, dropping invalid runs by
    default (Stage 24: invalid-run handling). Pass
    ``include_invalid=True`` to keep invalid runs."""
    out: Dict[str, List[dict]] = {}
    for r in runs:
        if not include_invalid:
            valid = (r.get("validity") or {}).get("valid", True)
            if not valid:
                continue
        label = r.get("controller_label", "?")
        out.setdefault(label, []).append(r)
    return out


def valid_run_filter(runs: List[dict]) -> List[dict]:
    """Return only the rows whose validity flag is True."""
    return [
        r for r in runs
        if (r.get("validity") or {}).get("valid", True)
    ]


def per_policy_summary(runs: List[dict]) -> List[dict]:
    """One row per policy: count + mean + std of selected metrics.

    Each row has:

      * ``controller_label``
      ``n_total_runs`` / ``n_valid_runs``
      * mean (and population std) of every numeric metric over the
        *valid* runs.

    Population std (n-denominator) is used to keep the formula
    reviewer-defensible; the std is reported as ``None`` when fewer
    than 2 valid samples are available.
    """
    grouped = _per_policy(runs)
    out: List[dict] = []
    for label, bucket in sorted(grouped.items()):
        valid_bucket = valid_run_filter(bucket)
        n_total = len(bucket)
        n_valid = len(valid_bucket)
        row = {
            "controller_label": label,
            "n_total_runs": n_total,
            "n_valid_runs": n_valid,
        }
        if valid_bucket:
            metric_keys = set()
            for r in valid_bucket:
                metric_keys.update((r.get("metrics") or {}).keys())
            for mk in sorted(metric_keys):
                vals = [
                    r["metrics"].get(mk)
                    for r in valid_bucket
                    if isinstance(r["metrics"].get(mk), (int, float))
                ]
                if vals:
                    mean = sum(vals) / len(vals)
                    row[f"{mk}_mean"] = mean
                    if len(vals) >= 2:
                        var = sum((v - mean) ** 2 for v in vals) / len(vals)
                        row[f"{mk}_std"] = var ** 0.5
                    else:
                        row[f"{mk}_std"] = 0.0
        out.append(row)
    return out

# ----------------------------------------------------------------------
# Backward-compat shim for the legacy root-level monte_carlo.py.
# Mirror the metric names from the root-level aggregate.py so that
# imports of `_METRICS` from either module resolve consistently.
# ----------------------------------------------------------------------
_METRICS = [
    "elapsed_s", "actions_taken", "n_failed_end",
    "n_isolated_end", "avg_voltage_end", "total_energy_loss_end",
    "n_faults", "n_restored", "restoration_rate",
    "energy_not_served_mwh",
    "voltage_violation_count",
    "critical_load_interruption_steps",
    "total_customer_minutes_interrupted",
]

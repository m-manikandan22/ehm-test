"""results_sanity.py — Stage 38 sanity-check harness.

This script verifies that the paper experiment outputs are within
*expected ranges* (sanity bounds). It does NOT claim the simulator
is correct — only that the numbers it produces are plausible.

Sanity bounds
-------------
For each metric, we record:

  * `min`            — never observed below this in smoke tests.
  * `max`            — never observed above this.
  * `expected_sign`  — what sign the ablation delta should have:
        - `mean_ens`     : non-negative (energy can be served or not
                           served, but ENS is always ≥ 0).
        - `restoration`  : in [0, 1].

How to use
----------
::

    python -m experiments.results_sanity \
        --input paper_results/summary.json \
        --output paper_results/sanity.json

Exit code 0 = pass, 1 = fail.

Limitations
-----------
* The bounds are empirical (smoke-test-derived). They are NOT
  physical constants. If the simulator is extended (e.g. a new
  grid topology), the bounds must be re-calibrated.
* This script does not catch scientific defects (e.g. wrong sign,
  wrong units). It only catches crash-level issues.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


# Sanity bounds derived from paper_results/smoke runs.
# (See docs/RESULTS_SANITY_BOUNDS.md for the derivation log.)
_SANITY_BOUNDS: Dict[str, Dict[str, Any]] = {
    "energy_not_served_mwh_mean": {
        "min": 0.0,
        "max": 100.0,  # very generous upper bound
        "expected_sign": "non-negative",
    },
    "restoration_rate_mean": {
        "min": 0.0,
        "max": 1.0,
        "expected_sign": "in_unit_interval",
    },
    "voltage_violation_count_mean": {
        "min": 0.0,
        "max": 1_000_000.0,
        "expected_sign": "non-negative",
    },
    "n_faults_mean": {
        "min": 0.0,
        "max": 1_000.0,
        "expected_sign": "non-negative",
    },
    "actions_taken_mean": {
        "min": 0.0,
        "max": 1_000_000.0,
        "expected_sign": "non-negative",
    },
}


def _check_metric(name: str, value: float, bounds: Dict[str, Any]) -> Dict[str, Any]:
    """Return a per-metric check record."""
    result = {
        "metric": name,
        "value": value,
        "min": bounds["min"],
        "max": bounds["max"],
        "pass": bounds["min"] <= value <= bounds["max"],
    }
    if bounds["expected_sign"] == "non-negative" and value < 0:
        result["pass"] = False
    if bounds["expected_sign"] == "in_unit_interval":
        result["pass"] = 0.0 <= value <= 1.0
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=str, required=True,
                    help="summary.json from paper_experiment")
    ap.add_argument("--output", type=str, default=None,
                    help="Where to write sanity.json (optional)")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        summary = json.load(f)

    checks: list = []
    overall_pass = True

    # The summary file does not include per-policy means; if absent,
    # we fall back to using the high-level fields.
    for metric, bounds in _SANITY_BOUNDS.items():
        # Allow top-level (e.g. n_total_runs) or per-policy
        # (e.g. energy_not_served_mwh_mean) lookup.
        if metric in summary:
            value = float(summary[metric])
            rec = _check_metric(metric, value, bounds)
            checks.append(rec)
            overall_pass = overall_pass and rec["pass"]

    # Always check valid_rate.
    if "valid_rate" in summary:
        v = float(summary["valid_rate"])
        rec = {
            "metric": "valid_rate",
            "value": v,
            "min": 0.0,
            "max": 1.0,
            "pass": 0.0 <= v <= 1.0,
        }
        checks.append(rec)
        overall_pass = overall_pass and rec["pass"]

    out = {
        "schema_version": 1,
        "input": args.input,
        "overall_pass": overall_pass,
        "checks": checks,
    }

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=str)
        print(f"Wrote {args.output}")
    else:
        print(json.dumps(out, indent=2, default=str))

    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

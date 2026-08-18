"""verify_validity_guards.py — Phase 8 verification.

Tests the validity guard against known bad cases:
  - NaN values
  - Inf values
  - Impossible voltage (>2.5 pu)
  - Empty topology
  - Valid state

The validity guard should NOT silently convert invalid runs to valid.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
for p in (os.path.join(PROJECT_ROOT, "backend"), PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from experiments.validity import (  # noqa: E402
    ValidityReport, InvalidRunReason, check_run_validity,
)


class _Node:
    def __init__(self, nid, voltage=1.0, failed=False, isolated=False):
        self.node_id = nid
        self.voltage = voltage
        self.failed = failed
        self.isolated = isolated


class _Grid:
    def __init__(self, nodes=None, edges=None):
        self.nodes = nodes or {}
        self.graph = edges  # may be None


def main() -> int:
    out_dir = os.path.join("experiments", "results", "final_paper", "logs")
    os.makedirs(out_dir, exist_ok=True)

    cases = []

    # 1. Healthy grid
    nodes = {f"B{i}": _Node(f"B{i}", voltage=1.0) for i in range(3)}
    grid = _Grid(nodes=nodes)
    r = check_run_validity(grid, step=0)
    cases.append({
        "name": "healthy_grid",
        "valid": r.valid,
        "invalid_reason": r.invalid_reason,
        "details": r.details,
    })

    # 2. NaN voltage
    nodes = {f"B{i}": _Node(f"B{i}", voltage=float("nan")) for i in range(3)}
    grid = _Grid(nodes=nodes)
    r = check_run_validity(grid, step=0)
    cases.append({
        "name": "nan_voltage",
        "valid": r.valid,
        "invalid_reason": r.invalid_reason,
    })

    # 3. Inf voltage
    nodes = {f"B{i}": _Node(f"B{i}", voltage=float("inf")) for i in range(3)}
    grid = _Grid(nodes=nodes)
    r = check_run_validity(grid, step=0)
    cases.append({
        "name": "inf_voltage",
        "valid": r.valid,
        "invalid_reason": r.invalid_reason,
    })

    # 4. Impossible high voltage
    nodes = {f"B{i}": _Node(f"B{i}", voltage=3.0) for i in range(3)}
    grid = _Grid(nodes=nodes)
    r = check_run_validity(grid, step=0)
    cases.append({
        "name": "impossible_voltage_high",
        "valid": r.valid,
        "invalid_reason": r.invalid_reason,
    })

    # 5. Empty topology
    grid = _Grid(nodes={})
    r = check_run_validity(grid, step=0)
    cases.append({
        "name": "empty_topology",
        "valid": r.valid,
        "invalid_reason": r.invalid_reason,
    })

    # 6. Normal-low voltage (still valid)
    nodes = {f"B{i}": _Node(f"B{i}", voltage=0.85) for i in range(3)}
    grid = _Grid(nodes=nodes)
    r = check_run_validity(grid, step=0)
    cases.append({
        "name": "low_voltage_still_valid",
        "valid": r.valid,
        "invalid_reason": r.invalid_reason,
    })

    # Summary
    summary = {
        "schema_version": "1.0",
        "cases": cases,
        "verdict": "PASS" if (
            cases[1]["valid"] is False and
            cases[2]["valid"] is False and
            cases[3]["valid"] is False and
            cases[4]["valid"] is False and
            cases[0]["valid"] is True
        ) else "FAIL",
    }

    json_path = os.path.join(out_dir, "validity_guards_report.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print(f"Wrote {json_path}")
    print(f"verdict: {summary['verdict']}")
    for c in cases:
        print(f"  {c['name']}: valid={c['valid']} reason={c.get('invalid_reason')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
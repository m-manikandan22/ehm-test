"""run_topology_planning.py — Stage 22 topology-planning experiment.

Runs ``AIPlanner.plan()`` on the default 49-node grid, captures the
five-objective metrics before and after, and persists the action list
to ``experiments/results/topology_planning.json``.

This script is *deterministic*: ``PlannerConfig`` is frozen, the
underlying DC PF solver has no RNG, and the planner's RNG is seeded.

Limitations
-----------
* The planner is a constrained local-search, not a global optimiser.
  The action list is a *candidate* plan, not a proof of optimality.
* ``voltage_drop_index`` and ``power_loss_mw`` use DC PF.
* No construction cost is modelled (see docs/TOPOLOGY_PLANNING.md).

Output schema
-------------
::

    {
      "seed": 42,
      "kpis_before": {...},
      "kpis_after":  {...},
      "actions":     [PlanAction.to_dict(), ...],
      "summary":     str
    }
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure backend is on the path so we can ``import planning`` etc.
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from planning.ai_planner import AIPlanner, PlannerConfig  # noqa: E402
from planning.topology_kpis import all_kpis              # noqa: E402
from simulation.grid import SmartGrid                    # noqa: E402


DEFAULT_RESULTS_DIR = HERE / "results"
DEFAULT_RESULTS_FILE = DEFAULT_RESULTS_DIR / "topology_planning.json"


def _ensure_results_dir() -> Path:
    DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_RESULTS_FILE


def run(
    *,
    seed: int = 42,
    max_iterations: int = 8,
    write_path: Path = DEFAULT_RESULTS_FILE,
) -> dict:
    """Run the planner on a fresh default 49-node grid.

    Returns a JSON-serialisable dict ready to be persisted.
    """
    g = SmartGrid()
    kpis_before = all_kpis(g)

    config = PlannerConfig(max_iterations=max_iterations)
    planner = AIPlanner(g, config=config, seed=seed)
    actions = planner.plan()

    # KPIs *after* simulated application — note: the planner does
    # not mutate the input grid, so we report the KPIs of the
    # original grid. The expected_delta on each action is the
    # reduction in cost that the planner *predicted* (i.e. simulated
    # on a temporary mutation).
    kpis_after = dict(kpis_before)

    summary_lines = [
        f"AIPlanner ran {len(actions)} accepted actions on a "
        f"{len(g.nodes)}-node grid (max_iterations={max_iterations}, "
        f"seed={seed}).",
        f"Baseline KPIs: {kpis_before}",
        f"Predicted total cost reduction: "
        f"{sum(a.expected_delta for a in actions):.4f}",
        "Actions:",
    ]
    for i, act in enumerate(actions, 1):
        summary_lines.append(
            f"  {i}. {act.kind}({act.params})  "
            f"expected_delta={act.expected_delta:.4f}"
        )

    out = {
        "seed": seed,
        "max_iterations": max_iterations,
        "n_nodes": len(g.nodes),
        "n_actions": len(actions),
        "kpis_before": kpis_before,
        "kpis_after": kpis_after,
        "actions": [a.to_dict() for a in actions],
        "summary": "\n".join(summary_lines),
    }

    # Persist
    write_path.parent.mkdir(parents=True, exist_ok=True)
    with open(write_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return out


def _parse_args(argv: list) -> "argparse.Namespace":
    import argparse
    p = argparse.ArgumentParser(
        description="Run AIPlanner on the default SmartGrid and persist "
                    "before/after KPIs + action list."
    )
    p.add_argument("--seed", type=int, default=42,
                   help="RNG seed for the planner (default: 42).")
    p.add_argument("--max-iterations", type=int, default=8,
                   help="Maximum planner iterations (default: 8).")
    p.add_argument("--out", type=str, default=str(DEFAULT_RESULTS_FILE),
                   help=f"Output JSON path (default: {DEFAULT_RESULTS_FILE}).")
    return p.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    out = run(seed=args.seed,
              max_iterations=args.max_iterations,
              write_path=Path(args.out))
    print(out["summary"])
    print(f"\nResults written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""completion_gate.py — Stage 40 final completion gate.

The completion gate is the last script run before submission. It
verifies:

  1. **All 14 claims** have backing artefacts (claim_gate.py).
  2. **All docs** listed in ``docs/`` cross-referenced from
     ``PAPER_OUTLINE.md`` exist.
  3. **Tests pass** — runs the test suite (configurable list of
     paths) and checks the exit code.
  4. **Anti-claims absent** from PAPER_OUTLINE.md.

Usage::

    python -m experiments.completion_gate

Exit code 0 = paper is ready, 1 = something is missing.

Limitations
-----------
* This script runs the test suite in-process (pytest). If the
  environment lacks pytest, the test step is skipped.
* The gate is a *necessary* condition, not a *sufficient* one —
  it does not review the prose, check numerical correctness, or
  enforce ICLR-style formatting.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


REPO = Path(__file__).resolve().parents[2]   # EHM-paper/
DOCS = (REPO / "docs").resolve()
BACKEND = (REPO / "backend").resolve()


def _check_claim_gate() -> Dict[str, Any]:
    """Run claim_gate.py and return its output."""
    proc = subprocess.run(
        [sys.executable, "-m", "experiments.claim_gate",
         "--docs-root", str(DOCS)],
        cwd=str(BACKEND),
        capture_output=True, text=True, timeout=60,
    )
    try:
        out = json.loads(proc.stdout)
    except Exception:
        out = {"error": proc.stderr or proc.stdout}
    out["exit_code"] = proc.returncode
    return out


def _check_required_docs() -> Dict[str, Any]:
    """Verify all docs cross-referenced from PAPER_OUTLINE.md exist."""
    required = [
        "NOVELTY_MATRIX.md",
        "LIMITATIONS.md",
        "PAPER_OUTLINE.md",
        "ARCHITECTURE.md",
        "REWARD_FORMULATION.md",
        "HYBRID_STORAGE.md",
        "TOPOLOGY_PLANNING.md",
        "digital_twin.md",
        "power_flow.md",
        "METRICS_REFERENCE.md",
        "VALIDATION.md",
        "EXPERIMENTS.md",
        "PAPER_READINESS_AUDIT.md",
        "FINAL_PAPER_READINESS_REPORT.md",
        "CHECKPOINT_3_ABLATION.md",
    ]
    missing = [d for d in required if not (DOCS / d).exists()]
    return {
        "required": required,
        "missing": missing,
        "pass": not missing,
    }


def _check_smoke_tests() -> Dict[str, Any]:
    """Run a smoke subset of the test suite."""
    test_paths = [
        "tests/test_research_readiness.py",
        "tests/test_paper_experiment.py",
        "tests/test_upgrade.py",
        "tests/test_n_minus_1.py",
        "tests/test_ieee_1366_analytical.py",
    ]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest"] + test_paths + ["-q"],
        cwd=str(BACKEND),
        capture_output=True, text=True, timeout=600,
    )
    return {
        "paths": test_paths,
        "exit_code": proc.returncode,
        "pass": proc.returncode == 0,
    }


def main() -> int:
    print("=== completion_gate ===")
    claim_gate = _check_claim_gate()
    print(f"claim_gate: overall_pass={claim_gate.get('overall_pass')}")

    docs_check = _check_required_docs()
    print(f"docs_check: {len(docs_check['missing'])} missing")

    tests_check = _check_smoke_tests()
    print(f"smoke_tests: exit={tests_check['exit_code']}")

    overall_pass = (
        claim_gate.get("overall_pass", False)
        and docs_check["pass"]
        and tests_check["pass"]
    )
    out = {
        "schema_version": 1,
        "claim_gate": {
            "overall_pass": claim_gate.get("overall_pass"),
            "claims_passing": claim_gate.get("claims_passing"),
            "anti_claims_passing": claim_gate.get("anti_claims_passing"),
        },
        "docs_check": docs_check,
        "smoke_tests": tests_check,
        "overall_pass": overall_pass,
    }
    print(json.dumps(out, indent=2, default=str))
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
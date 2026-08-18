"""claim_gate.py — Stage 36 verification harness.

The claim gate enforces that every claim in
``docs/NOVELTY_MATRIX.md`` §1 has a corresponding backing artefact
(file, test, or experiment). It also enforces that no anti-claim
(novelty claim) from §2 of the same file is present in the paper
manuscript.

Usage::

    python -m experiments.claim_gate --docs-root ../docs

Exit code 0 = pass, 1 = fail.

Limitations
-----------
* The gate is *static* — it parses the NOVELTY_MATRIX.md and
  PAPER_OUTLINE.md and checks that the documented evidence paths
  exist on disk. It does not run the experiments.
* The gate does not enforce numerical correctness — it only checks
  that the *documented* claims are honest and the *documented*
  evidence exists.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List


# Claims from NOVELTY_MATRIX.md §1 — 14 rows.
# Evidence paths are relative to backend/ (the "backend_root").
_CLAIMS: List[Dict[str, Any]] = [
    {"id": 1, "evidence": ["simulation", "models", "rl",
                            "self_healing", "metrics",
                            "digital_twin", "../docs/EXPERIMENTS.md",
                            "../docs/ARCHITECTURE.md"]},
    {"id": 2, "evidence": ["utils/seeds.py", "experiments/runner.py"]},
    {"id": 3, "evidence": ["simulation/grid.py",
                            "reliability/n_minus_1.py"]},
    {"id": 4, "evidence": ["experiments/run_hybrid_storage.py"]},
    {"id": 5, "evidence": ["reliability/n_minus_1.py",
                            "tests/test_n_minus_1.py"]},
    {"id": 6, "evidence": ["simulation/power_flow.py",
                            "tests/test_ieee33.py"]},
    {"id": 7, "evidence": ["models/lstm_model.py",
                            "tests/test_lstm_no_leakage.py"]},
    {"id": 8, "evidence": ["models/rl_agent.py",
                            "tests/test_dqn_eval_mode.py"]},
    {"id": 9, "evidence": ["digital_twin",
                            "tests/test_digital_twin.py"]},
    {"id": 10, "evidence": ["metrics/ieee_1366.py",
                             "tests/test_ieee_1366_analytical.py"]},
    {"id": 11, "evidence": ["experiments/ablation.py",
                             "tests/test_research_readiness.py"]},
    {"id": 12, "evidence": ["planning/ai_planner.py",
                             "tests/test_run_topology_planning.py"]},
    {"id": 13, "evidence": ["experiments/aggregate.py",
                             "tests/test_research_readiness.py"]},
    {"id": 14, "evidence": ["metrics/statistics.py",
                             "tests/test_upgrade.py"]},
]


# Anti-claims from NOVELTY_MATRIX.md §2 — must NOT appear in PAPER_OUTLINE.md
# in *positive* form. Disclaimers like "no real-world validation" and
# "not novel algorithm" count as *honest* and pass.
# Each pattern is a 2-tuple: (literal, regex that *flags* positive usage).
_ANTI_CLAIMS: List[Dict[str, str]] = [
    {"anti_claim": "LSTM is novel for load forecasting",
     "flag_pattern": r"novel lstm|i invent.*lstm|first.*lstm.*load"},
    {"anti_claim": "DQN is novel for grid control",
     "flag_pattern": r"novel dqn|i invent.*dqn|first.*dqn.*grid"},
    {"anti_claim": "FLISR is novel as a pipeline",
     "flag_pattern": r"novel flisr|i invent.*flisr|first.*flisr"},
    {"anti_claim": "Hybrid storage is novel",
     "flag_pattern": r"novel storage|hybrid storage is novel"},
    {"anti_claim": "Real-world validation",
     "flag_pattern": r"real-world validation shows|field.*proves|we prove.*real-world"},
    {"anti_claim": "Real-world deployment benefit",
     "flag_pattern": r"real-world deployment proves|field test proves"},
]


def _check_evidence(repo_root: Path, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Verify each claim's evidence exists on disk."""
    results: List[Dict[str, Any]] = []
    for c in claims:
        missing = []
        for ev in c["evidence"]:
            p = repo_root / ev
            if not p.exists():
                missing.append(ev)
        results.append({
            "claim_id": c["id"],
            "missing_evidence": missing,
            "pass": len(missing) == 0,
        })
    return results


def _check_no_anti_claims(outline_path: Path) -> List[Dict[str, Any]]:
    """Verify no anti-claim text appears in PAPER_OUTLINE.md."""
    results: List[Dict[str, Any]] = []
    if not outline_path.exists():
        return [{"anti_claim": "?", "pass": False,
                 "reason": "PAPER_OUTLINE.md not found"}]
    text = outline_path.read_text(encoding="utf-8")
    for anti in _ANTI_CLAIMS:
        pattern = anti["flag_pattern"]
        flagged = bool(re.search(pattern, text, flags=re.IGNORECASE))
        results.append({
            "anti_claim": anti["anti_claim"],
            "flagged": flagged,
            "pass": not flagged,
        })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docs-root", type=str, default="../docs",
                    help="Path to docs/ directory.")
    ap.add_argument("--backend-root", type=str, default=".",
                    help="Path to backend/ directory (parent of utils/, "
                         "backend/, etc.).")
    args = ap.parse_args()

    backend_root = Path(args.backend_root).resolve()
    docs_root = Path(args.docs_root).resolve()

    claim_results = _check_evidence(backend_root, _CLAIMS)
    anti_results = _check_no_anti_claims(docs_root / "PAPER_OUTLINE.md")

    overall_pass = (
        all(c["pass"] for c in claim_results)
        and all(a["pass"] for a in anti_results)
    )

    out = {
        "schema_version": 1,
        "backend_root": str(backend_root),
        "claims_total": len(_CLAIMS),
        "claims_passing": sum(1 for c in claim_results if c["pass"]),
        "anti_claims_total": len(_ANTI_CLAIMS),
        "anti_claims_passing": sum(1 for a in anti_results if a["pass"]),
        "overall_pass": overall_pass,
        "claim_results": claim_results,
        "anti_claim_results": anti_results,
    }

    print(json.dumps(out, indent=2, default=str))
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

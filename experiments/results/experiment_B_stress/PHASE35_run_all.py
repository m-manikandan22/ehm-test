"""
PHASE 35 — Master automation: post-run pipeline.

This script runs the post-run phases that need to be re-runnable
against the freshly-generated experiment_B_runs.json. The order
is: statistics → figures → text reports → package → integrity audit.

Run from project root with EHM-paper:

    C:/Users/ELCOT/miniconda3/envs/EHM-paper/python.exe \
        experiments/results/experiment_B_stress/PHASE35_run_all.py
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import List


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(THIS_DIR)))
EHM_PAPER_PY = (
    r"C:\Users\ELCOT\miniconda3\envs\EHM-paper\python.exe"
)


def _run(script: str, args: List[str]) -> int:
    cmd = [EHM_PAPER_PY, os.path.join(THIS_DIR, script)] + list(args)
    print(f"\n=== {script} {' '.join(args)} ===")
    res = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return res.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs",
                    default="experiments/results/experiment_B_stress/experiment_B_runs.json")
    ap.add_argument("--out-dir", default="paper_results_experiment_B")
    args = ap.parse_args()

    eb_dir = os.path.dirname(args.runs)
    plan = [
        # 1. Statistics (Wilcoxon + Holm + Cliff's delta).
        ("PHASE21_statistics.py",
            ["--input", args.runs,
             "--output-dir", eb_dir]),
        # 2. Resilience curves (text summary).
        ("PHASE23_resilience_curves.py",
            ["--runs", args.runs,
             "--output",
             os.path.join(args.out_dir, "reports", "RESILIENCE_CURVES.md")]),
        # 3. Failure cases.
        ("PHASE24_failure_cases.py",
            ["--runs", args.runs,
             "--output",
             os.path.join(args.out_dir, "reports", "FAILURE_CASE_ANALYSIS.md")]),
        # 4. A vs B numerical comparison.
        ("PHASE26_compute_a_vs_b.py",
            ["--exp-a", "paper_results/raw/baseline_results.json",
             "--exp-b", args.runs,
             "--output-dir", os.path.join(args.out_dir, "tables")]),
        # 5. Figures.
        ("PHASE27_figures.py",
            ["--input", args.runs,
             "--output-dir", os.path.join(args.out_dir, "figures"),
             "--experiment-a", "paper_results/raw/baseline_results.json"]),
        # 6. Final package assembly.
        ("PHASE29_final_package.py", []),
        # 7. Claim audit.
        ("PHASE31_claim_audit.py", []),
        # 8. Scientific wording audit.
        ("PHASE32_scientific_wording.py", []),
        # 9. Final integrity audit.
        ("PHASE34_integrity_audit.py", []),
    ]
    failed = []
    for script, sargs in plan:
        rc = _run(script, sargs)
        if rc != 0:
            failed.append((script, rc))
    if failed:
        print(f"\nFAILED: {failed}")
        return 1
    print("\nALL PHASES OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

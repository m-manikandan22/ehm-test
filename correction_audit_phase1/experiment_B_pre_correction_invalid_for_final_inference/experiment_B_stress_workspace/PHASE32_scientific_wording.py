"""
PHASE 32 — Scientific-wording audit.

Scans EXPERIMENT_B_FINAL_RESULTS.md and EXPERIMENT_B_CLAIM_AUDIT.md
for words that imply stronger-than-supported claims. If any of
those words appear without context, the audit flags them.

The script never modifies the text — it only reports. The author
then chooses whether to soften the wording.

Run from project root with EHM-paper:

    C:/Users/ELCOT\miniconda3\envs\EHM-paper\python.exe \
        experiments/results/experiment_B_stress/PHASE32_scientific_wording.py
"""
from __future__ import annotations

import argparse
import os
import re
from typing import Any, Dict, List


OVERCONFIDENT_PHRASES = [
    r"\bproves?\b",
    r"\bguarantees?\b",
    r"\boptimal\b",
    r"\bindustry[- ]proven\b",
    r"\bvalidated\s+on\s+(real|hardware)\b",
    r"\bdeployed\s+in\s+production\b",
    r"\bstate[- ]of[- ]the[- ]art\b",
    r"\bsuperior\s+to\s+all\b",
    r"\boutperforms?\s+(every|all|any)\b",
    r"\bbest[- ]in[- ]class\b",
]

SAFE_PHRASES = [
    r"under the tested simulation conditions",
    r"simulation results indicate",
    r"statistically detectable",
    r"the proposed framework",
    r"balanced positive-sequence equivalent",
    r"relative failure-risk indicator",
    r"relative digital-twin risk",
]


def _scan(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    findings = []
    for pat in OVERCONFIDENT_PHRASES:
        for m in re.finditer(pat, text, flags=re.IGNORECASE):
            findings.append({
                "file": path,
                "phrase": m.group(0),
                "offset": m.start(),
            })
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--report",
        default="experiments/results/experiment_B_stress/EXPERIMENT_B_FINAL_RESULTS.md",
    )
    ap.add_argument(
        "--claim-audit",
        default="experiments/results/experiment_B_stress/EXPERIMENT_B_CLAIM_AUDIT.md",
    )
    ap.add_argument(
        "--output",
        default="experiments/results/experiment_B_stress/validation/SCIENTIFIC_WORDING_AUDIT.md",
    )
    args = ap.parse_args()

    findings = _scan(args.report) + _scan(args.claim_audit)
    out = []
    out.append("# SCIENTIFIC WORDING AUDIT\n")
    out.append(
        "This document audits the wording of the final-results "
        "documents for over-confident phrases. If any appear, the "
        "author is asked to soften them to be consistent with the "
        "level of evidence.\n"
    )
    if not findings:
        out.append(
            "**No over-confident phrases detected.** The wording is "
            "consistent with the level of evidence.\n"
        )
    else:
        out.append("| File | Phrase | Offset |")
        out.append("|---|---|---|")
        for f in findings:
            out.append(f"| {f['file']} | `{f['phrase']}` | {f['offset']} |")
        out.append("")
        out.append(
            "**Action required.** Each flagged phrase should be "
            "softened to one of the safe phrases below:\n"
        )
        for safe in SAFE_PHRASES:
            out.append(f"- `{safe}`")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"Wrote {args.output}")
    print(f"Findings: {len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
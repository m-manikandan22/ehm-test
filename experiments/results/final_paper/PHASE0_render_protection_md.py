"""
Render EXPERIMENT_A_PROTECTION_REPORT.md from
EXPERIMENT_A_PROTECTION.json so the markdown never drifts from the
checksum truth.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",
                    default="experiments/results/final_paper/EXPERIMENT_A_PROTECTION.json")
    ap.add_argument("--output",
                    default="experiments/results/final_paper/EXPERIMENT_A_PROTECTION_REPORT.md")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        rec = json.load(f)

    lines = []
    lines.append("# EXPERIMENT A PROTECTION REPORT")
    lines.append("")
    lines.append("> **Experiment A is FROZEN.** No file under "
                 "`paper_results/` may be modified, overwritten, or "
                 "deleted by Experiment B. The null/saturation finding "
                 "of Experiment A is preserved as a legitimate scientific "
                 "result.")
    lines.append("")
    lines.append(f"- Generated: `{rec['generated_at']}`")
    lines.append(f"- Git commit at protection: `{rec['git_commit_at_protection']}`")
    lines.append(f"- Paper directory: `{rec['paper_dir']}/`")
    lines.append(f"- Number of files protected: **{rec['n_files']}**")
    lines.append(f"- Total bytes: **{rec['total_bytes']}** "
                 f"(~{rec['total_bytes']/1024/1024:.2f} MiB)")
    lines.append(f"- Aggregate SHA-256 over all files: "
                 f"`{rec['aggregate_sha256']}`")
    lines.append("")
    lines.append("## Why Experiment A is protected")
    lines.append("")
    lines.append(
        "Experiment A already produced a legitimate scientific result: "
        "the demonstrated 49-node grid with 200 ticks and 3 faults is "
        "**too forgiving** to differentiate the tested controllers on "
        "primary reliability indices (SAIFI, SAIDI, ENS, restoration "
        "time, critical-load restored %, voltage violations, switching "
        "operations, number of islands). All five baseline controllers "
        "produced identical aggregate values for those metrics over "
        "the 100-seed paired experiment."
    )
    lines.append("")
    lines.append(
        "This saturation finding is **evidence**, not a defect. It is "
        "the scientific justification for designing a harder, "
        "controller-independent stress benchmark for Experiment B. "
        "Therefore:"
    )
    lines.append("")
    lines.append("1. Experiment A is **not** to be deleted.")
    lines.append("2. Experiment A is **not** to be overwritten.")
    lines.append("3. Experiment A is **not** to be retroactively changed.")
    lines.append("4. Experiment A is **not** to be re-tuned to produce "
                 "favourable results.")
    lines.append("")
    lines.append("## Inventory")
    lines.append("")
    lines.append("| Relative path | Bytes | SHA-256 |")
    lines.append("|---|---:|---|")
    # Sort by directory then filename for readability.
    items = sorted(rec["files"].items(), key=lambda kv: kv[0])
    for rel, info in items:
        lines.append(f"| `{rel}` | {info['bytes']} | `{info['sha256']}` |")
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append(
        "Run `python experiments/results/final_paper/PHASE0_verify_protection.py` "
        "to confirm that no file in `paper_results/` has been modified "
        "after this protection record was created. Any drift in any "
        "SHA-256 is a violation of Experiment A's frozen status."
    )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in rec.get("notes", []):
        lines.append(f"- {note}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"_Protection record SHA-256: `{rec['aggregate_sha256']}`_  ")
    lines.append(f"_Auto-generated from `{args.input}`; do not edit by hand — "
                 f"re-run the renderer to refresh._")
    lines.append("")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
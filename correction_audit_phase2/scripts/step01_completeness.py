"""STEP 1 — Verify corrected raw data completeness (540 runs)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fina_common as fc

OUT = fc.ROOT


def main() -> None:
    raw = fc.load_corrected_b()
    total = len(raw)
    valid = int(raw["valid"].sum())
    invalid = int((~raw["valid"]).sum())

    seeds = sorted(raw["seed"].unique())
    levels = sorted(raw["stress_level"].unique())
    policies = sorted(raw["policy"].unique())

    combos = raw.groupby(["seed", "stress_level", "policy"]).size().reset_index(name="count")
    dup = combos[combos["count"] > 1]
    missing = []
    expected_combos = set()
    for s in seeds:
        for lvl in fc.STRESS_LEVELS:
            for p in fc.POLICIES:
                expected_combos.add((s, lvl, p))
    actual_combos = set(map(tuple, combos[["seed", "stress_level", "policy"]].to_numpy()))
    missing = sorted(expected_combos - actual_combos)

    lines = []
    lines.append("# RUN COMPLETENESS REPORT — Corrected Experiment B")
    lines.append("")
    lines.append("## 1. Dataset source")
    lines.append("")
    lines.append(f"- File: `correction_audit_phase1/experiment_B_corrected_rerun/experiment_B_runs.json`")
    lines.append(f"- Git commit: `{fc.load_corrected_b.__doc__ and 'corrected rerun (frozen)'}`")
    lines.append("")
    lines.append("## 2. Totals")
    lines.append("")
    lines.append(f"| Item | Expected | Observed |")
    lines.append(f"|---|---|---|")
    lines.append(f"| Total runs | 540 | {total} |")
    lines.append(f"| Valid runs | 540 | {valid} |")
    lines.append(f"| Invalid runs | 0 | {invalid} |")
    lines.append("")
    lines.append(f"**Verdict: {'PASS' if (total == 540 and valid == 540 and invalid == 0) else 'FAIL'}**")
    lines.append("")
    lines.append("## 3. Design axes")
    lines.append("")
    lines.append(f"| Axis | Expected | Observed | Verdict |")
    lines.append(f"|---|---|---|---|")
    lines.append(f"| Unique seeds | 30 | {len(seeds)} | {'PASS' if len(seeds) == 30 else 'FAIL'} |")
    lines.append(f"| Stress levels | 2 (`moderate`, `severe`) | {levels} | {'PASS' if set(levels) == set(fc.STRESS_LEVELS) else 'FAIL'} |")
    lines.append(f"| Unique policies | 9 | {len(policies)} | {'PASS' if len(policies) == 9 else 'FAIL'} |")
    lines.append("")
    lines.append("Policies observed:")
    for p in policies:
        lines.append(f"- `{p}`")
    lines.append("")
    lines.append("## 4. seed x stress x policy completeness")
    lines.append("")
    lines.append(f"- Expected combinations: `30 seeds x 2 levels x 9 policies = {30 * 2 * 9}`")
    lines.append(f"- Observed combinations: {len(actual_combos)}")
    lines.append(f"- Duplicated combinations: {len(dup)}")
    lines.append(f"- Missing combinations: {len(missing)}")
    lines.append("")
    if len(dup) == 0 and len(missing) == 0:
        lines.append("Every seed x stress x policy combination occurs **exactly once**.")
    else:
        lines.append("Deficiencies found:")
        for _, r in dup.iterrows():
            lines.append(f"- DUPLICATE: seed={r['seed']} {r['stress_level']} {r['policy']} x{r['count']}")
        for m in missing:
            lines.append(f"- MISSING: {m}")
    lines.append("")
    lines.append("## 5. Per-policy / per-level counts")
    lines.append("")
    lines.append("| stress_level | policy | n_runs | n_valid |")
    lines.append("|---|---|---:|---:|")
    for lvl in fc.STRESS_LEVELS:
        for p in policies:
            sub = raw[(raw["stress_level"] == lvl) & (raw["policy"] == p)]
            lines.append(f"| {lvl} | {p} | {len(sub)} | {int(sub['valid'].sum())} |")
    lines.append("")
    overall = "PASS" if (total == 540 and valid == 540 and invalid == 0
                         and len(seeds) == 30 and len(policies) == 9
                         and len(dup) == 0 and len(missing) == 0) else "FAIL"
    lines.append(f"## 6. Overall verdict: **{overall}**")
    lines.append("")
    lines.append("_Raw results were not modified by this audit._")
    lines.append("")

    path = os.path.join(OUT, "RUN_COMPLETENESS_REPORT.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")
    print(f"total={total} valid={valid} invalid={invalid} seeds={len(seeds)} policies={len(policies)} dup={len(dup)} missing={len(missing)}")


if __name__ == "__main__":
    main()

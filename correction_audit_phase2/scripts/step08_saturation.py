"""STEP 8 — Saturation recheck using corrected execution evidence."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

import fina_common as fc

OUT = fc.ROOT

METRICS = [
    ("SAIFI", "saifi"),
    ("SAIDI", "saidi"),
    ("ENS", "ens"),
    ("Stress cumulative ENS", "stress_cumulative_unserved_energy"),
    ("Restoration time (s)", "restoration_time_seconds"),
    ("Time-to-50% restoration (steps)", "resilience_time_to_50pct_restoration"),
    ("Critical-load restoration (%)", "stress_critical_load_restored_pct"),
    ("Voltage violations", "voltage_violation_count"),
    ("Switching operations", "switching_operations"),
    ("Resilience loss area", "resilience_loss_area"),
    ("Restoration rate", "stress_restoration_rate"),
    ("Isolated nodes", "isolated_nodes"),
    ("Line overloads", "line_overload_count"),
    ("Frequency deviations", "frequency_deviation_count"),
]


def classify_metric(vals_all: np.ndarray, med_by_policy_lvl: dict) -> str:
    v = np.asarray(vals_all, dtype=float)
    n_unique = len(np.unique(v))
    sd = float(np.std(v, ddof=1)) if len(v) > 1 else 0.0
    m = float(np.mean(v)) if len(v) else 0.0
    cv = sd / m if abs(m) > 1e-9 else 0.0
    # number of policy-level medians that differ across policies
    distinct_policy_medians = len(set(round(x, 6) for x in med_by_policy_lvl.values()))
    if n_unique <= 1:
        return "FULL SATURATION"
    if distinct_policy_medians <= 1 and n_unique < 50:
        return "PARTIAL SATURATION"
    if distinct_policy_medians > 1:
        return "GOOD VARIANCE"
    return "PARTIAL SATURATION"


def main() -> None:
    raw = fc.load_corrected_b()
    lines = []
    lines.append("# SATURATION RECHECK — Corrected Experiment B")
    lines.append("")
    lines.append("Does corrected FLISR execution change the historical saturation pattern? Each metric is classified over the corrected 540-run dataset.")
    lines.append("")
    lines.append("| metric | full-saturation flag | unique values | CV | distinct policy medians (severe) | classification |")
    lines.append("|---|---:|---:|---:|---:|---|")
    rows = []
    for label, col in METRICS:
        vals_all = raw[col].to_numpy(dtype=float)
        med_by_policy = {}
        for pol in fc.POLICIES:
            sub = raw[(raw["policy"] == pol) & (raw["stress_level"] == "severe")][col]
            med_by_policy[pol] = float(sub.median())
        n_unique = len(np.unique(vals_all))
        m = float(np.mean(vals_all))
        sd = float(np.std(vals_all, ddof=1)) if len(vals_all) > 1 else 0.0
        cv = sd / m if abs(m) > 1e-9 else 0.0
        distinct_pm = len(set(round(x, 6) for x in med_by_policy.values()))
        cls = classify_metric(vals_all, med_by_policy)
        rows.append((label, n_unique, cv, distinct_pm, cls, m, sd))
        lines.append(f"| {label} | {col} | {n_unique} | {cv:.3f} | {distinct_pm} | {cls} |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("**Corrected FLISR execution changed the ENS picture.** Historically FLISR never executed (`flisr_calls` = 0) and all FLISR-enabled arms looked identical to persistence. In the corrected data FLISR executes every timestep for every FLISR-enabled policy (200 calls/run), applies restoration actions, and reduces unserved energy:")
    lines.append("")
    lines.append("| stress | median ENS persistence/random | median ENS rule_based | median ENS full_stack |")
    lines.append("|---|---:|---:|---:|")
    for lvl in fc.STRESS_LEVELS:
        def med(p):
            return raw[(raw["policy"] == p) & (raw["stress_level"] == lvl)]["stress_cumulative_unserved_energy"].median()
        lines.append(f"| {lvl} | {med('persistence'):.1f} / {med('random'):.1f} | {med('rule_based'):.1f} | {med('full_stack'):.1f} |")
    lines.append("")
    lines.append("**However**, four pre-registered primary metrics remain fully saturated in the corrected data: `saidi` (=0), `resilience_time_to_50pct_restoration` (=0), `stress_critical_load_restored_pct` (=100), `switching_operations` (=0). The `stress_restoration_rate` is 0 for all arms (no fault is ever recorded as restored). These are measurement-instrumentation ceilings/floors, not evidence about controller quality, and are reported as observed.")
    lines.append("")
    lines.append("## Why saturation persists (corrected execution evidence)")
    lines.append("")
    lines.append("- `saidi` is derived from the IEEE-1366 formula over restoration events; with no fault recorded as `restored` (`successful_restoration_count` = 0 everywhere), SAIDI = 0 for every run.")
    lines.append("- `resilience_time_to_50pct_restoration` is computed as the first step index at which service >= 0.5; because service is 1.0 at step 0 (before faults begin), the recorded value is 0 for every run. The pre-registered \"max = 200\" floor for never-recovering runs is not realised by the recorded value.")
    lines.append("- `stress_critical_load_restored_pct` = 100 because the recorded `stress_critical_load_restored_mw` can go negative when the max simultaneous interrupted load exceeds the run-level total; every run records 100%.")
    lines.append("- `switching_operations` is not incremented by the SCADA `_flisr_restore` path (restoration actions applied via tie-switch closures are counted in `restoration_actions_applied`, not in `switching_operations`).")
    lines.append("")
    lines.append("_No raw values were modified._")
    lines.append("")
    path = os.path.join(OUT, "SATURATION_RECHECK.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")
    print(pd.DataFrame(rows, columns=["metric", "unique", "cv", "distinct_pm", "class", "mean", "sd"])[["metric", "class"]].to_string(index=False))


if __name__ == "__main__":
    main()

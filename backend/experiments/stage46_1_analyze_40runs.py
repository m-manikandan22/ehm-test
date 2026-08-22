import json
from collections import defaultdict

d = json.load(open("experiments/results/stage46_1/validation_40runs.json", encoding="utf-8"))
runs = d["runs"]
groups = defaultdict(dict)
for r in runs:
    groups[(r["scenario"], r["seed"])][r["ablation"]] = r

fpk = sorted(runs[0]["fingerprints"].keys())
summary = defaultdict(lambda: defaultdict(int))
for (scen, seed), cells in sorted(groups.items()):
    ref = cells["full_stack"]
    print(f"--- {scen} seed={seed} ---")
    for ab in ["no_lstm", "no_twin", "no_ems", "no_predictive"]:
        if ab not in cells:
            continue
        cell = cells[ab]
        diffs = [k for k in fpk if cell["fingerprints"][k] != ref["fingerprints"][k]]
        mdiffs = {
            k: (ref["metrics"][k], cell["metrics"][k])
            for k in ref["metrics"]
            if ref["metrics"][k] != cell["metrics"][k]
        }
        ac_same = cell["action_counts"] == ref["action_counts"]
        sel_same = cell["selected_actions"] == ref["selected_actions"]
        print(f"  {ab:<12} fp_diffs={len(diffs)} {diffs[:8]}")
        print(f"      action_counts_same={ac_same} selected_same={sel_same} "
              f"metric_diffs={list(mdiffs.keys()) if mdiffs else 'none'}")
        for k, v in list(mdiffs.items())[:4]:
            print(f"        {k}: {v}")
        if diffs:
            for k in diffs:
                summary[ab][k] += 1

print("\n=== Across-cell fingerprint difference counts (out of 8 cells) ===")
for ab in sorted(summary):
    print(f"  {ab}: {dict(summary[ab])}")

# Overall: how many of the 16 cells have ANY ablation difference
any_diff_cells = defaultdict(int)
for (scen, seed), cells in groups.items():
    ref = cells["full_stack"]
    for ab in ["no_lstm", "no_twin", "no_ems", "no_predictive"]:
        if ab not in cells:
            continue
        if cells[ab]["fingerprints"] != ref["fingerprints"]:
            any_diff_cells[ab] += 1
print("\n=== Number of (scenario,seed) cells where ablation differs from full_stack ===")
for ab in sorted(any_diff_cells):
    print(f"  {ab}: {any_diff_cells[ab]}/8")
"""stage46_inspect_pairwise.py — quick inspection helper."""
import json
from pathlib import Path

P = Path("experiments/results/stage46/statistics/pairwise_correct_stage45_full_stack.json")
data = json.loads(P.read_text())
print(f"Total: {len(data)}")
print()
for k, v in sorted(data.items()):
    if (
        v["cell_a"] == "rule_based"
        and v["cell_b"] == "trained_dqn"
        and v["scenario"] == "A"
        and v["metric"] == "energy_not_served_mwh"
    ):
        print(k)
        for kk, vv in v.items():
            print(f"  {kk}: {vv}")
print()
print("=== random vs everything (scenario A, ENS) ===")
for k, v in sorted(data.items()):
    if v["scenario"] == "A" and v["metric"] == "energy_not_served_mwh" and v["cell_a"] == "random":
        print(k)
        for kk, vv in v.items():
            print(f"  {kk}: {vv}")
        print()

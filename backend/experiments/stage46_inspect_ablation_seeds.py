"""Verify ablation cells aren't functionally identical."""
import json
from pathlib import Path

src = Path("experiments/results/stage45/validation.json")
rep = json.loads(src.read_text())
runs = rep["runs"]
print(f"runs: {len(runs)}")
print()

abl_counts = {}
abl_ens_per_seed = {}
for r in runs:
    if r["controller_label"] != "trained_dqn":
        continue
    key = (r["ablation"], r["scenario"], r["seed"])
    abl_counts[key[0]] = abl_counts.get(key[0], 0) + 1
    abl_ens_per_seed.setdefault(key[0], {}).setdefault(key[2], {})[key[1]] = \
        r["metrics"]["energy_not_served_mwh"]

print("ablations counts:")
for k, v in abl_counts.items():
    print(f"  {k}: {v}")
print()

# For each ablation, show ENS for seed=0 across scenarios
print("Seed=0 ENS for each (ablation, scenario):")
for abl in sorted(abl_ens_per_seed.keys()):
    row = [abl]
    for scen in ("A", "E", "I", "J"):
        ens = abl_ens_per_seed[abl].get(0, {}).get(scen, None)
        row.append(f"{ens:.3f}" if ens is not None else "—")
    print(f"  {row[0]:>14s} | A={row[1]} | E={row[2]} | I={row[3]} | J={row[4]}")

print()
print("Seed=5 ENS for each (ablation, scenario):")
for abl in sorted(abl_ens_per_seed.keys()):
    row = [abl]
    for scen in ("A", "E", "I", "J"):
        ens = abl_ens_per_seed[abl].get(5, {}).get(scen, None)
        row.append(f"{ens:.3f}" if ens is not None else "--")
    print(f"  {row[0]:>14s} | A={row[1]} | E={row[2]} | I={row[3]} | J={row[4]}")

# Show how often ablation differs across all seeds
print()
print("How many seeds have full_stack != no_lstm (by scenario):")
for scen in ("A", "E", "I", "J"):
    matches = 0
    for s in range(10):
        a = abl_ens_per_seed["full_stack"].get(s, {}).get(scen)
        b = abl_ens_per_seed["no_lstm"].get(s, {}).get(scen)
        if a is not None and b is not None and abs(a - b) > 1e-6:
            matches += 1
    print(f"  {scen}: {matches}/10 seeds differ between full_stack and no_lstm")

"""stage46_inspect_ablations.py — explore ablation contrasts."""
import json
from pathlib import Path

P = Path("experiments/results/stage46/statistics/pairwise_correct_stage45_all_ablations.json")
data = json.loads(P.read_text())
print(f"Total: {len(data)}")
print()
# Inspect trained_dqn — full_stack vs no_lstm / no_twin / etc.
ablation_pairs = [
    ("trained_dqn", "full_stack", "trained_dqn", "no_lstm"),
    ("trained_dqn", "full_stack", "trained_dqn", "no_twin"),
    ("trained_dqn", "full_stack", "trained_dqn", "no_ems"),
    ("trained_dqn", "full_stack", "trained_dqn", "no_predictive"),
    ("trained_dqn", "no_lstm", "trained_dqn", "no_twin"),
]
for ca, aa, cb, ab in ablation_pairs:
    print(f"=== {ca}/{aa} vs {cb}/{ab} (ENS) ===")
    n = 0
    for k, v in sorted(data.items()):
        if (
            (v["cell_a"] == ca and v["ablation_a"] == aa and v["cell_b"] == cb and v["ablation_b"] == ab)
            or (v["cell_a"] == cb and v["ablation_a"] == ab and v["cell_b"] == ca and v["ablation_b"] == aa)
        ):
            if v["metric"] == "energy_not_served_mwh":
                # Force cell_a = full_stack
                if v["cell_a"] != ca:
                    ma, mb, diff = v["mean_b"], v["mean_a"], -v["mean_diff"]
                else:
                    ma, mb, diff = v["mean_a"], v["mean_b"], v["mean_diff"]
                p_val = v["wilcoxon"]["p_value"]
                cls = v["classification"]
                print(f"  scenario={v['scenario']:>2}  n={v['n_pairs']}  "
                      f"{ma:7.3f} vs {mb:7.3f}  diff={diff:+7.3f}  "
                      f"p={p_val:.4f}  {cls}")
                n += 1
    if n == 0:
        print("  NO PAIRS")
    print()

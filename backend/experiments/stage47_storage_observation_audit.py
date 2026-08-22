"""
stage47_storage_observation_audit.py — Stage 47 Storage Observation Audit

Reproduces the Stage-46.3 controlled experiments using the NEW observation
representation to verify that grid-scale storage SOC is now observable.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, r'C:\Users\ELCOT\Music\EHM-paper\backend')

from simulation.grid import SmartGrid
from experiments.runner import _storage_level
from models.rl_agent import build_extended_state, EXTENDED_STATE_DIM

OUTPUT_DIR = Path(r'C:\Users\ELCOT\Music\EHM-paper\backend\experiments\results\stage47')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_test_grid(battery_soc=None, supercap_soc=None, 
                    house_battery_soc=1.0, house_supercap_soc=1.0):
    """Build a grid with controlled storage SOC values."""
    grid = SmartGrid(seed=0)
    
    if battery_soc is not None:
        grid.nodes["STORAGE_BAT"].battery_level = float(battery_soc)
    if supercap_soc is not None:
        grid.nodes["STORAGE_SC"].supercap_level = float(supercap_soc)
    
    for nid, node in grid.nodes.items():
        if node.node_type == "house":
            if house_battery_soc is not None:
                node.battery_level = float(house_battery_soc)
            if house_supercap_soc is not None:
                node.supercap_level = float(house_supercap_soc)
    
    grid.update_power_flow()
    return grid


def get_extended_state(grid, predicted_load=0.5, twin_max_risk=0.0, 
                       twin_mean_risk=0.0, twin_high_frac=0.0):
    """Build the 78-dim extended state vector."""
    legacy_state = grid.get_rl_state()
    battery_soc = _storage_level(grid, "battery")
    supercap_soc = _storage_level(grid, "supercap")
    return build_extended_state(
        legacy_state,
        predicted_load=predicted_load,
        battery_soc=battery_soc,
        supercap_soc=supercap_soc,
        twin_max_risk=twin_max_risk,
        twin_mean_risk=twin_mean_risk,
        twin_high_frac=twin_high_frac,
    )


print("="*60)
print("STAGE 47 STORAGE OBSERVATION AUDIT")
print("="*60)

# ─── Experiment 1: Battery SOC Controlled Test ────────────────────────
print("\n" + "="*60)
print("EXPERIMENT 1: Battery SOC Observation (Grid-Scale)")
print("="*60)

battery_results = []
test_values = [0.80, 0.60, 0.40, 0.20, 0.10, 0.05, 0.00]

for bat_soc in test_values:
    grid = build_test_grid(battery_soc=bat_soc, house_battery_soc=1.0)
    
    grid_bat_soc = grid.nodes["STORAGE_BAT"].battery_level
    house_bat_socs = [n.battery_level for n in grid.nodes.values() if n.node_type == "house"]
    
    feat_73 = _storage_level(grid, "battery")
    state_vec = get_extended_state(grid)
    
    battery_results.append({
        "grid_battery_soc": grid_bat_soc,
        "house_battery_socs": house_bat_socs[:3],
        "feature_73": feat_73,
        "feature_73_matches_grid": abs(feat_73 - grid_bat_soc) < 1e-6,
        "state_vector": state_vec,
    })
    print(f"  Grid BAT SOC={grid_bat_soc:.3f} -> Feature 73={feat_73:.3f} (match: {abs(feat_73 - grid_bat_soc) < 1e-6})")

feat_73_vals = [r["feature_73"] for r in battery_results]
all_match = all(r["feature_73_matches_grid"] for r in battery_results)
print(f"  Feature 73 range: min={min(feat_73_vals):.6f}, max={max(feat_73_vals):.6f}")
print(f"  All values match grid SOC: {all_match}")

with open(OUTPUT_DIR / "battery_observation_probe.json", "w") as f:
    json.dump(battery_results, f, indent=2, default=str)

# ─── Experiment 2: Supercap SOC Controlled Test ──────────────────────
print("\n" + "="*60)
print("EXPERIMENT 2: Supercapacitor SOC Observation (Grid-Scale)")
print("="*60)

supercap_results = []
test_values_sc = [0.80, 0.60, 0.40, 0.20, 0.10, 0.05, 0.00]

for sc_soc in test_values_sc:
    grid = build_test_grid(supercap_soc=sc_soc, house_supercap_soc=1.0)
    
    grid_sc_soc = grid.nodes["STORAGE_SC"].supercap_level
    house_sc_socs = [n.supercap_level for n in grid.nodes.values() if n.node_type == "house"]
    
    feat_74 = _storage_level(grid, "supercap")
    state_vec = get_extended_state(grid)
    
    supercap_results.append({
        "grid_supercap_soc": grid_sc_soc,
        "house_supercap_socs": house_sc_socs[:3],
        "feature_74": feat_74,
        "feature_74_matches_grid": abs(feat_74 - grid_sc_soc) < 1e-6,
        "state_vector": state_vec,
    })
    print(f"  Grid SC SOC={grid_sc_soc:.3f} -> Feature 74={feat_74:.3f} (match: {abs(feat_74 - grid_sc_soc) < 1e-6})")

feat_74_vals = [r["feature_74"] for r in supercap_results]
all_match_sc = all(r["feature_74_matches_grid"] for r in supercap_results)
print(f"  Feature 74 range: min={min(feat_74_vals):.6f}, max={max(feat_74_vals):.6f}")
print(f"  All values match grid SOC: {all_match_sc}")

with open(OUTPUT_DIR / "supercap_observation_probe.json", "w") as f:
    json.dump(supercap_results, f, indent=2, default=str)

# ─── Experiment 3: Multi-State Verification ──────────────────────────
print("\n" + "="*60)
print("EXPERIMENT 3: Multi-State Verification (Both Storage Types)")
print("="*60)

test_states = [
    {"name": "high_bat_high_sc", "bat": 0.80, "sc": 0.80},
    {"name": "low_bat_high_sc", "bat": 0.20, "sc": 0.80},
    {"name": "high_bat_low_sc", "bat": 0.80, "sc": 0.20},
    {"name": "low_bat_low_sc", "bat": 0.20, "sc": 0.20},
    {"name": "mid_bat_mid_sc", "bat": 0.50, "sc": 0.50},
    {"name": "empty_bat_full_sc", "bat": 0.00, "sc": 1.00},
    {"name": "full_bat_empty_sc", "bat": 1.00, "sc": 0.00},
]

multi_state_results = []
for ts in test_states:
    grid = build_test_grid(battery_soc=ts["bat"], supercap_soc=ts["sc"],
                           house_battery_soc=1.0, house_supercap_soc=1.0)
    
    feat_73 = _storage_level(grid, "battery")
    feat_74 = _storage_level(grid, "supercap")
    state_vec = get_extended_state(grid)
    
    multi_state_results.append({
        "name": ts["name"],
        "grid_battery_soc": ts["bat"],
        "grid_supercap_soc": ts["sc"],
        "feature_73": feat_73,
        "feature_74": feat_74,
        "feat73_matches_grid": abs(feat_73 - ts["bat"]) < 1e-6,
        "feat74_matches_grid": abs(feat_74 - ts["sc"]) < 1e-6,
    })
    print(f"  {ts['name']}: bat={ts['bat']:.2f}->feat73={feat_73:.3f}, sc={ts['sc']:.2f}->feat74={feat_74:.3f}")

all_bat_match = all(r["feat73_matches_grid"] for r in multi_state_results)
all_sc_match = all(r["feat74_matches_grid"] for r in multi_state_results)
print(f"  All battery features match grid: {all_bat_match}")
print(f"  All supercap features match grid: {all_sc_match}")

with open(OUTPUT_DIR / "multi_state_verification.json", "w") as f:
    json.dump(multi_state_results, f, indent=2, default=str)

# ─── Experiment 4: House SOC Independence Test ───────────────────────
print("\n" + "="*60)
print("EXPERIMENT 4: House SOC Independence Test")
print("="*60)

# Test that house SOC at various levels doesn't affect grid storage features
house_soc_tests = [
    {"house_bat": 1.0, "house_sc": 1.0, "grid_bat": 0.50, "grid_sc": 0.50},
    {"house_bat": 0.5, "house_sc": 1.0, "grid_bat": 0.50, "grid_sc": 0.50},
    {"house_bat": 0.0, "house_sc": 1.0, "grid_bat": 0.50, "grid_sc": 0.50},
    {"house_bat": 1.0, "house_sc": 0.5, "grid_bat": 0.50, "grid_sc": 0.50},
    {"house_bat": 1.0, "house_sc": 0.0, "grid_bat": 0.50, "grid_sc": 0.50},
]

independence_results = []
for test in house_soc_tests:
    grid = build_test_grid(
        battery_soc=test["grid_bat"],
        supercap_soc=test["grid_sc"],
        house_battery_soc=test["house_bat"],
        house_supercap_soc=test["house_sc"],
    )
    
    feat_73 = _storage_level(grid, "battery")
    feat_74 = _storage_level(grid, "supercap")
    
    independence_results.append({
        "house_battery_soc": test["house_bat"],
        "house_supercap_soc": test["house_sc"],
        "grid_battery_soc": test["grid_bat"],
        "grid_supercap_soc": test["grid_sc"],
        "feature_73": feat_73,
        "feature_74": feat_74,
        "bat_independent": abs(feat_73 - test["grid_bat"]) < 1e-6,
        "sc_independent": abs(feat_74 - test["grid_sc"]) < 1e-6,
    })
    print(f"  House bat={test['house_bat']:.1f}, sc={test['house_sc']:.1f} -> feat73={feat_73:.3f} (grid={test['grid_bat']:.1f}), feat74={feat_74:.3f} (grid={test['grid_sc']:.1f})")

all_bat_ind = all(r["bat_independent"] for r in independence_results)
all_sc_ind = all(r["sc_independent"] for r in independence_results)
print(f"  Battery feature independent of house SOC: {all_bat_ind}")
print(f"  Supercap feature independent of house SOC: {all_sc_ind}")

with open(OUTPUT_DIR / "house_soc_independence.json", "w") as f:
    json.dump(independence_results, f, indent=2, default=str)

# ─── Summary ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SUMMARY: STAGE 47 OBSERVATION REPAIR VERIFICATION")
print("="*60)

overall_success = all_match and all_match_sc and all_bat_match and all_sc_match and all_bat_ind and all_sc_ind

print(f"  Battery feature tracks grid SOC:     {'PASS' if all_match else 'FAIL'}")
print(f"  Supercap feature tracks grid SOC:    {'PASS' if all_match_sc else 'FAIL'}")
print(f"  Multi-state battery verification:    {'PASS' if all_bat_match else 'FAIL'}")
print(f"  Multi-state supercap verification:   {'PASS' if all_sc_match else 'FAIL'}")
print(f"  Battery independent of house SOC:    {'PASS' if all_bat_ind else 'FAIL'}")
print(f"  Supercap independent of house SOC:   {'PASS' if all_sc_ind else 'FAIL'}")
print(f"  OVERALL:                             {'PASS' if overall_success else 'FAIL'}")

summary = {
    "battery_tracks_grid": all_match,
    "supercap_tracks_grid": all_match_sc,
    "multi_state_battery": all_bat_match,
    "multi_state_supercap": all_sc_match,
    "battery_independent_of_house": all_bat_ind,
    "supercap_independent_of_house": all_sc_ind,
    "overall_success": overall_success,
}

with open(OUTPUT_DIR / "observation_repair_summary.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\nResults saved to: {OUTPUT_DIR}")
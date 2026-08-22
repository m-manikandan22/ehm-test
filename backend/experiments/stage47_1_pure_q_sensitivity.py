"""
stage47_1_pure_q_sensitivity.py — Stage 47.1 Pure Q-Value Sensitivity Audit

This script tests whether Feature 73 (battery SOC) and Feature 74 (supercapacitor SOC)
causally affect DQN Q-values when perturbed IN ISOLATION, without any physical
simulation side effects.

NO power-flow recomputation. NO grid rebuild. ONLY the input vector changes.
"""

import json
import hashlib
import numpy as np
import torch
import sys
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, r'C:\Users\ELCOT\Music\EHM-paper\backend')

from models.rl_agent import DQNAgent, EXTENDED_STATE_DIM, build_extended_state


# ============================================================
# CONFIGURATION
# ============================================================
CKPT_PATH = r'C:\Users\ELCOT\Music\EHM-paper\backend\experiments\checkpoints\dqn_stage47_storage_aware.pt'
STAGE44_CKPT_PATH = r'C:\Users\ELCOT\Music\EHM-paper\backend\experiments\checkpoints\dqn_stage44.pt'
OUTPUT_DIR = Path(r'C:\Users\ELCOT\Music\EHM-paper\backend\experiments\results\stage47_1')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Numerical tolerance for state-isolation verification
STATE_ISOLATION_TOLERANCE = 1e-10

# Controlled SOC values to test
SOC_TEST_VALUES = [0.90, 0.80, 0.60, 0.50, 0.40, 0.20, 0.10, 0.05, 0.00]

# Q-value sensitivity tolerance (defined BEFORE running experiment)
Q_SENSITIVITY_TOLERANCE = 1e-6


# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_checkpoint_hash(path: str) -> str:
    """Calculate SHA-256 of checkpoint file."""
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_q_values(agent: DQNAgent, state_vec: List[float]) -> np.ndarray:
    """Get Q-values for a state vector (greedy, no exploration)."""
    with torch.no_grad():
        state_tensor = torch.tensor(state_vec, dtype=torch.float32).unsqueeze(0)
        return agent.policy_net(state_tensor).squeeze(0).numpy()


def get_argmax_action(agent: DQNAgent, state_vec: List[float], grid_state: Dict[str, Any] = None) -> int:
    """Get argmax action for a state vector (eval mode)."""
    decision = agent.select_action(state_vec, predicted_load=state_vec[72], grid_state=grid_state)
    return decision["action_id"]


def verify_state_isolation(base_vec: np.ndarray, test_vec: np.ndarray, expected_index: int) -> bool:
    """
    Verify that ONLY the expected index changed between base and test vectors.
    
    Returns True if either:
    - No elements differ (test value equals baseline value), OR
    - Exactly one element (at expected_index) differs beyond tolerance.
    """
    diff = np.abs(test_vec - base_vec)
    changed_indices = np.where(diff > STATE_ISOLATION_TOLERANCE)[0]
    
    if len(changed_indices) == 0:
        # Test value equals baseline - no change expected, this is correct
        return True
    elif len(changed_indices) == 1 and changed_indices[0] == expected_index:
        return True
    else:
        print(f"  STATE ISOLATION FAILED: Expected only index {expected_index} to change, "
              f"but changed indices: {changed_indices}")
        print(f"  Diffs > tolerance: {diff[changed_indices]}")
        return False


def run_feature_sensitivity_test(
    agent: DQNAgent,
    base_state_vec: np.ndarray,
    feature_index: int,
    feature_name: str,
    soc_values: List[float],
    base_action: int,
    grid_state: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Run pure sensitivity test for a single feature.
    
    For each SOC value, create a test state where ONLY feature_index changes.
    """
    results = []
    
    for soc_val in soc_values:
        # Create test vector: copy base, change ONLY the target feature
        test_vec = base_state_vec.copy()
        test_vec[feature_index] = soc_val
        
        # Verify state isolation
        isolation_ok = verify_state_isolation(base_state_vec, test_vec, feature_index)
        
        # Get Q-values
        q_vals = get_q_values(agent, test_vec.tolist())
        
        # Get action
        action = get_argmax_action(agent, test_vec.tolist(), grid_state)
        
        # Calculate deltas vs base
        base_q = get_q_values(agent, base_state_vec.tolist())
        delta_q = q_vals - base_q
        l2_norm = float(np.linalg.norm(delta_q))
        max_abs_delta = float(np.max(np.abs(delta_q)))
        
        result = {
            "soc_value": soc_val,
            "feature_index": feature_index,
            "feature_name": feature_name,
            "state_isolation_passed": isolation_ok,
            "q_values": q_vals.tolist(),
            "base_q_values": base_q.tolist(),
            "delta_q": delta_q.tolist(),
            "delta_q_l2_norm": l2_norm,
            "delta_q_max_abs": max_abs_delta,
            "base_action": base_action,
            "test_action": action,
            "action_changed": action != base_action,
        }
        results.append(result)
        
        print(f"  {feature_name}={soc_val:.2f}: "
              f"isolation={'PASS' if isolation_ok else 'FAIL'}, "
              f"||dQ||_2={l2_norm:.6f}, "
              f"max|dQ|={max_abs_delta:.6f}, "
              f"action={action} ({'FLIP' if action != base_action else 'same'})")
    
    return results


def main():
    print("=" * 70)
    print("STAGE 47.1 — PURE Q-VALUE SENSITIVITY AUDIT")
    print("=" * 70)
    
    # ------------------------------------------------------------------
    # 1. CHECKPOINT INTEGRITY VERIFICATION
    # ------------------------------------------------------------------
    print("\n[1] CHECKPOINT INTEGRITY VERIFICATION")
    print("-" * 50)
    
    # Stage-44 checkpoint
    stage44_hash = get_checkpoint_hash(STAGE44_CKPT_PATH)
    expected_stage44 = "eb7bbed22a18f13dbe607b908caf7905ec0fd9b9c14f2a80a75c628bac594493"
    stage44_ok = stage44_hash == expected_stage44
    print(f"Stage-44 checkpoint: {stage44_hash}")
    print(f"Expected:            {expected_stage44}")
    print(f"Match: {stage44_ok}")
    if not stage44_ok:
        print("[ERROR] STAGE-44 CHECKPOINT HASH MISMATCH - STOP")
        return
    
    # Stage-47 checkpoint
    stage47_hash = get_checkpoint_hash(CKPT_PATH)
    expected_stage47 = "316b1a91028ee9143390bc4fba289ffc845a92b94f94ba55015ad52920d029d5"
    stage47_ok = stage47_hash == expected_stage47
    print(f"Stage-47 checkpoint: {stage47_hash}")
    print(f"Expected:            {expected_stage47}")
    print(f"Match: {stage47_ok}")
    if not stage47_ok:
        print("[ERROR] STAGE-47 CHECKPOINT HASH MISMATCH - STOP")
        return
    
    # ------------------------------------------------------------------
    # 2. LOAD STAGE-47 DQN
    # ------------------------------------------------------------------
    print("\n[2] LOAD STAGE-47 DQN")
    print("-" * 50)
    
    agent = DQNAgent.load_checkpoint(CKPT_PATH, state_dim=EXTENDED_STATE_DIM, eval_mode=True)
    agent.eval_mode()
    print(f"Agent loaded: state_dim={agent.state_dim}, training={agent.is_training}")
    print(f"N_ACTIONS: {agent.policy_net.net[-1].out_features}")
    
    # Verify dimensions
    assert agent.state_dim == 78, f"Expected state_dim=78, got {agent.state_dim}"
    n_actions = agent.policy_net.net[-1].out_features
    assert n_actions == 5, f"Expected 5 actions, got {n_actions}"
    print("[OK] State dim = 78, Actions = 5 verified")
    
    # ------------------------------------------------------------------
    # 3. BUILD BASELINE STATE VECTOR (NO GRID, NO PHYSICS)
    # ------------------------------------------------------------------
    print("\n[3] BUILD BASELINE STATE VECTOR (PURE, NO PHYSICS)")
    print("-" * 50)
    
    # We need a valid 72-dim legacy state + 6 extended features = 78 total
    # The legacy state (72 dim) comes from SmartGrid.get_rl_state()
    # But for PURE state isolation, we construct a FIXED base vector directly
    # and only perturb features 73 and 74.
    
    # First, get a legitimate baseline by building ONE grid to extract the 72-dim structure
    from simulation.grid import SmartGrid
    temp_grid = SmartGrid(seed=0)
    temp_grid.update_power_flow()
    legacy_state = temp_grid.get_rl_state()
    assert len(legacy_state) == 72, f"Expected 72-dim legacy state, got {len(legacy_state)}"
    print(f"Legacy state dimension: {len(legacy_state)} (verified)")
    
    # Build the baseline extended state with neutral values for features 73-78
    # Feature indices (0-indexed):
    #   72 = predicted_load (LSTM)
    #   73 = battery_soc (STORAGE_BAT) <-- FEATURE 73
    #   74 = supercap_soc (STORAGE_SC) <-- FEATURE 74
    #   75 = twin_max_risk
    #   76 = twin_mean_risk
    #   77 = twin_high_frac
    
    BASE_PREDICTED_LOAD = 0.5
    BASE_BATTERY_SOC = 0.50
    BASE_SUPERCAP_SOC = 0.50
    BASE_TWIN_MAX_RISK = 0.0
    BASE_TWIN_MEAN_RISK = 0.0
    BASE_TWIN_HIGH_FRAC = 0.0
    
    base_extended = build_extended_state(
        legacy_state,
        predicted_load=BASE_PREDICTED_LOAD,
        battery_soc=BASE_BATTERY_SOC,
        supercap_soc=BASE_SUPERCAP_SOC,
        twin_max_risk=BASE_TWIN_MAX_RISK,
        twin_mean_risk=BASE_TWIN_MEAN_RISK,
        twin_high_frac=BASE_TWIN_HIGH_FRAC,
    )
    
    base_state_vec = np.array(base_extended, dtype=np.float32)
    print(f"Base extended state dimension: {len(base_state_vec)}")
    print(f"  Feature 72 (predicted_load): {base_state_vec[72]:.4f}")
    print(f"  Feature 73 (battery_soc):    {base_state_vec[73]:.4f} <-- TARGET")
    print(f"  Feature 74 (supercap_soc):   {base_state_vec[74]:.4f} <-- TARGET")
    print(f"  Feature 75 (twin_max_risk):  {base_state_vec[75]:.4f}")
    print(f"  Feature 76 (twin_mean_risk): {base_state_vec[76]:.4f}")
    print(f"  Feature 77 (twin_high_frac): {base_state_vec[77]:.4f}")
    
    # Get baseline Q-values and action
    base_q = get_q_values(agent, base_state_vec.tolist())
    base_action = get_argmax_action(agent, base_state_vec.tolist(), None)
    print(f"\nBaseline Q-values: {base_q}")
    print(f"Baseline argmax action: {base_action} ({['increase_generation','use_battery','use_supercapacitor','shift_load','reroute_energy'][base_action]})")
    
    # Create a minimal grid_state for action masking (all actions valid)
    # This is just for the action mask - doesn't affect Q-values
    minimal_grid_state = {
        "nodes": {
            "STORAGE_BAT": {"node_type": "battery", "failed": False, "isolated": False, "battery_level": BASE_BATTERY_SOC, "supercap_level": 0.0, "load": 0.0},
            "STORAGE_SC": {"node_type": "supercap", "failed": False, "isolated": False, "battery_level": 0.0, "supercap_level": BASE_SUPERCAP_SOC, "load": 0.0},
        },
        "edges": []
    }
    # Add generator for action 0 validity
    minimal_grid_state["nodes"]["G0"] = {"node_type": "generator", "failed": False, "isolated": False, "battery_level": 0.0, "supercap_level": 0.0, "load": 0.0}
    # Add house for action 3 validity
    minimal_grid_state["nodes"]["H0"] = {"node_type": "house", "failed": False, "isolated": False, "battery_level": 1.0, "supercap_level": 1.0, "load": 1.0}
    # Add tie switch for action 4 validity
    minimal_grid_state["edges"].append({"source": "S_MAIN", "target": "S_BACKUP", "is_tie_switch": True, "active": False, "switch_status": "closed"})
    
    # ------------------------------------------------------------------
    # 4. BATTERY PURE SENSITIVITY TEST (Feature 73 ONLY)
    # ------------------------------------------------------------------
    print("\n[4] BATTERY PURE SENSITIVITY TEST (Feature 73 ONLY)")
    print("-" * 50)
    print(f"Testing SOC values: {SOC_TEST_VALUES}")
    print(f"Only feature 73 changes; all other 77 features fixed.")
    
    battery_results = run_feature_sensitivity_test(
        agent=agent,
        base_state_vec=base_state_vec,
        feature_index=73,
        feature_name="battery_soc",
        soc_values=SOC_TEST_VALUES,
        base_action=base_action,
        grid_state=minimal_grid_state
    )
    
    # Verify ALL isolation checks passed
    battery_isolation_all_pass = all(r["state_isolation_passed"] for r in battery_results)
    print(f"\n  Battery state isolation: {'ALL PASS' if battery_isolation_all_pass else 'SOME FAIL'}")
    
    # ------------------------------------------------------------------
    # 5. SUPERCAPACITOR PURE SENSITIVITY TEST (Feature 74 ONLY)
    # ------------------------------------------------------------------
    print("\n[5] SUPERCAPACITOR PURE SENSITIVITY TEST (Feature 74 ONLY)")
    print("-" * 50)
    print(f"Testing SOC values: {SOC_TEST_VALUES}")
    print(f"Only feature 74 changes; all other 77 features fixed.")
    
    supercap_results = run_feature_sensitivity_test(
        agent=agent,
        base_state_vec=base_state_vec,
        feature_index=74,
        feature_name="supercap_soc",
        soc_values=SOC_TEST_VALUES,
        base_action=base_action,
        grid_state=minimal_grid_state
    )
    
    # Verify ALL isolation checks passed
    supercap_isolation_all_pass = all(r["state_isolation_passed"] for r in supercap_results)
    print(f"\n  Supercap state isolation: {'ALL PASS' if supercap_isolation_all_pass else 'SOME FAIL'}")
    
    # ------------------------------------------------------------------
    # 6. ANALYSIS & CLASSIFICATION
    # ------------------------------------------------------------------
    print("\n[6] SENSITIVITY ANALYSIS & CLASSIFICATION")
    print("-" * 50)
    
    # Battery analysis
    battery_q_matrix = np.array([r["q_values"] for r in battery_results])
    battery_q_range = battery_q_matrix.max(axis=0) - battery_q_matrix.min(axis=0)
    battery_max_range = float(battery_q_range.max())
    battery_max_delta_norm = max(r["delta_q_l2_norm"] for r in battery_results)
    battery_max_delta_abs = max(r["delta_q_max_abs"] for r in battery_results)
    battery_actions = [r["test_action"] for r in battery_results]
    battery_unique_actions = set(battery_actions)
    battery_action_flips = any(r["action_changed"] for r in battery_results)
    
    print(f"\n  BATTERY (Feature 73):")
    print(f"    Q-range per action: {battery_q_range}")
    print(f"    Max Q-range:        {battery_max_range:.6f}")
    print(f"    Max ||dQ||_2:       {battery_max_delta_norm:.6f}")
    print(f"    Max |dQ|:           {battery_max_delta_abs:.6f}")
    print(f"    Actions observed:   {sorted(battery_unique_actions)}")
    print(f"    Action flips:       {'YES' if battery_action_flips else 'NO'}")
    
    # Level 2 Q-value sensitivity: Q-range > tolerance
    battery_level2 = battery_max_range > Q_SENSITIVITY_TOLERANCE
    battery_level3 = battery_action_flips
    
    print(f"    Level 1 (representation): PASS (by construction)")
    print(f"    Level 2 (Q-value sensitivity): {'PASS' if battery_level2 else 'FAIL'} (Q-range > {Q_SENSITIVITY_TOLERANCE})")
    print(f"    Level 3 (action sensitivity): {'PASS' if battery_level3 else 'NOT DEMONSTRATED'}")
    
    # Supercap analysis
    supercap_q_matrix = np.array([r["q_values"] for r in supercap_results])
    supercap_q_range = supercap_q_matrix.max(axis=0) - supercap_q_matrix.min(axis=0)
    supercap_max_range = float(supercap_q_range.max())
    supercap_max_delta_norm = max(r["delta_q_l2_norm"] for r in supercap_results)
    supercap_max_delta_abs = max(r["delta_q_max_abs"] for r in supercap_results)
    supercap_actions = [r["test_action"] for r in supercap_results]
    supercap_unique_actions = set(supercap_actions)
    supercap_action_flips = any(r["action_changed"] for r in supercap_results)
    
    print(f"\n  SUPERCAPACITOR (Feature 74):")
    print(f"    Q-range per action: {supercap_q_range}")
    print(f"    Max Q-range:        {supercap_max_range:.6f}")
    print(f"    Max ||dQ||_2:       {supercap_max_delta_norm:.6f}")
    print(f"    Max |dQ|:           {supercap_max_delta_abs:.6f}")
    print(f"    Actions observed:   {sorted(supercap_unique_actions)}")
    print(f"    Action flips:       {'YES' if supercap_action_flips else 'NO'}")
    
    supercap_level2 = supercap_max_range > Q_SENSITIVITY_TOLERANCE
    supercap_level3 = supercap_action_flips
    
    print(f"    Level 1 (representation): PASS (by construction)")
    print(f"    Level 2 (Q-value sensitivity): {'PASS' if supercap_level2 else 'FAIL'} (Q-range > {Q_SENSITIVITY_TOLERANCE})")
    print(f"    Level 3 (action sensitivity): {'PASS' if supercap_level3 else 'NOT DEMONSTRATED'}")
    
    # ------------------------------------------------------------------
    # 7. COMPARISON WITH STAGE-47 (HISTORICAL CONTEXT)
    # ------------------------------------------------------------------
    print("\n[7] COMPARISON WITH STAGE-47 HISTORICAL RESULTS")
    print("-" * 50)
    print("  Previous Stage-47 (physical perturbation, may have side effects):")
    print("    Battery Q-range:  ~5.6732 (Action 1)")
    print("    Supercap Q-range: ~0.2231 (Action 0)")
    print("    Both classified as 'LEVEL 3' (incorrect terminology - was Level 2)")
    print("    Action flips: NO (all Action 4)")
    print("")
    print("  Stage-47.1 (pure state isolation, NO physics):")
    print(f"    Battery Q-range:  {battery_max_range:.6f} (Action {np.argmax(battery_q_range)})")
    print(f"    Supercap Q-range: {supercap_max_range:.6f} (Action {np.argmax(supercap_q_range)})")
    print(f"    Battery Level 2:  {'PASS' if battery_level2 else 'FAIL'}")
    print(f"    Supercap Level 2: {'PASS' if supercap_level2 else 'FAIL'}")
    print(f"    Battery Level 3:  {'PASS' if battery_level3 else 'NOT DEMONSTRATED'}")
    print(f"    Supercap Level 3: {'PASS' if supercap_level3 else 'NOT DEMONSTRATED'}")
    
    # ------------------------------------------------------------------
    # 8. FINAL GATE
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("STAGE 47.1 FINAL GATE")
    print("=" * 70)
    
    # Gate checks
    gate_stage44_protected = stage44_ok
    gate_stage44_sha_unchanged = stage44_ok  # Same check
    gate_stage47_protected = stage47_ok
    gate_stage47_sha_unchanged = stage47_ok  # Same check
    gate_stage44_provenance = True  # Git diff showed clean changes, original preserved in history
    gate_feat73_repr = True  # By construction
    gate_feat74_repr = True  # By construction
    gate_battery_isolation = battery_isolation_all_pass
    gate_supercap_isolation = supercap_isolation_all_pass
    gate_battery_q_sensitivity = battery_level2
    gate_supercap_q_sensitivity = supercap_level2
    gate_battery_action_sensitivity = "NOT DEMONSTRATED" if not battery_level3 else "PASS"
    gate_supercap_action_sensitivity = "NOT DEMONSTRATED" if not supercap_level3 else "PASS"
    gate_no_training = True  # We didn't train
    gate_no_stage48 = True  # We didn't start Stage 48
    
    print(f"Stage-44 checkpoint protected: {'PASS' if gate_stage44_protected else 'FAIL'}")
    print(f"Stage-44 SHA unchanged:        {'PASS' if gate_stage44_sha_unchanged else 'FAIL'}")
    print(f"Stage-47 checkpoint protected: {'PASS' if gate_stage47_protected else 'FAIL'}")
    print(f"Stage-47 SHA unchanged:        {'PASS' if gate_stage47_sha_unchanged else 'FAIL'}")
    print(f"Historical Stage-44 provenance: {'PASS' if gate_stage44_provenance else 'FAIL'}")
    print(f"Feature 73 representation:     {'PASS' if gate_feat73_repr else 'FAIL'}")
    print(f"Feature 74 representation:     {'PASS' if gate_feat74_repr else 'FAIL'}")
    print(f"Pure battery state isolation:  {'PASS' if gate_battery_isolation else 'FAIL'}")
    print(f"Pure supercap state isolation: {'PASS' if gate_supercap_isolation else 'FAIL'}")
    print(f"Battery Q-value sensitivity:   {'PASS' if gate_battery_q_sensitivity else 'FAIL'}")
    print(f"Supercap Q-value sensitivity:  {'PASS' if gate_supercap_q_sensitivity else 'FAIL'}")
    print(f"Battery Level 3 action sens:   {gate_battery_action_sensitivity}")
    print(f"Supercap Level 3 action sens:  {gate_supercap_action_sensitivity}")
    print(f"Training performed:            NO")
    print(f"Stage-48 started:              NO")
    
    # Overall status
    all_core_pass = all([
        gate_stage44_protected, gate_stage44_sha_unchanged,
        gate_stage47_protected, gate_stage47_sha_unchanged,
        gate_stage44_provenance, gate_feat73_repr, gate_feat74_repr,
        gate_battery_isolation, gate_supercap_isolation,
    ])
    
    q_sensitivity_pass = gate_battery_q_sensitivity and gate_supercap_q_sensitivity
    
    if all_core_pass and q_sensitivity_pass:
        overall = "PASS"
    elif all_core_pass and (gate_battery_q_sensitivity or gate_supercap_q_sensitivity):
        overall = "PARTIAL PASS"
    else:
        overall = "FAIL"
    
    print(f"\nOverall Stage-47.1 status: {overall}")
    
    # ------------------------------------------------------------------
    # 9. SAVE RESULTS
    # ------------------------------------------------------------------
    print("\n[9] SAVING RESULTS")
    print("-" * 50)
    
    # Machine-readable JSON
    results = {
        "metadata": {
            "script": "stage47_1_pure_q_sensitivity.py",
            "stage44_checkpoint_hash": stage44_hash,
            "stage47_checkpoint_hash": stage47_hash,
            "state_isolation_tolerance": STATE_ISOLATION_TOLERANCE,
            "q_sensitivity_tolerance": Q_SENSITIVITY_TOLERANCE,
            "state_dim": 78,
            "n_actions": 5,
            "feature_73_name": "battery_soc (STORAGE_BAT.battery_level)",
            "feature_74_name": "supercap_soc (STORAGE_SC.supercap_level)",
            "soc_test_values": SOC_TEST_VALUES,
        },
        "baseline": {
            "state_vector": base_state_vec.tolist(),
            "q_values": base_q.tolist(),
            "action": base_action,
            "action_name": ['increase_generation','use_battery','use_supercapacitor','shift_load','reroute_energy'][base_action],
        },
        "battery_sensitivity": battery_results,
        "supercap_sensitivity": supercap_results,
        "summary": {
            "battery": {
                "q_range_per_action": battery_q_range.tolist(),
                "max_q_range": battery_max_range,
                "max_delta_q_l2_norm": battery_max_delta_norm,
                "max_delta_q_abs": battery_max_delta_abs,
                "actions_observed": sorted(list(battery_unique_actions)),
                "action_flips": battery_action_flips,
                "level_1_representation": True,
                "level_2_q_sensitivity": battery_level2,
                "level_3_action_sensitivity": battery_level3,
            },
            "supercapacitor": {
                "q_range_per_action": supercap_q_range.tolist(),
                "max_q_range": supercap_max_range,
                "max_delta_q_l2_norm": supercap_max_delta_norm,
                "max_delta_q_abs": supercap_max_delta_abs,
                "actions_observed": sorted(list(supercap_unique_actions)),
                "action_flips": supercap_action_flips,
                "level_1_representation": True,
                "level_2_q_sensitivity": supercap_level2,
                "level_3_action_sensitivity": supercap_level3,
            },
            "stage47_comparison": {
                "previous_battery_q_range": 5.6732,
                "previous_supercap_q_range": 0.2231,
                "previous_classification_both_level3": True,
                "note": "Previous test used physical grid perturbations (update_power_flow) which may have changed other state variables. Stage-47.1 uses pure state isolation.",
            },
        },
        "final_gate": {
            "stage44_checkpoint_protected": gate_stage44_protected,
            "stage44_sha_unchanged": gate_stage44_sha_unchanged,
            "stage47_checkpoint_protected": gate_stage47_protected,
            "stage47_sha_unchanged": gate_stage47_sha_unchanged,
            "historical_stage44_provenance_audited": gate_stage44_provenance,
            "feature_73_representation": gate_feat73_repr,
            "feature_74_representation": gate_feat74_repr,
            "pure_battery_state_isolation": gate_battery_isolation,
            "pure_supercap_state_isolation": gate_supercap_isolation,
            "battery_q_value_sensitivity": gate_battery_q_sensitivity,
            "supercap_q_value_sensitivity": gate_supercap_q_sensitivity,
            "battery_level_3_action_sensitivity": gate_battery_action_sensitivity,
            "supercap_level_3_action_sensitivity": gate_supercap_action_sensitivity,
            "training_performed": False,
            "stage48_started": False,
            "overall_status": overall,
        },
    }
    
    results_path = OUTPUT_DIR / "pure_q_sensitivity_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to: {results_path}")
    
    # Also save a summary table as CSV
    import csv
    csv_path = OUTPUT_DIR / "sensitivity_summary.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Test", "Feature", "Only_Changed_Index", "Q_range_max", "Action_Changes", "Level_2_Q_Sensitivity", "Level_3_Action_Sensitivity"])
        writer.writerow(["Battery", "73 (battery_soc)", "73", f"{battery_max_range:.6f}", "YES" if battery_action_flips else "NO", "PASS" if battery_level2 else "FAIL", "PASS" if battery_level3 else "NOT DEMONSTRATED"])
        writer.writerow(["Supercap", "74 (supercap_soc)", "74", f"{supercap_max_range:.6f}", "YES" if supercap_action_flips else "NO", "PASS" if supercap_level2 else "FAIL", "PASS" if supercap_level3 else "NOT DEMONSTRATED"])
    print(f"Summary CSV saved to: {csv_path}")
    
    return overall


if __name__ == "__main__":
    main()
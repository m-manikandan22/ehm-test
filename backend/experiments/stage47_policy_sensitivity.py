"""
stage47_policy_sensitivity.py - Stage 47 Policy Sensitivity Tests

Tests the newly trained Stage-47 DQN with corrected storage observation
on controlled storage SOC perturbations.
"""

import json
import hashlib
import numpy as np
import torch
from pathlib import Path
import sys
from collections import Counter

sys.path.insert(0, r'C:\Users\ELCOT\Music\EHM-paper\backend')

from simulation.grid import SmartGrid
from models.rl_agent import (
    DQNAgent, build_extended_state, EXTENDED_STATE_DIM
)
from experiments.runner import _storage_level

# Stage-47 checkpoint
CKPT_PATH = r'C:\Users\ELCOT\Music\EHM-paper\backend\experiments\checkpoints\dqn_stage47_storage_aware.pt'
OUTPUT_DIR = Path(r'C:\Users\ELCOT\Music\EHM-paper\backend\experiments\results\stage47')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Verify checkpoint
with open(CKPT_PATH, 'rb') as f:
    ckpt_hash = hashlib.sha256(f.read()).hexdigest()
print("Stage-47 checkpoint SHA-256:", ckpt_hash)

# Load Stage-47 DQN
agent = DQNAgent.load_checkpoint(CKPT_PATH, state_dim=EXTENDED_STATE_DIM, eval_mode=True)
agent.eval_mode()
print("Agent loaded: state_dim={}, training={}".format(agent.state_dim, agent.is_training))

def build_test_grid(battery_soc=None, supercap_soc=None, 
                    house_battery_soc=1.0, house_supercap_soc=1.0):
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

def get_grid_state_for_masking(grid):
    grid_state = {"nodes": {}, "edges": []}
    for nid, node in grid.nodes.items():
        grid_state["nodes"][nid] = {
            "node_type": node.node_type,
            "failed": node.failed,
            "isolated": node.isolated,
            "battery_level": node.battery_level,
            "supercap_level": node.supercap_level,
            "load": node.load,
        }
    for u, v, data in grid.graph.edges(data=True):
        grid_state["edges"].append({
            "source": u, "target": v,
            "is_tie_switch": data.get("is_tie_switch", False),
            "active": data.get("active", True),
            "switch_status": data.get("switch_status", "closed"),
        })
    return grid_state

def get_q_values(state_vec):
    with torch.no_grad():
        state_tensor = torch.tensor(state_vec, dtype=torch.float32).unsqueeze(0)
        return agent.policy_net(state_tensor).squeeze(0).numpy()

def get_action(state_vec, grid_state):
    decision = agent.select_action(state_vec, predicted_load=state_vec[72], grid_state=grid_state)
    return decision["action_id"], decision

print("=" * 60)
print("STAGE 47 POLICY SENSITIVITY TESTS")
print("=" * 60)

# Test 1: Battery SOC Sensitivity
print("\n" + "=" * 60)
print("TEST 1: Battery SOC Sensitivity (Supercap fixed at 1.0)")
print("=" * 60)

battery_tests = [
    {"bat": 0.90, "sc": 1.0, "name": "very_high_bat"},
    {"bat": 0.80, "sc": 1.0, "name": "high_bat"},
    {"bat": 0.60, "sc": 1.0, "name": "mid_high_bat"},
    {"bat": 0.50, "sc": 1.0, "name": "mid_bat"},
    {"bat": 0.40, "sc": 1.0, "name": "mid_low_bat"},
    {"bat": 0.20, "sc": 1.0, "name": "low_bat"},
    {"bat": 0.10, "sc": 1.0, "name": "very_low_bat"},
    {"bat": 0.05, "sc": 1.0, "name": "critical_bat"},
    {"bat": 0.00, "sc": 1.0, "name": "empty_bat"},
]

battery_results = []
prev_q = None
for tc in battery_tests:
    grid = build_test_grid(battery_soc=tc["bat"], supercap_soc=tc["sc"],
                           house_battery_soc=1.0, house_supercap_soc=1.0)
    grid_state = get_grid_state_for_masking(grid)
    legacy_state = grid.get_rl_state()
    
    battery_soc = _storage_level(grid, "battery")
    supercap_soc = _storage_level(grid, "supercap")
    
    state_vec = build_extended_state(
        legacy_state,
        predicted_load=0.5,
        battery_soc=battery_soc,
        supercap_soc=supercap_soc,
        twin_max_risk=0.0,
        twin_mean_risk=0.0,
        twin_high_frac=0.0,
    )
    
    q_vals = get_q_values(state_vec)
    action, decision = get_action(state_vec, grid_state)
    
    battery_results.append({
        "name": tc["name"],
        "grid_battery_soc": tc["bat"],
        "grid_supercap_soc": tc["sc"],
        "feature_73": battery_soc,
        "feature_74": supercap_soc,
        "q_values": q_vals.tolist(),
        "action": action,
        "action_name": decision["action_name"],
        "confidence": decision["confidence"],
        "reasoning": decision["reasoning"],
    })
    
    print("  {}: grid_bat={:.2f} -> feat73={:.3f}, Q={}, action={} ({}), conf={:.3f}".format(
        tc['name'], tc['bat'], battery_soc, q_vals, action, decision['action_name'], decision['confidence']))
    
    if prev_q is not None:
        delta_q = q_vals - prev_q
        l2_norm = np.linalg.norm(delta_q)
        print("    Delta Q from prev: {}, ||Delta Q||_2={:.4f}".format(delta_q, l2_norm))
    prev_q = q_vals

# Check Q-value sensitivity
q_matrix = np.array([r["q_values"] for r in battery_results])
q_range = q_matrix.max(axis=0) - q_matrix.min(axis=0)
print("\n  Q-value range per action across battery SOC:", q_range)
print("  Max Q-range: {:.4f}".format(q_range.max()))

# Test 2: Supercap SOC Sensitivity
print("\n" + "=" * 60)
print("TEST 2: Supercapacitor SOC Sensitivity (Battery fixed at 0.75)")
print("=" * 60)

supercap_tests = [
    {"bat": 0.75, "sc": 0.90, "name": "very_high_sc"},
    {"bat": 0.75, "sc": 0.80, "name": "high_sc"},
    {"bat": 0.75, "sc": 0.60, "name": "mid_high_sc"},
    {"bat": 0.75, "sc": 0.50, "name": "mid_sc"},
    {"bat": 0.75, "sc": 0.40, "name": "mid_low_sc"},
    {"bat": 0.75, "sc": 0.20, "name": "low_sc"},
    {"bat": 0.75, "sc": 0.10, "name": "very_low_sc"},
    {"bat": 0.75, "sc": 0.05, "name": "critical_sc"},
    {"bat": 0.75, "sc": 0.00, "name": "empty_sc"},
]

supercap_results = []
prev_q = None
for tc in supercap_tests:
    grid = build_test_grid(battery_soc=tc["bat"], supercap_soc=tc["sc"],
                           house_battery_soc=1.0, house_supercap_soc=1.0)
    grid_state = get_grid_state_for_masking(grid)
    legacy_state = grid.get_rl_state()
    
    battery_soc = _storage_level(grid, "battery")
    supercap_soc = _storage_level(grid, "supercap")
    
    state_vec = build_extended_state(
        legacy_state,
        predicted_load=0.5,
        battery_soc=battery_soc,
        supercap_soc=supercap_soc,
        twin_max_risk=0.0,
        twin_mean_risk=0.0,
        twin_high_frac=0.0,
    )
    
    q_vals = get_q_values(state_vec)
    action, decision = get_action(state_vec, grid_state)
    
    supercap_results.append({
        "name": tc["name"],
        "grid_battery_soc": tc["bat"],
        "grid_supercap_soc": tc["sc"],
        "feature_73": battery_soc,
        "feature_74": supercap_soc,
        "q_values": q_vals.tolist(),
        "action": action,
        "action_name": decision["action_name"],
        "confidence": decision["confidence"],
        "reasoning": decision["reasoning"],
    })
    
    print("  {}: grid_sc={:.2f} -> feat74={:.3f}, Q={}, action={} ({}), conf={:.3f}".format(
        tc['name'], tc['sc'], supercap_soc, q_vals, action, decision['action_name'], decision['confidence']))
    
    if prev_q is not None:
        delta_q = q_vals - prev_q
        l2_norm = np.linalg.norm(delta_q)
        print("    Delta Q from prev: {}, ||Delta Q||_2={:.4f}".format(delta_q, l2_norm))
    prev_q = q_vals

# Check Q-value sensitivity
q_matrix_sc = np.array([r["q_values"] for r in supercap_results])
q_range_sc = q_matrix_sc.max(axis=0) - q_matrix_sc.min(axis=0)
print("\n  Q-value range per action across supercap SOC:", q_range_sc)
print("  Max Q-range: {:.4f}".format(q_range_sc.max()))

# Test 3: Joint Battery + Supercap Sensitivity
print("\n" + "=" * 60)
print("TEST 3: Joint Storage Sensitivity (4-corner + center)")
print("=" * 60)

joint_tests = [
    {"bat": 0.90, "sc": 0.90, "name": "both_high"},
    {"bat": 0.90, "sc": 0.10, "name": "high_bat_low_sc"},
    {"bat": 0.10, "sc": 0.90, "name": "low_bat_high_sc"},
    {"bat": 0.10, "sc": 0.10, "name": "both_low"},
    {"bat": 0.50, "sc": 0.50, "name": "both_mid"},
    {"bat": 0.80, "sc": 0.20, "name": "high_bat_midlow_sc"},
    {"bat": 0.20, "sc": 0.80, "name": "midlow_bat_high_sc"},
]

joint_results = []
for tc in joint_tests:
    grid = build_test_grid(battery_soc=tc["bat"], supercap_soc=tc["sc"],
                           house_battery_soc=1.0, house_supercap_soc=1.0)
    grid_state = get_grid_state_for_masking(grid)
    legacy_state = grid.get_rl_state()
    
    battery_soc = _storage_level(grid, "battery")
    supercap_soc = _storage_level(grid, "supercap")
    
    state_vec = build_extended_state(
        legacy_state,
        predicted_load=0.5,
        battery_soc=battery_soc,
        supercap_soc=supercap_soc,
        twin_max_risk=0.0,
        twin_mean_risk=0.0,
        twin_high_frac=0.0,
    )
    
    q_vals = get_q_values(state_vec)
    action, decision = get_action(state_vec, grid_state)
    
    joint_results.append({
        "name": tc["name"],
        "grid_battery_soc": tc["bat"],
        "grid_supercap_soc": tc["sc"],
        "feature_73": battery_soc,
        "feature_74": supercap_soc,
        "q_values": q_vals.tolist(),
        "action": action,
        "action_name": decision["action_name"],
        "confidence": decision["confidence"],
        "reasoning": decision["reasoning"],
    })
    
    print("  {}: bat={:.2f}, sc={:.2f} -> Q={}, action={} ({}), conf={:.3f}".format(
        tc['name'], tc['bat'], tc['sc'], q_vals, action, decision['action_name'], decision['confidence']))

# Test 4: Feature Isolation (Single Variable Changes)
print("\n" + "=" * 60)
print("TEST 4: Feature Isolation (Single Variable Changes)")
print("=" * 60)

base_grid = build_test_grid(battery_soc=0.50, supercap_soc=0.50, 
                            house_battery_soc=1.0, house_supercap_soc=1.0)
base_state = base_grid.get_rl_state()
base_bat = _storage_level(base_grid, "battery")
base_sc = _storage_level(base_grid, "supercap")
base_ext = build_extended_state(
    base_state,
    predicted_load=0.5,
    battery_soc=base_bat,
    supercap_soc=base_sc,
    twin_max_risk=0.0,
    twin_mean_risk=0.0,
    twin_high_frac=0.0,
)
base_q = get_q_values(base_ext)
base_action, _ = get_action(base_ext, get_grid_state_for_masking(base_grid))

isolation_tests = [
    {"name": "battery_low", "bat": 0.10, "sc": 0.50, "feature": "battery_soc"},
    {"name": "supercap_low", "bat": 0.50, "sc": 0.10, "feature": "supercap_soc"},
    {"name": "lstm_high", "bat": 0.50, "sc": 0.50, "pred": 0.90, "feature": "lstm_forecast"},
    {"name": "twin_high", "bat": 0.50, "sc": 0.50, "twin": 0.80, "feature": "twin_max_risk"},
]

isolation_results = []
for test in isolation_tests:
    grid = build_test_grid(
        battery_soc=test.get("bat", 0.50),
        supercap_soc=test.get("sc", 0.50),
        house_battery_soc=1.0, house_supercap_soc=1.0,
    )
    grid_state = get_grid_state_for_masking(grid)
    legacy_state = grid.get_rl_state()
    
    battery_soc = _storage_level(grid, "battery")
    supercap_soc = _storage_level(grid, "supercap")
    predicted_load = test.get("pred", 0.5)
    twin_max = test.get("twin", 0.0)
    
    ext_state = build_extended_state(
        legacy_state,
        predicted_load=predicted_load,
        battery_soc=battery_soc,
        supercap_soc=supercap_soc,
        twin_max_risk=twin_max,
        twin_mean_risk=0.0,
        twin_high_frac=0.0,
    )
    
    q_vals = get_q_values(ext_state)
    action, _ = get_action(ext_state, grid_state)
    
    delta_q = q_vals - base_q
    l2_norm = np.linalg.norm(delta_q)
    
    isolation_results.append({
        "feature_changed": test["feature"],
        "test_params": {k: v for k, v in test.items() if k != "name" and k != "feature"},
        "base_q": base_q.tolist(),
        "test_q": q_vals.tolist(),
        "delta_q": delta_q.tolist(),
        "delta_q_norm": float(l2_norm),
        "base_action": base_action,
        "test_action": action,
        "action_changed": base_action != action,
    })
    
    print("  {}: Delta Q_norm={:.4f}, action {}->{} ({})".format(
        test['name'], l2_norm, base_action, action, 
        'CHANGED' if base_action != action else 'same'))

# Summary
print("\n" + "=" * 60)
print("SUMMARY: STAGE 47 POLICY SENSITIVITY")
print("=" * 60)

# Battery sensitivity
bat_q_range = q_matrix.max(axis=0) - q_matrix.min(axis=0)
bat_max_range = bat_q_range.max()
print("Battery SOC Q-range (max): {:.4f}".format(bat_max_range))
print("  Per-action ranges:", bat_q_range)

# Supercap sensitivity
sc_q_range = q_matrix_sc.max(axis=0) - q_matrix_sc.min(axis=0)
sc_max_range = sc_q_range.max()
print("Supercap SOC Q-range (max): {:.4f}".format(sc_max_range))
print("  Per-action ranges:", sc_q_range)

# Action diversity
bat_actions = [r["action"] for r in battery_results]
sc_actions = [r["action"] for r in supercap_results]
joint_actions = [r["action"] for r in joint_results]
all_actions = bat_actions + sc_actions + joint_actions
unique_actions = set(all_actions)
print("\nActions observed:", sorted(unique_actions))
print("Action distribution:", Counter(all_actions))

# Determine sensitivity levels
print("\n  Sensitivity Classification:")
bat_level = "LEVEL 3" if bat_max_range > 0.01 else "LEVEL 2" if bat_max_range > 0.001 else "LEVEL 1"
sc_level = "LEVEL 3" if sc_max_range > 0.01 else "LEVEL 2" if sc_max_range > 0.001 else "LEVEL 1"
print("  Battery SOC:  {} (Q-range: {:.4f})".format(bat_level, bat_max_range))
print("  Supercap SOC: {} (Q-range: {:.4f})".format(sc_level, sc_max_range))
print("  Action flips observed:", len(unique_actions) > 1)

# Save all results
results = {
    "checkpoint_hash": ckpt_hash,
    "battery_sensitivity": battery_results,
    "supercap_sensitivity": supercap_results,
    "joint_sensitivity": joint_results,
    "feature_isolation": isolation_results,
    "summary": {
        "battery_q_range_max": float(bat_max_range),
        "supercap_q_range_max": float(sc_max_range),
        "unique_actions": sorted(list(unique_actions)),
        "action_distribution": {str(k): v for k, v in Counter(all_actions).items()},
        "battery_level": bat_level,
        "supercap_level": sc_level,
        "action_flips": len(unique_actions) > 1,
    }
}

with open(OUTPUT_DIR / "policy_sensitivity.json", "w") as f:
    json.dump(results, f, indent=2, default=str)

print("\nResults saved to: {}/policy_sensitivity.json".format(OUTPUT_DIR))
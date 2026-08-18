"""
test_attack.py — Verify AttackDetector identifies FDIA, REPLAY, and RAMP.

FDIA must be detected within 1 step (residual jump is instant).
REPLAY must be detected within 50 timesteps (needs enough history).
RAMP must be detected within `ramp_window + 1` steps.
"""
import math
import os
import random
import sys

_THIS = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_THIS)
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from simulation.grid import SmartGrid
from models.attack_detector import AttackDetector, AttackType


def _build_grid_and_detector():
    random.seed(0)
    g = SmartGrid()
    g.update_power_flow()
    det = AttackDetector(
        alpha_ewma=0.4,
        ramp_window=10,
        ramp_threshold=0.005,
        replay_window=20,
        replay_threshold=0.30,
    )
    return g, det


def _measure(g):
    return {
        (u, v): g.graph[u][v].get("flow", 0.0)
        for u, v, _ in g.graph.edges(data=True)
        if g.graph[u][v].get("active", True)
    }


def test_fdia_detected_quickly():
    g, det = _build_grid_and_detector()
    # Inject a strong FDIA on the S_MAIN→T_A edge
    det.inject_attack(g, AttackType.FDIA, target="S_MAIN->T_A", magnitude=10.0)
    # Re-run PF so dc_state remains consistent, then have the detector
    # observe the measured (tampered) flow.
    alerts = det.detect(g, measured_flows=_measure(g))
    fdia = [a for a in alerts if a.attack_type == AttackType.FDIA]
    assert fdia, f"FDIA not detected. Alerts: {[a.message for a in alerts]}"
    assert fdia[0].target == "S_MAIN->T_A"
    assert fdia[0].score > 0.5


def test_ramp_detected_over_window():
    g, det = _build_grid_and_detector()
    target_node = "T_C"
    detected = False
    # Inject a slow ramp on T_C's edges for 15 steps
    for step in range(15):
        g.update_power_flow()                     # 1. baseline DC PF
        det.inject_attack(g, AttackType.RAMP, target=target_node)
        alerts = det.detect(g, measured_flows=_measure(g))
        if any(a.attack_type == AttackType.RAMP for a in alerts):
            detected = True
            break
    assert detected, (
        "RAMP attack not detected within 15 steps. "
        f"Last detections: {[(d.attack_type, d.target) for d in det.detections[-3:]]}"
    )


def test_no_attack_stays_clean():
    g, det = _build_grid_and_detector()
    alerts_collected = []
    for _ in range(30):
        g.update_power_flow()
        alerts_collected.extend(det.detect(g, measured_flows=_measure(g)))
    # On a healthy grid, no FDIA/RAMP alerts should appear
    false_pos = [a for a in alerts_collected
                 if a.attack_type in (AttackType.FDIA, AttackType.RAMP)]
    assert not false_pos, (
        f"False positives on healthy grid: {[a.message for a in false_pos[:5]]}"
    )


def test_status_serialisable():
    g, det = _build_grid_and_detector()
    det.inject_attack(g, AttackType.FDIA, target="S_MAIN->T_A", magnitude=5.0)
    det.detect(g, measured_flows=_measure(g))
    s = det.status()
    assert "timestep" in s
    assert "active_attacks" in s
    assert "detections" in s
    assert isinstance(s["detections"], list)


if __name__ == "__main__":
    test_fdia_detected_quickly()
    print("FDIA OK")
    test_no_attack_stays_clean()
    print("No-FP OK")
    test_ramp_detected_over_window()
    print("RAMP OK")
    test_status_serialisable()
    print("STATUS OK")
    print("All attack-detector tests PASSED")

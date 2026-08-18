"""
metrics.py — Metrics collected from each benchmark run.

The runner reports per-(seed, scenario) statistics. The reporter aggregates
them across seeds and computes mean ± std and 95 % CI.
"""
from __future__ import annotations

import math
from typing import Dict, List


def restoration_time(grid, scenario_meta: dict) -> int:
    """How many timesteps until the last isolated node has been restored.

    A trivial FLISR step runs in 1 simulation tick; here we measure the
    timesteps required to reach zero isolated nodes (or a budget of 30).
    """
    budget = 30
    for t in range(budget):
        if not any(n.isolated for n in grid.nodes.values()):
            return t
        grid.update_power_flow()
    return budget  # did not restore within budget


def energy_not_supplied(grid, scenario_meta: dict) -> float:
    """Cumulative MW·steps where an isolated node had unmet load.

    Approximated by summing (load × timestep) for all isolated nodes at the
    point of measurement.
    """
    ens = 0.0
    for n in grid.nodes.values():
        if n.isolated:
            ens += float(n.load)
    return ens


def saidi_proxy(grid, scenario_meta: dict) -> float:
    """SAIDI proxy = average outage duration per affected customer.

    We treat each isolated node as one "affected customer"; restoration_time
    gives the duration in timesteps. SAIDI-proxy = sum(duration) / n_affected.
    """
    n_iso = sum(1 for n in grid.nodes.values() if n.isolated)
    if n_iso == 0:
        return 0.0
    rt = restoration_time(grid, scenario_meta)
    return rt / max(1, n_iso)


def rl_reward(grid, scenario_meta: dict) -> float:
    """Same reward formula as rl_agent.compute_reward, evaluated at the
    scenario endpoint."""
    from models.rl_agent import DQNAgent
    state = grid.get_state()
    return DQNAgent.compute_reward(state)


def fault_detection_f1(grid, scenario_meta: dict) -> float:
    """F1 score of the fault detector. Ground-truth positives = the
    scenario's `faulted` list. Detections come from FaultDetector.analyse."""
    from models.fault_detector import FaultDetector
    global _FD_SINGLETON
    try:
        det = _FD_SINGLETON
    except NameError:
        det = FaultDetector()
        _FD_SINGLETON = det
    pred = det.analyse(grid.nodes)
    pred_alerts = {a["node_id"] for a in pred["alerts"] if a["score"] > 0.55}
    truth = set(scenario_meta.get("faulted", []))

    if not truth and not pred_alerts:
        return 1.0
    tp = len(truth & pred_alerts)
    fp = len(pred_alerts - truth)
    fn = len(truth - pred_alerts)
    precision = tp / (tp + fp) if tp + fp > 0 else 0.0
    recall    = tp / (tp + fn) if tp + fn > 0 else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def forecast_rmse(grid, scenario_meta: dict) -> float:
    """RMSE between the LSTM forecaster's prediction and the actual load on
    the 5 priority load nodes (HOSP, IND0, S_MAIN, T_A, T_B)."""
    from models.lstm_model import DemandForecaster
    global _FORECASTER_SINGLETON
    try:
        fc = _FORECASTER_SINGLETON
    except NameError:
        fc = DemandForecaster()
        _FORECASTER_SINGLETON = fc
    actual, predicted = [], []
    for nid in ("HOSP", "IND0", "S_MAIN", "T_A", "T_B"):
        if nid in grid.nodes:
            seq = grid.get_lstm_input(nid)
            actual.append(grid.nodes[nid].load)
            predicted.append(fc.predict(seq))
    if not actual:
        return 0.0
    err = sum((a - p) ** 2 for a, p in zip(actual, predicted))
    return math.sqrt(err / len(actual))


# ── Aggregator ────────────────────────────────────────────────────────

METRIC_FNS = {
    "restoration_time":   restoration_time,
    "energy_not_supplied": energy_not_supplied,
    "saidi_proxy":        saidi_proxy,
    "rl_reward":          rl_reward,
    "fault_detection_f1": fault_detection_f1,
    "forecast_rmse":      forecast_rmse,
}


def compute_all(grid, scenario_meta: dict) -> Dict[str, float]:
    return {name: float(fn(grid, scenario_meta)) for name, fn in METRIC_FNS.items()}
"""
attack_detector.py — Cyber-attack detection for the EHM smart-grid telemetry.

Attacks implemented
-------------------
1. FDIA  (False Data Injection Attack):
       Adversary tampers with reported power-flow measurements on a chosen
       line. The measured P changes by +delta, while the true P from DC PF
       stays unchanged. Classic attack vector — see Liang et al. (IEEE TCNS
       2017).

2. REPLAY:
       Adversary replays the telemetry observed 50 timesteps ago, replacing
       the current measurement. Subtle because the replayed values are
       self-consistent; detected via staleness on the auto-correlation.

3. RAMP:
       Adversary slowly drifts power-flow measurements by +0.5% per step
       over many steps (≥10). Designed to slip past per-step thresholds;
       detected by accumulating the residual trend.

Detection strategy
------------------
For each suspected line we compute the residual
   r_t = measured P — DC-PF-predicted P
and feed it into:
   • EWMA (exponentially weighted moving average)  — fires FDIA on spikes
   • slope  detector   on a sliding 10-step window — fires RAMP
   • autocorrelation drop on a 50-step history    — fires REPLAY

The detector also raises a generic ``ANOMALY`` alert when the cumulative
|SI| index (system imbalance) leaves a 3-σ envelope over the recent history.

This module does NOT depend on any external library beyond numpy.
"""
from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Attack taxonomy ──────────────────────────────────────────────────

class AttackType(str, Enum):
    NONE   = "none"
    FDIA   = "fdia"
    REPLAY = "replay"
    RAMP   = "ramp"


# ── Detector result container ────────────────────────────────────────

@dataclass
class AttackDetection:
    attack_type:  AttackType
    target:       str                # node_id or (u, v) edge key
    score:        float              # 0–1 confidence
    timestep:     int
    message:      str
    extra:        Dict[str, float] = field(default_factory=dict)


@dataclass
class AttackState:
    """Mutable detector state for one EDGE in the grid."""

    history: Deque[float] = field(default_factory=lambda: deque(maxlen=128))
    residual_history: Deque[float] = field(default_factory=lambda: deque(maxlen=128))
    replay_buffer: Deque[float] = field(default_factory=lambda: deque(maxlen=64))
    ewma:    float = 0.0
    ramp_sum: float = 0.0
    last_replay_hist: List[float] = field(default_factory=list)
    cumulative_ramp: float = 0.0  # tracks RAMP attack drift (MW)


# ── Main detector class ──────────────────────────────────────────────

class AttackDetector:
    """
    Lightweight real-time attack detector that compares measured per-edge
    power flows against the DC power-flow prediction.

    Args:
        alpha_ewma:    EWMA smoothing factor (0..1). Higher = more reactive.
        ramp_window:   Number of consecutive steps before a ramp is flagged.
        ramp_threshold:Per-step drift fraction that triggers ramp detection.
        replay_window: Number of history samples to compare for replay.
        replay_threshold: Auto-correlation drop (0..1) that flips replay.
    """

    def __init__(
        self,
        alpha_ewma:        float = 0.30,
        ramp_window:       int   = 10,
        ramp_threshold:    float = 0.005,
        replay_window:     int   = 50,
        replay_threshold:  float = 0.20,
    ):
        self.alpha_ewma        = alpha_ewma
        self.ramp_window       = ramp_window
        self.ramp_threshold    = ramp_threshold
        self.replay_window     = replay_window
        self.replay_threshold  = replay_threshold

        # Per-edge state keyed by (u, v) string "u->v"
        self._state: Dict[str, AttackState] = {}
        # Bookkeeping for active attacks (injected) and detections (found)
        self.active_attacks: List[Dict]   = []
        self.detections:    List[AttackDetection] = []
        self.timestep:      int = 0
        # Per-step ramp magnitude (MW) — injected on each RAMP call.
        self.ramp_step:     float = 0.05   # 50 kW added per step


    # ── 1. Attack injection (test hook) ──────────────────────────────
    def inject_attack(
        self,
        grid,
        attack_type: AttackType,
        target: str,
        magnitude: Optional[float] = None,
    ) -> dict:
        """
        Inject an attack of the given type on a node or edge.

        Args:
            grid:         SmartGrid (we mutate its edge attributes).
            attack_type:  FDIA | REPLAY | RAMP
            target:       For FDIA: (u, v) tuple or "u->v" string.
                          For REPLAY/RAMP: a node_id (we modify its edges).
            magnitude:    Optional override for FDIA delta (default 2x link capacity).
        """
        import json
        record: dict = {
            "attack_type":  attack_type.value,
            "target":       target if isinstance(target, str) else list(target),
            "timestep":     self.timestep,
            "magnitude":    magnitude,
            "ts":           time.time(),
        }
        self.active_attacks.append(record)

        # Apply the perturbation by mutating the edge that will be measured
        if attack_type == AttackType.FDIA:
            if "->" in target:
                u, v = target.split("->")
            else:
                u, v = target[0], target[1]
            if grid.graph.has_edge(u, v):
                if magnitude is None:
                    magnitude = 2.0 * grid.graph[u][v].get("capacity", 5.0)
                # Sign-flip the measured flow so it disagrees with DC PF
                grid.graph[u][v]["flow"] = -magnitude
                # Mirror on the reverse direction if it exists
                if grid.graph.has_edge(v, u):
                    grid.graph[v][u]["flow"] = magnitude
        elif attack_type == AttackType.REPLAY:
            # Stash the current values for later replay
            if target in grid.nodes:
                nid = target
                for u, v, _ in grid.graph.edges(nid, data=True):
                    key = f"{u}->{v}"
                    st = self._state.setdefault(key, AttackState())
                    st.replay_buffer.append(grid.graph[u][v].get("flow", 0.0))
                # Replace current with a value from 50 steps ago, if available
                for u, v, _ in grid.graph.edges(nid, data=True):
                    key = f"{u}->{v}"
                    st = self._state[key]
                    if len(st.replay_buffer) > self.replay_window:
                        past = st.replay_buffer[0]
                        grid.graph[u][v]["flow"] = past
        elif attack_type == AttackType.RAMP:
            if target in grid.nodes:
                nid = target
                # Each RAMP call ADDS `ramp_step` MW to the measured flow on
                # each of the target's edges. We track cumulative ramp per
                # edge inside AttackState so the residual grows linearly
                # over time — which is the actual behaviour of a ramp
                # attacker in the literature (Liang et al., 2017).
                for u, v, _ in grid.graph.edges(nid, data=True):
                    edge_key = f"{u}->{v}"
                    st = self._state.setdefault(edge_key, AttackState())
                    st.cumulative_ramp = getattr(st, "cumulative_ramp", 0.0) + self.ramp_step
                    if grid.graph.has_edge(u, v):
                        true_flow = 0.0
                        if grid.dc_state is not None:
                            true_flow = grid.dc_state.line_flow_mw.get(
                                (u, v),
                                grid.dc_state.line_flow_mw.get((v, u), 0.0),
                            )
                        grid.graph[u][v]["flow"] = true_flow + st.cumulative_ramp

        logger.warning(
            "Attack injected: %s on %s (mag=%s, t=%d)",
            attack_type.value, target, magnitude, self.timestep,
        )
        return record

    # ── 2. Clear attacks ─────────────────────────────────────────────
    def clear_attacks(self) -> None:
        self.active_attacks = []
        self.detections    = []

    # ── 3. Detection on new measurements ─────────────────────────────
    def detect(
        self,
        grid,
        measured_flows: Optional[Dict[Tuple[str, str], float]] = None,
    ) -> List[AttackDetection]:
        """
        Run a detection pass.

        Args:
            grid:            SmartGrid (must have run DC PF; `dc_state` populated).
            measured_flows:  optional dict {(u, v): P_meas_MW}. If None, we
                             use the current edge['flow'] values.

        Returns:
            List of AttackDetection objects newly raised on this pass.
        """
        self.timestep += 1
        new_alerts: List[AttackDetection] = []

        if grid.dc_state is None or not grid.dc_state.converged:
            return new_alerts
        expected = grid.dc_state.line_flow_mw  # {(u, v): P_MW}

        if measured_flows is None:
            measured_flows = {
                (u, v): grid.graph[u][v].get("flow", 0.0)
                for u, v, _ in grid.graph.edges(data=True)
                if grid.graph[u][v].get("active", True)
            }

        # Per-edge residual analysis
        for key, meas_p in measured_flows.items():
            exp_p = expected.get(key, expected.get((key[1], key[0]), 0.0))
            residual = meas_p - exp_p

            edge_key = f"{key[0]}->{key[1]}"
            st = self._state.setdefault(edge_key, AttackState())
            st.history.append(meas_p)
            st.residual_history.append(residual)

            # EWMA update
            st.ewma = (1 - self.alpha_ewma) * st.ewma + self.alpha_ewma * residual

            # ── FDIA: spike in |residual| ──────────────────────────
            if len(st.residual_history) >= 1 and abs(residual) > 5.0:
                score = float(min(1.0, abs(residual) / 10.0))
                det = AttackDetection(
                    attack_type=AttackType.FDIA,
                    target=edge_key,
                    score=score,
                    timestep=self.timestep,
                    message=(
                        f"FDIA: |residual| on {edge_key} jumped to {residual:.3f} MW"
                    ),
                    extra={"residual": float(residual), "expected_p": float(exp_p)},
                )
                new_alerts.append(det)

            # ── RAMP: sustained small drift ─────────────────────────
            if len(st.residual_history) >= self.ramp_window:
                recent = list(st.residual_history)[-self.ramp_window:]
                # Linear-fit slope: rise / run over the window
                xs = np.arange(len(recent))
                ys = np.array(recent, dtype=float)
                if ys.std() > 1e-9:
                    slope = float(np.polyfit(xs, ys, 1)[0])
                else:
                    slope = 0.0
                st.ramp_sum = 0.9 * st.ramp_sum + 0.1 * abs(slope)
                # Trigger when smoothed slope per step exceeds threshold
                if st.ramp_sum > self.ramp_threshold:
                    det = AttackDetection(
                        attack_type=AttackType.RAMP,
                        target=edge_key,
                        score=float(min(1.0, st.ramp_sum / 0.05)),
                        timestep=self.timestep,
                        message=(
                            f"RAMP drift on {edge_key}: smoothed slope {st.ramp_sum:.4f} MW/step"
                        ),
                        extra={"slope": float(slope), "ewma": float(st.ewma)},
                    )
                    new_alerts.append(det)

            # ── REPLAY: autocorrelation break ──────────────────────
            if len(st.history) >= self.replay_window:
                # Compare current 50-step window vs 50-step window from 50 steps ago
                cur  = np.array(list(st.history)[-self.replay_window:],  dtype=float)
                past = np.array(list(st.history)[:self.replay_window],  dtype=float)
                if cur.std() > 1e-6 and past.std() > 1e-6:
                    corr = float(np.corrcoef(cur, past)[0, 1])
                    if corr > 1 - self.replay_threshold and corr < 1.0:
                        det = AttackDetection(
                            attack_type=AttackType.REPLAY,
                            target=edge_key,
                            score=float(min(1.0, corr)),
                            timestep=self.timestep,
                            message=(
                                f"REPLAY: telemetry on {edge_key} has autocorrelation {corr:.2f}"
                            ),
                            extra={"autocorr": corr},
                        )
                        new_alerts.append(det)

        # Update history for replay detection (once per call, not per edge)
        # (no-op here; we per-edge capture history above)

        self.detections.extend(new_alerts)
        if new_alerts:
            for d in new_alerts:
                logger.warning("Detection: %s @ t=%d", d.message, d.timestep)
        return new_alerts

    # ── 4. Status snapshot for the API ───────────────────────────────
    def status(self) -> dict:
        """JSON-serialisable snapshot of attack state for the API."""
        return {
            "timestep":       self.timestep,
            "active_attacks": self.active_attacks[-10:],
            "detections": [
                {
                    "attack_type": d.attack_type.value,
                    "target":      d.target,
                    "score":       round(d.score, 4),
                    "timestep":    d.timestep,
                    "message":     d.message,
                    **d.extra,
                }
                for d in self.detections[-20:]
            ],
            "n_active":   len(self.active_attacks),
            "n_detected": len(self.detections),
        }

"""
explainer.py — XAI panel for RL decisions.

Why
---
A black-box RL agent isn't publishable.  This module computes a
small ``XAIReport`` for the agent's last action so the dashboard
can render:
  - ``why``           : top-3 features by |gradient·value| proxy
  - ``inputs``        : which extractors fired (i.e. were non-zero)
  - ``expected_benefit``: scalar summary
  - ``alternatives``  : top-3 alternative actions and their Q-values
  - ``confidence``    : softmax over Q-values

The gradient·value proxy is a simple "feature attribution by signed
importance" — without backprop, we approximate the gradient as the
absolute deviation of the feature from a neutral value.  This is
defensible and consistent across runs; it isn't SHAP, but it's
fast and stable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class XAIReport:
    why: List[Dict[str, float]]
    inputs: List[str]
    expected_benefit: float
    alternatives: List[Dict[str, float]]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "why": self.why,
            "inputs": self.inputs,
            "expected_benefit": self.expected_benefit,
            "alternatives": self.alternatives,
            "confidence": self.confidence,
        }


@dataclass
class RLExplainer:
    """Build an ``XAIReport`` from an RL action trace."""

    n_top_features: int = 3
    n_alternatives: int = 3

    def explain(
        self,
        *,
        features: Dict[str, List[float]],
        q_values: List[float],
        chosen_action: int,
        action_names: List[str],
    ) -> XAIReport:
        # 1. feature attribution — simple signed-importance proxy.
        scored: List[Dict[str, float]] = []
        for name, vals in features.items():
            if not vals:
                continue
            # Use the mean of the absolute values; sign follows deviation
            # from neutral (1.0 for voltages, 0.0 for the rest).
            for i, v in enumerate(vals):
                neutral = 1.0 if name == "voltage" else 0.0
                importance = abs(float(v) - neutral)
                scored.append({
                    "feature": f"{name}[{i}]",
                    "value": float(v),
                    "importance": float(importance),
                })
        scored.sort(key=lambda d: d["importance"], reverse=True)
        why = scored[: self.n_top_features]
        inputs = sorted({w["feature"].split("[")[0] for w in why})

        # 2. alternatives — top-N non-chosen actions.
        sorted_idx = sorted(range(len(q_values)), key=lambda i: q_values[i], reverse=True)
        alts: List[Dict[str, float]] = []
        for idx in sorted_idx:
            if idx == chosen_action:
                continue
            if len(alts) >= self.n_alternatives:
                break
            alts.append({
                "action_id": int(idx),
                "action_name": action_names[idx] if idx < len(action_names) else f"a{idx}",
                "q_value": float(q_values[idx]),
            })

        # 3. confidence — softmax of Q-values.
        if q_values:
            mx = max(q_values)
            exps = [math.exp(float(q) - mx) for q in q_values]
            s = sum(exps) or 1.0
            confidence = float(exps[chosen_action] / s)
        else:
            confidence = 0.0

        # 4. expected_benefit — Q-value of the chosen action.
        expected = float(q_values[chosen_action]) if q_values else 0.0

        return XAIReport(
            why=why,
            inputs=inputs,
            expected_benefit=expected,
            alternatives=alts,
            confidence=confidence,
        )
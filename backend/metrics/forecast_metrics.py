"""
forecast_metrics.py — point-forecast error metrics.

Why
---
For LSTM / transformer evaluation we need standard regression
metrics.  These are intentionally tiny, depend only on
``math``, and accept anything ``__len__``-aware.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence


def _aligned(actual: Sequence[float], predicted: Sequence[float]) -> int:
    return min(len(actual), len(predicted))


def mae(actual: Sequence[float], predicted: Sequence[float]) -> float:
    n = _aligned(actual, predicted)
    if n <= 0:
        return 0.0
    return sum(abs(a - p) for a, p in zip(actual, predicted[:n])) / n


def rmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    n = _aligned(actual, predicted)
    if n <= 0:
        return 0.0
    s = 0.0
    for a, p in zip(actual, predicted[:n]):
        d = a - p
        s += d * d
    return math.sqrt(s / n)


def mape(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Mean absolute percentage error in [0, +inf).  Zero actuals skipped."""
    n = _aligned(actual, predicted)
    if n <= 0:
        return 0.0
    pct: list[float] = []
    for a, p in zip(actual, predicted[:n]):
        if abs(float(a)) > 1e-9:
            pct.append(abs((a - p) / a))
    if not pct:
        return 0.0
    return sum(pct) / len(pct)
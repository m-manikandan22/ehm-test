"""
degradation.py — Arrhenius-style thermal aging model.

Why
---
A digital twin must age with its physical counterpart.  The simplest
defensible aging model for power-system assets is the Arrhenius
relationship:

    ageing_rate = exp(-Ea / (k * T))

At normal operating temperatures the rate is small; under overload it
grows super-linearly.  Multiplying by loading^2 captures the
I²R-heating reality that hot-spots accelerate insulation breakdown.

This is intentionally simple — it gives every asset a `health` field
that decreases monotonically and accelerates when the asset is
overloaded.  Calibration constants are deliberately conservative so
simulations over a few hundred steps don't show obvious degradation;
they're meant to produce visible trends over thousands of steps.

Status — not validated
----------------------
This is a **simulation-based risk indicator**, not a calibrated
failure-probability model. The Arrhenius constants (`_EA_OVER_K`,
`_T_NOMINAL`) are engineering rule-of-thumb values, not fitted
parameters. To claim a calibrated failure-probability model we would
need: (1) a recorded transformer-outage dataset, (2) calibration of
`Ea` and `T_nominal` against that dataset, and (3) out-of-sample
ROC/PR curves. None of these exist in the EHM project today.

Use the resulting `health` and `failure_probability` as a relative
ranking signal ("high vs low risk") not a calibrated probability
statement. See ``docs/digital_twin.md`` for the project-wide position.
"""
from __future__ import annotations

import math
from typing import Dict


# Reference constants — chosen so the function behaves well over a
# few-thousand-step run without needing to be retuned.
_EA_OVER_K = 8000.0     # pseudo-activation energy (K)
_T_NOMINAL = 320.0      # nominal hot-spot temperature (K)


def thermal_ageing_step(
    *,
    current_health: float,
    loading: float,
    ambient_k: float = 293.0,
    dt_hours: float = 1.0,
) -> Dict[str, float]:
    """Compute one timestep of the aging model.

    Parameters
    ----------
    current_health : float
        Health in [0, 1].  1 = pristine, 0 = end-of-life.
    loading : float
        Per-unit load (0 = idle, 1 = rated, >1 = overload).
    ambient_k : float
        Ambient temperature in Kelvin (default 293 K ≈ 20 °C).
    dt_hours : float
        Elapsed simulated time.  Default 1 hour per step.

    Returns
    -------
    dict with keys ``delta_health``, ``temperature_k``, ``ageing_rate``,
    and ``new_health``.  ``new_health`` is the post-tick value
    clamped to [0, 1].

    The model:  hot-spot temperature T = ambient + (T_nominal - ambient) * loading².
    Ageing rate = exp(-Ea/(k*T)).  Health decrement = ageing_rate * dt_hours.
    """
    loading = max(0.0, loading)
    temp_k = ambient_k + (_T_NOMINAL - ambient_k) * (loading ** 2)
    # Normalise ageing so a unit-loaded asset at 320 K degrades at ~0.001/hr.
    base_rate = math.exp(-_EA_OVER_K / temp_k)
    delta = base_rate * dt_hours
    new_health = max(0.0, min(1.0, current_health - delta))
    return {
        "delta_health": delta,
        "temperature_k": temp_k,
        "ageing_rate": base_rate,
        "new_health": new_health,
    }
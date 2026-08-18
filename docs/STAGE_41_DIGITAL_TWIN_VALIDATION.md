# Stage 41 — Digital-Twin Validation

This document validates the digital-twin component against the
on-disk artefacts and source code. We do NOT run a new digital-twin
experiment in Stage 41 — we evaluate the existing implementation
honestly.

---

## 1. Where the digital twin lives

`backend/digital_twin/twin.py::DigitalTwin` with a `health` field in
`[0, 1]` and a derived `health_risk_score ∈ [0, 1]` computed via
`_health_risk_from_health`.

`backend/digital_twin/degradation.py::thermal_ageing_step` implements
an Arrhenius-style ageing model that nudges `health` downward each
tick.

The Stage-40 gate text is explicit about the limitation:

> *"`health_risk_score` (heuristic) — not a calibrated failure
> prediction."*

We confirm and elaborate.

## 2. What the twin can represent

* A per-asset health estimate in [0, 1].
* A per-asset risk score in [0, 1].
* An Arrhenius-style degradation rate (`thermal_ageing_step`).
* A registry (`TwinRegistry`) so the SCADA control center can look
  up twins by node ID.

## 3. What the twin is *not*

* Not calibrated against field failure data.
* Not trained on any real distribution of failure times.
* Not used as an input to any controller in the Stage-26 paper
  experiments.

A `grep -rn "health_risk_score"` across `backend/` excluding the
declaration site returns **no consumers**. Specifically:

```
$ grep -rn "health_risk_score" backend/
backend/digital_twin/twin.py:18:  - ``health_risk_score``    : heuristic in [0, 1] — *not* a
backend/digital_twin/twin.py:28:This module therefore exposes the canonical name ``health_risk_score``
backend/digital_twin/twin.py:53:def _health_risk_from_health(h: float) -> float:
backend/digital_twin/twin.py:75:    _health_risk_score: float = field(default=0.0, init=True, repr=False)
backend/digital_twin/twin.py:78:    # Derived property — keeps health_risk_score in lock-step with
backend/digital_twin/twin.py:83:    def health_risk_score(self) -> float:
backend/digital_twin/twin.py:93:        return _health_risk_from_health(self.health)
backend/digital_twin/twin.py:95:    @health_risk_score.setter
backend/digital_twin/twin.py:96:    def health_risk_score(self, value: float) -> float:
backend/digital_twin/twin.py:112:        """DEPRECATED alias for ``health_risk_score``.
backend/digital_twin/twin.py:116:        ``health_risk_score`` — see main.md Stage 10.
backend/digital_twin/twin.py:120:            "use DigitalTwin.health_risk_score instead. "
backend/digital_twin/twin.py:125:        return self.health_risk_score
backend/digital_twin/twin.py:131:            "use DigitalTwin.health_risk_score instead.",
backend/digital_twin/twin.py:135:        self.health_risk_score = value
backend/digital_twin/twin.py:158:    from digital_twin.degradation import thermal_ageing_step
backend/digital_twin/twin.py:177:    self.health_risk_score = _health_risk_from_health(self.health)
backend/digital_twin/twin.py:196:    "health_risk_score": self.health_risk_score,
backend/digital_twin/twin.py:211:     ``health_risk_score`` as ``clip((0.4 - H_proj)/0.4)`` when
```

All hits are either declarations, getters/setters, aliases, or
docstrings. **No consumer in the simulation, the runner, the SCADA
control loop, or any ablation row.**

## 4. What the Stage-26 paper experiments can claim about the twin

* The digital twin exists as a module with documented limitations.
* The Stage-26 results do not depend on it (it is never invoked).
* The Stage-26 `no_twin` ablation is a no-op for the same reason as
  the other ablations: the harness doesn't gate the flag.

## 5. What a calibrated twin would require

The user prompt explicitly notes:

> *"Calibrate the digital-twin heuristic against any available
> field data (REQUIRES EXTERNAL DATA)."*

This is correctly out of scope for Stage 41 (and indeed for any
single-author paper project). The calibration data would have to
come from a utility partner.

## 6. What we *can* do without field data

We can demonstrate **simulation-based health-aware predictive
control** — not calibrated failure prediction, but the *idea* that
the controller uses the twin's risk score to re-route around an
at-risk asset before it fails. To make this claim defensible, Stage
42 should:

1. Implement Scenario H (degraded asset + fault) from the scenario
   matrix.
2. Run the same scenario with `twin_aware = True` and `twin_aware =
   False` (where `twin_aware` means the controller reads
   `twin.health_risk_score` and prefers to reroute around high-risk
   assets).
3. Report the difference in ENS, restoration_time, and number of
   faults that became "unrecoverable" because the controller
   refused to route through them.

## 7. Honest framing

> **The digital twin is implemented as a heuristic with explicit
> limitations, and it is not consumed by any controller in the
> Stage-26 paper experiments. We do not claim the twin improves
> decision-making. We present it as a *future-work* component that
> requires calibration and a controlled stress scenario (Scenario
> H).**

## 8. Recommendations for Stage 42

1. Wire `health_risk_score` into the DQN state vector so it
   influences action selection. This is a 1-line change in the
   `StateBuilder` module.
2. Implement Scenario H.
3. Run the twin-aware vs twin-unaware comparison.
4. If the difference is negligible, report that honestly.

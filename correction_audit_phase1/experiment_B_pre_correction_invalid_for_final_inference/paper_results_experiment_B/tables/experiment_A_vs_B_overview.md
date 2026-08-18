# Experiment A vs Experiment B — Overview

Experiment A and Experiment B are *independent* experiments that answer *different* research questions. Their raw samples are **never** merged into one homogeneous dataset.


## Experimental design contrast

| Item | Experiment A | Experiment B |
|---|---|---|
| Conditions | Nominal | Stress / constrained |
| Fault severity | 1–3 steps | moderate: 10–20; severe: 25–50 |
| Concurrent faults | 1 (3 sequential) | up to 2 (moderate), up to 3 (severe) |
| Capacity margin | Effectively unlimited | constrained (tie_capacity_mw 5.6 / 3.2) |
| Load level | 1.0× | 1.2× (moderate), 1.5× (severe) |
| Weather | normal | normal / storm |
| Critical-load competition | no | yes (fraction 0.7 / 0.4) |
| Controller variance | saturated | differentiates on secondary metrics |
| Primary findings | saturation | under-reported — see results |
| Research question | does the framework run? | does it help under stress? |

## Why two experiments?

Experiment A's null finding (no measurable controller differentiation on the standard metrics) is a *legitimate* scientific result. It is the evidence that motivates the stress benchmark. Experiment B is what the experiment looks like when the benchmark is allowed to be discriminating.

Critically, the *nominal* 49-node benchmark's near-flat tail of metrics is not a defect of the framework; it is evidence that the benchmark's disturbance profile is too mild to engage the controller's differentiating mechanisms.

Under the stress benchmark, the same FLISR engines and the same controllers are evaluated under conditions that demand differentiated decisions. The result is reported as-is, with no tuning of the benchmark based on the cross-controller ranking.

The two experiments therefore share simulation code but differ in their *benchmark*. Their raw outputs are preserved side-by-side so that the contrast can be audited by a reviewer.

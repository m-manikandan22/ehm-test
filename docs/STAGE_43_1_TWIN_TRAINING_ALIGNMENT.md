# Stage 43.1 — Digital-Twin Training Alignment

## Method

`twin_alignment_audit` rebuilt the grid + twin registry for
Scenarios A and H with 3 seeds each. It recorded the time series of
`health_risk_score` per asset and the per-run max and mean.

Artefact: `experiments/results/stage43_1/twin_alignment.json`.

## Headline numbers

| Scenario | max_risk (max over seeds) | mean_risk (mean over seeds) |
|----------|--------------------------:|----------------------------:|
| A (no pre-aging)     | **0.0**   | 0.0              |
| H (one asset pre-aged) | 0.50   | 0.0102           |

`max_risk_per_seed` for Scenario A: `[0.0, 0.0, 0.0]`. Twin never
reaches the high-risk threshold (`>= 0.5`) during a clean run.

## Implications for the trained DQN

* Training had **zero** high-risk twin signal.
* The **only** way to introduce a high-risk twin signal during
  *evaluation* is via `cfg.enable_predictive_healing=True` or a
  Scenario H seed that forces a `health_override` mapping.
* The DQN's input features at positions 75–77 are `twin_max_risk`,
  `twin_mean_risk`, `twin_high_frac`. The network has only been
  exposed to `(0.0, 0.0, 0.0)` for these features during training.
  The Q-value audit's `high_twin_risk` state
  (`twin_max=0.9, twin_mean=0.6, twin_high=0.4`) is therefore
  out-of-distribution.

## But — the Q-value audit shows the network *does* respond

Even at out-of-distribution twin features, the argmax stays action 2.
The Q-values for `high_twin_risk`:

```
Q0=-1069.88   Q1=-1058.22   Q2=-1052.22   Q3=-1066.13   Q4=-1069.61
```

versus baseline:

```
Q0=-1070.76   Q1=-1059.11   Q2=-1053.09   Q3=-1067.02   Q4=-1070.50
```

All Q-values shifted by ~+1.0 (including Q2), so the network's
output *did* respond to the feature change — but the rank order did
not flip. **The twin signal does reach the network; the network
just has not learned to route that signal to action 4 (which is
where the reroute bonus would reward it).**

## H4 verdict — environment mismatch on twin? **Confirmed: yes.**

Training distribution for twin features: {0.0}.
Evaluation distribution: [0.0, 1.0] (with Scenario H
explicitly forcing 0.5+).

## Recommendation (Stage-44 candidate)

* Inject controlled health degradation during training (e.g. by
  randomly marking one asset at 0.4 health at the start of some
  training episodes).
* OR run additional training that uses the existing Scenario H
  health_override map.

## Files

- `backend/experiments/stage43_1_diag.py::twin_alignment_audit`
- `backend/experiments/info_flow.py::_pre_age_twins`, `_twin_risk_map`
- `experiments/results/stage43_1/twin_alignment.json`

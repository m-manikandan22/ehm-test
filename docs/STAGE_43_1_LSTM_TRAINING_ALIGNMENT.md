# Stage 43.1 — LSTM Training Alignment

## The Stage-43 standing concern

`STAGE_43_DQN_TRAINING.md` documents that the LSTM forecast feature
used during **training** is _not_ produced by the LSTM itself — it
is a stand-in derived from aggregate load:

```python
# dqn_training.py line 106
forecast_feature = max(0.05, min(2.0, _aggregate_load(grid) / 20.0))
```

At **evaluation** time the LSTM's actual prediction is fed in:

```python
# runner.py line 631
predicted_load = float(_lstm_forecaster.predict([...]))
```

## Evidence (`lstm_alignment.json`, n=60 step pairs)

| Quantity         | min    | max    | mean   | std   |
|------------------|-------:|-------:|-------:|------:|
| LSTM prediction  | 0.3040 | 0.4940 | 0.3758 | 0.0534 |
| Training feature | 0.7434 | 1.0758 | 0.9358 | 0.0824 |
| Aggregate load   | 14.87  | 21.52  | 18.72  | —     |

The two distributions **do not overlap**:

- LSTM prediction range ≈ [0.30, 0.49] (narrow band around 0.38).
- Training feature range ≈ [0.74, 1.08] (narrow band around 0.94).

The gap is ~0.4. The trained network has only seen forecast values
in [0.74, 1.08]; during evaluation the LSTM-driven feature lands in
[0.30, 0.49]. The DQN has not seen anything like the evaluation
distribution.

## What this means for the policy collapse

* The network's response to the LSTM channel has only been learned
  for inputs ~0.94. Below ~0.7 the network's behaviour is
  interpolation territory, at best.
* However, the Q-value audit (`q_values.json`) showed that varying
  `forecast` between 0.05 and 1.5 produced *no* change in argmax
  (action 2 stayed on top). The narrow LSTM range seen at evaluation
  time is therefore unlikely to be the cause of the collapse; the
  collapse is driven by the reward-shaping / training-scenario
  mismatch, not the LSTM.
* **But the alignment is still real and should be fixed.** Any
  Stage-44 LSTM-driven experiment must feed the LSTM's *own*
  prediction into the network during training — or the network will
  silently underfit the evaluation distribution.

## H4 verdict — environment mismatch? **Confirmed: yes (in this dimension).**

This is one of three environment-vs-training mismatches:

1. **No faults in training.** Training saw `num_failed=0`,
   `num_isolated=0` for all 800 transitions in the reward audit and
   the controlled-state analysis. Evaluation sees faults.
2. **Twin risk in [0.0, 0.5] for training vs [0.0, 1.0] for evaluation
   (especially Scenario H)** — see `STAGE_43_1_TWIN_TRAINING_ALIGNMENT.md`.
3. **Forecast feature distribution does not match** — this document.

## Recommendation (Stage-44 candidate, not Stage-43 fix)

Train with the actual LSTM feature (or a probe distribution
quantile-matched to the LSTM's output range, e.g. uniform
[0.0, 0.6]) so position 72 of the state vector has the same
distribution at training and evaluation.

## Files

- `backend/experiments/dqn_training.py` (training feature stand-in,
  line 106)
- `backend/experiments/runner.py` (LSTM-driven feature at evaluation,
  line 631)
- `experiments/results/stage43_1/lstm_alignment.json`

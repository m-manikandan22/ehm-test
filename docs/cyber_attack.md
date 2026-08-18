# Cyber-Attack Detection

EHM ships with a lightweight cyber-attack detector that compares per-edge
telemetry against the DC power-flow prediction and fires alerts on three
attack classes.

## Scope — what this module is, and is not

The cyber-attack detector is **demonstrative**. It exercises three
attack classes (FDIA, RAMP, REPLAY) against a per-edge residual baseline.
A research-grade multi-edge detector with calibrated thresholds is
**future work** for this project (see `docs/ROADMAP_AFTER_CRITICAL_10.md`).

What it is:
- A reference implementation of three attack classes for unit tests.
- A seed for research discussions ("how would you extend this?").

What it is not:
- A production-grade, calibrated, multi-edge FDIA detector.
- A replacement for real PMU-based intrusion detection.

## Attack model

| Attack | What the adversary does | What the detector looks at |
|--------|-------------------------|----------------------------|
| **FDIA** (False Data Injection) | Tampers with a measurement on one edge by a large magnitude. | Spikes in `|measured − DC-PF-predicted|` above 5 MW on any edge. |
| **RAMP** | Slowly drifts measurements by `ramp_step` MW per step (default 0.05 MW). | Linear-fit slope of the residual over a sliding window. Fires when smoothed slope exceeds 5 mW per step. |
| **REPLAY** | Replaces current telemetry with values from 50 steps ago. | Auto-correlation between current window and 50-step-old window drops below threshold. |

Each detection carries a confidence score (0–1) and the residual statistics
for traceability. The detector runs in O(edges × window) per step and is
CPU-only.

## Detector state (per-edge)

```python
@dataclass
class AttackState:
    history:          Deque[float]   # last 128 measured flows
    residual_history: Deque[float]   # last 128 residuals
    replay_buffer:    Deque[float]   # 64-window buffer for replay compare
    ewma:             float          # smoothed residual
    ramp_sum:         float          # smoothed slope (MW / step)
    cumulative_ramp:  float          # active ramp drift on this edge
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/attack` | Inject `{type, target, magnitude?}` |
| `GET`  | `/attack_status` | List active attacks and recent detections |
| `POST` | `/attack_clear` | Reset detector state |

Example: inject an FDIA on the S_MAIN → T_A feeder:

```bash
curl -X POST http://localhost:8000/attack \
     -H 'Content-Type: application/json' \
     -d '{"type":"fdia","target":"S_MAIN->T_A","magnitude":10.0}'
```

Example: read detector status:

```bash
curl http://localhost:8000/attack_status
```

## Limitations and future work

- **Linear residual baseline.** The detector compares measurements to
  the DC-PF prediction assuming all loads and generation are exactly known.
  In practice, demand forecast error creates noise that limits detection
  sensitivity. A residual baseline built from the last N timesteps
  (subtracting mean) would suppress this.
- **No fusion across edges — coordinated FDIA is unmitigated.** Sophisticated
  attacks (Liu et al. 2018) inject false data on a coordinated subset of
  edges that bypass per-edge detectors. Adding a multi-edge chi-squared test
  would close this gap. **This is explicitly future work**; the current
  detector is per-edge by design and should not be claimed as robust to
  coordinated attacks.
- **No replay buffer re-randomisation.** The REPLAY detector assumes an
  attacker who replays the same window; periodic re-randomisation of the
  buffer helps but is not implemented yet.
- **No real-time resilience to measurement noise.** Threshold tuning for
  production deployment requires labelled attack data from a real PMU
  stream. The hook is in place (`csv_path` style loaders exist for LSTM and
  FaultDetector); adding one to `AttackDetector` is straightforward.

**Out of scope for this paper:** multi-edge coordinated FDIA detection,
PMU-stream integration, false-alarm tuning. See
`docs/ROADMAP_AFTER_CRITICAL_10.md` "Future work" section.

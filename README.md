# AI Self-Healing Smart Grid — README

## Project Structure

```
simulation/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── requirements.txt
│   ├── models/
│   │   ├── lstm_model.py    # LSTM demand forecaster (PyTorch)
│   │   └── rl_agent.py      # DQN reinforcement learning agent
│   ├── simulation/
│   │   ├── grid.py          # NetworkX smart grid simulation
│   │   └── node.py          # GridNode with hybrid storage
│   └── api/
│       └── routes.py        # All FastAPI endpoints
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── index.css         # Dark-mode design system
        ├── main.jsx
        ├── components/
        │   ├── GridGraph.jsx     # D3.js force-directed graph
        │   ├── ControlPanel.jsx  # Left panel controls
        │   └── AIDecisionPanel.jsx # Right panel AI display
        ├── pages/
        │   └── Dashboard.jsx     # 3-panel main layout
        └── services/
            └── api.js            # Axios API wrapper
```

---

## 🚀 Quick Start

### Step 1 — Backend

```cmd
cd c:\Users\ELCOT\Music\TNWISE\simulation\backend

:: Install Python dependencies (only once)
pip install fastapi uvicorn[standard] numpy torch networkx scikit-learn pydantic python-multipart

:: Start the server
python main.py
```

Expected output:
```
AI Self-Healing Smart Grid — Backend Starting Up
[1/3] Initialising smart grid simulation...
[2/3] Loading LSTM demand forecaster...
[LSTM] Training complete. Final loss: 0.00xxxx
[3/3] Loading DQN reinforcement learning agent...
[DQN] Warm-up complete.
✅ All systems ready.
Uvicorn running on http://0.0.0.0:8000
```

### Step 2 — Frontend

```cmd
cd c:\Users\ELCOT\Music\TNWISE\simulation\frontend

:: Install JS dependencies (only once)
npm install

:: Start the dev server
npm run dev
```

Open: **http://localhost:5173**

---

## 🌐 API Endpoints

| Method | Endpoint    | Description |
|--------|-------------|-------------|
| GET    | `/state`    | Current grid state |
| POST   | `/simulate` | Step simulation + LSTM + DQN |
| POST   | `/event`    | Trigger failure / storm / demand |
| GET    | `/predict`  | LSTM forecast |
| POST   | `/action`   | Force RL action |
| POST   | `/reset`    | Reset grid |
| GET    | `/health`   | Health check |

### Example — Trigger Storm
```cmd
curl -X POST http://localhost:8000/event -H "Content-Type: application/json" -d "{\"type\":\"storm\"}"
```

### Example — Fail a Node
```cmd
curl -X POST http://localhost:8000/event -H "Content-Type: application/json" -d "{\"type\":\"failure\",\"node_id\":\"H2\"}"
```

---

## 🎮 Dashboard Controls

| Button | Effect |
|--------|--------|
| 📈 Increase Demand | Spikes load +0.3 MW on all house nodes |
| 🌩️ Trigger Storm | Weather event: load ×1.35, gen ×0.6 |
| ⚠️ Fail Node | Marks selected node as failed, triggers self-healing |
| 🔧 Restore Node | Brings node back online |
| ⚡ Boost Generation | Adds +0.4 MW to all substation generators |
| 🔄 Reset Grid | Returns to initial state |
| ⏸ Pause / ▶ Resume | Toggle auto-simulation (2s interval) |
| ⏭ Step | Manual single timestep when paused |

---

## 🧠 AI Architecture

### LSTM Forecaster
- 2-layer LSTM, hidden_size=32, CPU-only
- Input: `[load, generation, weather] × 10 timesteps`
- Output: predicted next-step demand (MW)
- Pre-trains on 500 synthetic samples at startup (~2 seconds)

### DQN Agent
- MLP: 40-dim state → 64 → 64 → 5 actions
- State: `[voltage, freq/50, load, generation, stress] × 8 nodes`
- Actions: increase_gen | use_battery | use_supercapacitor | shift_load | reroute_energy
- ε-greedy exploration (decays 1.0 → 0.05 over 200 steps)
- Target network synced every 20 steps

### Self-Healing Logic
1. Node failure injected via `inject_failure(node_id)`
2. All connecting edges disabled
3. BFS from substations checks all remaining nodes for connectivity
4. Disconnected nodes marked as `isolated`
5. DQN responds with `reroute_energy` action to reactivate cross-links

---

## ⚙️ Requirements

- Python ≥ 3.9
- Node.js ≥ 18
- No GPU required — all ML runs on CPU

---

## 📊 Scientific Validation Status

This section enumerates what is implemented, what is validated against an
external reference, and what is **simulation-based** (i.e. not a calibrated
prediction). See `docs/VALIDATION.md` for run commands and details.

### Implemented and validated

| Component | Validation |
|-----------|-----------|
| DC power flow | 5-bus textbook case KCL residual <1e-15; IEEE 13-bus vs pandapower DC PF — both solvers converge and agree in sign; see `experiments/results/ieee13_validation.json` for the per-bus diff |
| AC power flow (positive-sequence NR via pandapower) | Converges on textbook 5-bus and on the IEEE 13-bus positive-sequence equivalent; per-bus V in [0.95, 1.05] pu *on the balanced equivalent* (not the full per-phase IEEE spec) |
| IEEE 1366 reliability indices | Unit-tested against textbook edge cases (zero customers, total outage) |
| Experiment runner | Multi-config × multi-seed × multi-weather runs. Every `ExperimentConfig` boolean genuinely alters runtime behaviour. Validity guards exclude NaN/Inf/impossible-voltage runs. |
| Benchmark runner | Random vs rule-based across 10 scenarios × 3 weather modes, paired t-test |
| Ablation study | Drop-one-component harness — each `no_*` config disables a real module, not just relabels |
| City generator | Determinism test across seeds; expected counts vs realised counts |
| Twin registry | Idempotent register, sync update, at-risk threshold tests |
| Statistical tests | `paired_t`, `paired_t_pvalue`, `wilcoxon_signed_rank`, `cohens_d_paired`, `ci95`, `ci95_student` — all unit-tested on known samples |

### Implemented and demonstrative (simulation-based, not validated)

| Component | What it is | What it is NOT |
|-----------|-----------|----------------|
| Digital Twin failure-risk indicator | Piecewise linear step function of asset `health`. Used as a relative ranking signal. | A calibrated probability model. We have no recorded transformer-outage dataset to calibrate against. |
| Twin failure horizon projection | Linear extrapolation of the last 8 health samples. | A forecast. Sensitive to noise. |
| DQN `smart_warmup` | Rule-guided replay-buffer bootstrap. The expert is a hand-coded `if/elif` ladder; actions chosen by the ladder populate the replay buffer. The network is then trained on standard Bellman regression — not behavioural cloning. | Behavioural cloning, DAgger, or any genuine imitation-learning algorithm. |
| `RewardGuidedDecisionAgent` (formerly `AdvancedDQNAgent`) | Argmax over the `RewardComposer` breakdown. | A trained Q-network. The class was renamed in this release so the name does not overstate what it does; the old name is preserved as an alias. |
| FLISR tie-switch selection | Weighted scoring across priority, voltage-drop, switch count, and path-length. | An optimal or cost-minimum solution. Greedy heuristic. |
| Cyber-attack detector | Per-edge residual baseline; FDIA / RAMP / REPLAY classes. | Coordinated multi-edge FDIA detector (Liu et al. 2018). See `docs/cyber_attack.md`. |

### Out of scope (explicitly future work)

- Coordinated FDIA detection (multi-edge chi-squared test)
- PMU-stream integration with calibration against real measurement noise
- Empirical calibration of twin failure probability
- Three-phase unbalanced AC PF
- Hardware-in-the-loop deployment

See `docs/VALIDATION.md` for the complete validation story and run commands,
and `docs/EXPERIMENTS.md` for the paper-grade experiment workflow.

### Paper experiments

```bash
# One-command paper sweep — baseline + ablation + tables + manifest.
python -m experiments.paper_experiment \
    --seeds 100 --ticks 200 --faults 3 \
    --policies random,rule_based,dqn_core_only,full_stack \
    --ablation-policies full_stack,no_lstm,no_twin,no_predictive,no_reward,dqn_core_only \
    --output experiments/results/paper
```

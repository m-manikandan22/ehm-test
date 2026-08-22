# Stage 46.1 — State Layout (Frozen Checkpoint)

## 1. Dimensions

- `STATE_DIM = 72` — legacy vector from `SmartGrid.get_rl_state()`.
- `LSTM_FEATURE_DIM = 1`
- `STORAGE_FEATURE_DIM = 2`
- `TWIN_FEATURE_DIM = 3`
- `EXTENDED_STATE_DIM = 78`

Verified against `models/rl_agent.py::build_extended_state` and the frozen
checkpoint (policy net input layer accepts 78).

## 2. The 78-dim layout

```
index  range        feature(s)
------ ------------ --------------------------------------------------
  0–71  legacy      72-dim grid state:
                    - 7 global scalars (energy, deficit, weather, ...)
                    - per-priority-node blocks (13 nodes × 5 features)
 72     LSTM        predicted next-step aggregate load (DemandForecaster)
 73     STORAGE     max battery_level over house nodes
 74     STORAGE     max supercap_level over house nodes
 75     TWIN        max health_risk_score over twin registry
 76     TWIN        mean health_risk_score over twin registry
 77     TWIN        fraction of twins with health_risk_score >= 0.5
```

Priority node list referenced by the legacy block (verified live in grid):

```
GEN_SOLAR, GEN_WIND, GEN_NUCLEAR, GEN_COAL, GEN_GAS, S_MAIN,
STORAGE_BAT, STORAGE_SC, T_A, T_B, T_C, HOSP, IND0
```

## 3. Node-type ground truth (verified by probe)

| Node            | node_type     | comment                                   |
|-----------------|---------------|-------------------------------------------|
| S_MAIN          | substation    | EMS generation boost reset by node.step()  |
| STORAGE_BAT     | battery       | NOT "storage_bat"; invisible to actions 1/2|
| STORAGE_SC      | supercap      | NOT "storage_sc"; invisible to actions 1/2 |
| GEN_*           | generator_*   | solar/wind/nuclear/coal/gas                |
| T_A/T_B/T_C     | transformer   | health_override only on scenario H         |
| H1…H13          | house         | source of battery/supercap SOC features    |
| HOSP, IND0      | hospital/industry | critical consumers                        |

## 4. Feature gating matrix

| Flag              | Features affected | Ablation semantics                          |
|-------------------|-------------------|---------------------------------------------|
| `enable_lstm`     | 72                | False → exact 0.5 sentinel                  |
| `enable_twin`     | 75, 76, 77        | False → all 0.0                             |
| `enable_ems`      | none in DQN state | environment-side (external)                 |
| `enable_predictive` | none in DQN state | pure healer, never mutates grid             |

## 5. Weather proxy mapping (forecast input)

Used as the third coordinate of each LSTM history triple (matches the
production runner):

| weather_mode | proxy |
|--------------|-------|
| normal       | 0.2   |
| storm        | 0.85  |
| heatwave     | 0.5   |

> Note: the training loop used `max(0, min(1, demand_multiplier - 1))` as
> the weather coordinate. The two conventions produce different absolute
> forecast values but the same relative information; documented here for
> provenance.
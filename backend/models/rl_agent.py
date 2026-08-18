"""
rl_agent.py — DQN Reinforcement Learning agent for smart grid control.

State  (per node): [voltage, frequency/50, load, generation, stress] × 13 nodes = 65-dim
                     + 7 global features = 72-dim total
Actions (5 discrete):
  0 → Increase generation on all substations
  1 → Use battery storage (highest-deficit node)
  2 → Use supercapacitor (largest spike node)
  3 → Shift load (reduce 10% on house nodes)
  4 → Reroute energy (activate cross-links, trigger multi-agent share)

Reward:
  +2   per node close to nominal voltage (|v−1| < 0.05)
  +1   per node close to nominal frequency (|f−50| < 0.2)
  -5   per failed/isolated node
  -1   per node with stress > 0.7
  -0.1 × total_energy_loss (cost proxy)

DQN details:
  - 2-hidden-layer MLP (64→64)
  - Replay buffer (capacity 2000)
  - ε-greedy exploration (ε decays 1.0 → 0.05)
  - Target network updated every 20 steps
  - Warms up on 100 random experience samples at startup
"""

from __future__ import annotations

import random
import math
from collections import deque
from typing import List, Optional

import numpy as np  # type: ignore
import torch  # type: ignore
import torch.nn as nn  # type: ignore
import torch.optim as optim  # type: ignore


# -----------------------------------------------------------------------
# Action Catalogue
# -----------------------------------------------------------------------

ACTIONS = [
    {
        "id": 0,
        "name": "increase_generation",
        "label": "⚡ Boosting generation on substations",
        "color": "green",
    },
    {
        "id": 1,
        "name": "use_battery",
        "label": "🔋 Drawing from battery storage",
        "color": "blue",
    },
    {
        "id": 2,
        "name": "use_supercapacitor",
        "label": "⚡ Discharging supercapacitor (spike suppression)",
        "color": "cyan",
    },
    {
        "id": 3,
        "name": "shift_load",
        "label": "📊 Deferring non-critical loads",
        "color": "yellow",
    },
    {
        "id": 4,
        "name": "reroute_energy",
        "label": "🔀 Rerouting energy via alternate paths",
        "color": "purple",
    },
]

N_ACTIONS = len(ACTIONS)
# State dim = 13 priority nodes × 5 features + 7 global features = 72.
# The 13 priority nodes are: 5 generators, S_MAIN, 2 storage, 3 transformer
# feeders, HOSP, IND0. This matches SmartGrid.get_rl_state() default targets.
STATE_DIM = 72

# Stage-43 (Repair 5+6): the DQN's decision input is the legacy 72-dim
# vector PLUS the features that the Stage-42.5 audit proved never reached
# selection:
#   1. predicted_load   — LSTM forecast of next-step aggregate demand
#                         (Repair 5; 0.5 sentinel when LSTM is disabled)
#   2. battery_soc      — STORAGE_BAT battery_level (0..1)
#   3. supercap_soc     — STORAGE_SC supercap_level (0..1)
#   4. twin_max_risk    — max digital-twin health_risk_score (Repair 6)
#   5. twin_mean_risk   — mean health_risk_score
#   6. twin_high_frac   — fraction of assets with health_risk_score >= 0.5
LSTM_FEATURE_DIM = 1
STORAGE_FEATURE_DIM = 2
TWIN_FEATURE_DIM = 3
EXTENDED_STATE_DIM = STATE_DIM + LSTM_FEATURE_DIM + STORAGE_FEATURE_DIM + TWIN_FEATURE_DIM


def build_extended_state(
    state: list,
    predicted_load: float = 0.5,
    battery_soc: float = 0.0,
    supercap_soc: float = 0.0,
    twin_max_risk: float = 0.0,
    twin_mean_risk: float = 0.0,
    twin_high_frac: float = 0.0,
) -> list:
    """Append the Stage-43 decision features to the legacy 72-dim vector.

    ``state`` is the output of ``SmartGrid.get_rl_state()``. The layout
    is documented in ``docs/STAGE_43_LSTM_INTEGRATION.md`` and
    ``docs/STAGE_43_DIGITAL_TWIN_INTEGRATION.md``.
    """
    return list(state) + [
        float(predicted_load),
        float(battery_soc),
        float(supercap_soc),
        float(twin_max_risk),
        float(twin_mean_risk),
        float(twin_high_frac),
    ]


# -----------------------------------------------------------------------
# Neural Network Q-function
# -----------------------------------------------------------------------

class DQNetwork(nn.Module):
    """Simple MLP approximating Q(s, a) for all actions simultaneously."""

    def __init__(self, state_dim: int = STATE_DIM, n_actions: int = N_ACTIONS):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, n_actions),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# -----------------------------------------------------------------------
# Replay Buffer
# -----------------------------------------------------------------------

class ReplayBuffer:
    def __init__(self, capacity: int = 2000):
        self.buf = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buf.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int):
        batch = random.sample(self.buf, batch_size)
        s, a, r, ns, d = zip(*batch)
        return (
            torch.tensor(np.array(s), dtype=torch.float32),
            torch.tensor(a, dtype=torch.long),
            torch.tensor(r, dtype=torch.float32),
            torch.tensor(np.array(ns), dtype=torch.float32),
            torch.tensor(d, dtype=torch.float32),
        )

    def __len__(self):
        return len(self.buf)

    # ── Item 2 — persistence for reproducibility ─────────────────────────
    def save(self, path: str) -> None:
        """Persist the replay buffer to disk using pickle."""
        import pickle  # local import; not needed at module import
        with open(path, "wb") as f:
            pickle.dump(list(self.buf), f)

    def load(self, path: str) -> None:
        """Load a replay buffer from pickle; truncates capacity if smaller."""
        import pickle
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.buf = deque(data, maxlen=self.buf.maxlen)


# -----------------------------------------------------------------------
# DQN Agent
# -----------------------------------------------------------------------

class DQNAgent:
    """
    Deep Q-Network agent for smart grid control.
    Designed for CPU-only, fast iteration — suitable for hackathon demo.
    """

    GAMMA = 0.95
    LR = 1e-3
    BATCH_SIZE = 32
    EPSILON_START = 1.0
    EPSILON_END = 0.05
    EPSILON_DECAY = 200   # steps to decay ε
    TARGET_UPDATE = 20    # steps between target network sync

    def __init__(self, state_dim: int = STATE_DIM):
        self.state_dim = state_dim
        self.policy_net = DQNetwork(state_dim=state_dim)
        self.target_net = DQNetwork(state_dim=state_dim)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.LR)
        self.buffer = ReplayBuffer()
        self.criterion = nn.SmoothL1Loss()   # Huber loss

        self.steps_done = 0
        self.epsilon = self.EPSILON_START
        self._last_action_id = 0
        self._last_reasoning = ""

        # EHM-CRIT-006 fix: explicit train/eval separation. The agent
        # starts in training mode (learning enabled by default — callers
        # who only want greedy action selection must call ``eval_mode()``).
        self._training = True
        self._dropped_experiences = 0

        # Warm up is now called externally via smart_warmup(grid)

    # ------------------------------------------------------------------
    # Exploration schedule
    # ------------------------------------------------------------------

    def _get_epsilon(self) -> float:
        """Exponential ε decay (only used in training mode)."""
        eps = self.EPSILON_END + (self.EPSILON_START - self.EPSILON_END) * \
              math.exp(-self.steps_done / self.EPSILON_DECAY)
        return eps

    # ------------------------------------------------------------------
    # Train / Eval separation (EHM-CRIT-006)
    # ------------------------------------------------------------------

    def eval_mode(self) -> None:
        """Switch the agent to evaluation mode.

        In evaluation mode:
          - ``select_action`` is greedy (ε forced to 0).
          - ``store_experience`` does **not** push to the replay buffer
            or trigger gradient updates.
          - ``target_net.load_state_dict`` is not invoked.
        """
        self._training = False
        self.policy_net.eval()
        self.target_net.eval()

    def train_mode(self) -> None:
        """Switch the agent back to training mode (default)."""
        self._training = True
        self.policy_net.train()
        self.target_net.train()

    @property
    def is_training(self) -> bool:
        return bool(self._training)

    @property
    def dropped_experiences(self) -> int:
        """Count of experiences ignored because the agent was in eval mode."""
        return int(self._dropped_experiences)

    # ------------------------------------------------------------------
    # Checkpoint persistence (Stage-43 Repair 4)
    # ------------------------------------------------------------------

    def save_checkpoint(
        self,
        path: str,
        *,
        seeds: Optional[dict] = None,
        git_sha: str = "",
        extra: Optional[dict] = None,
    ) -> str:
        """Persist the policy network, the target network, the optimizer
        state and the training bookkeeping to ``path``.

        The replay buffer is NOT persisted (it is training-only scratch);
        the checkpoint is a frozen policy for evaluation.
        """
        import os
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        payload = {
            "policy_net": self.policy_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "steps_done": int(self.steps_done),
            "epsilon": float(self.epsilon),
            "state_dim": int(self.state_dim),
            "n_actions": int(N_ACTIONS),
            "seeds": dict(seeds or {}),
            "git_sha": str(git_sha),
            "extra": dict(extra or {}),
        }
        import torch as _torch
        _torch.save(payload, path)
        return path

    @classmethod
    def load_checkpoint(cls, path: str, *, state_dim: int = STATE_DIM,
                        eval_mode: bool = True) -> "DQNAgent":
        """Build an agent whose weights come from ``path``.

        When ``eval_mode`` is True (the default for experiment runs) the
        agent is frozen: greedy action selection, no buffer writes, no
        gradient steps, no target-net sync — evaluation cannot train.
        """
        import torch as _torch
        payload = _torch.load(path, map_location="cpu", weights_only=False)
        agent = cls(state_dim=int(payload.get("state_dim", state_dim)))
        agent.policy_net.load_state_dict(payload["policy_net"])
        agent.target_net.load_state_dict(payload["target_net"])
        agent.optimizer.load_state_dict(payload["optimizer"])
        agent.steps_done = int(payload.get("steps_done", 0))
        agent.epsilon = float(payload.get("epsilon", agent.EPSILON_END))
        if eval_mode:
            agent.eval_mode()
        else:
            agent.train_mode()
        return agent

    # ------------------------------------------------------------------
    # Rule-Guided Warm-Up (dataset bootstrapping, not imitation learning)
    # ------------------------------------------------------------------

    def smart_warmup(self, grid, scada_instance=None):
        """Populate the replay buffer with transitions whose *actions* are
        chosen by the rule ladder in ``rl.expert_policy.choose_action``.

        Important — what this method is and is not:

        ✅ It is **dataset bootstrapping from rule outputs**: the rule
        ladder is run for 150 steps, each rule-chosen action is
        dispatched via SCADA, and the resulting ``(state, action,
        reward, next_state)`` transition is pushed to the replay buffer.
        The network is then trained on standard Bellman regression over
        this dataset.

        ❌ It is **not** behavioural cloning. There is no
        ``state -> expert_action`` regression loss, no behavioural-
        cloning head, no DAgger, no queryable expert at training time.
        The expert policy is also evaluated only once at startup on a
        freshly-reset, healthy grid, with the random-fault-injection
        branch commented out — so the warm-up dataset is heavily biased
        toward the "balance<−0.1 → battery" and "else → load shift"
        branches.

        See ``backend/rl/expert_policy.py`` for the exact rule ladder
        and threshold rationale.
        """
        print("[DQN] Warming up replay buffer via rule-guided bootstrap "
              "(not imitation learning)...")

        from rl.expert_policy import choose_action as _expert_choose

        for _ in range(150):
            state = grid.get_rl_state()
            state_dict = grid.get_state()
            action_id = _expert_choose(state, state_dict)
            action_name = str(ACTIONS[action_id]["name"])

            # Apply and step.
            if scada_instance:
                scada_instance._dispatch_control_signal(action_name, state_dict, grid)
            grid.step()

            next_state_dict = grid.get_state()
            next_state = grid.get_rl_state()
            reward = self.compute_reward(next_state_dict, action_name)

            s = np.array(state, dtype=np.float32)
            ns = np.array(next_state, dtype=np.float32)
            self.buffer.push(s, action_id, reward, ns, False)

            # Inject random failure to teach recovery (disabled for clean
            # startup — keeps warm-up data on the "balance<0 → battery"
            # and "else → load shift" branches. See expert_policy.py.)
            # if random.random() < 0.02:
            #     grid.inject_failure(random.choice(["H0", "H1", "H2", "H3", "H4"]))

        # Run a batch of training to initialize network
        for _ in range(40):
            self._train_step()

        grid.reset()
        grid.heal_all()  # Ensure clean startup state
        print("[DQN] Smart warmup complete.")

    # ------------------------------------------------------------------
    # Action Selection
    # ------------------------------------------------------------------

    def _valid_actions_mask(self, grid_state: Optional[dict]) -> List[int]:
        """Physical-validity action mask (Stage-43 Repair 11).

        Each rule is a *physically impossible* condition, not a policy
        preference:

          - 0 increase_generation : invalid when no non-failed
                conventional generator exists to ramp.
          - 1 use_battery         : invalid when no energised node
                has any battery charge left.
          - 2 use_supercapacitor  : invalid when no energised node
                has any supercapacitor charge left.
          - 3 shift_load          : invalid when no energised node
                has load to defer.
          - 4 reroute_energy      : invalid when no physically closable
                tie switch exists (open, not fault-locked, both
                endpoints alive).

        ``grid_state`` is the dict from ``SmartGrid.get_state()``; when
        it is None (unit tests, stub grids) all actions are allowed.
        """
        if not grid_state:
            return [0, 1, 2, 3, 4]
        nodes = grid_state.get("nodes", {}) or {}
        edges = grid_state.get("edges", []) or []
        if not nodes:
            return [0, 1, 2, 3, 4]

        alive = [
            n for n in nodes.values()
            if not n.get("failed") and not n.get("isolated")
        ]
        gen_exists = any(
            str(n.get("node_type", "")).startswith("generator")
            for n in alive
        )
        battery_ok = any(
            float(n.get("battery_level", 0.0) or 0.0) > 0.001
            for n in alive
        )
        supercap_ok = any(
            float(n.get("supercap_level", 0.0) or 0.0) > 0.001
            for n in alive
        )
        load_ok = any(
            float(n.get("load", 0.0) or 0.0) > 0.001
            for n in alive
        )
        failed_ids = {nid for nid, n in nodes.items() if n.get("failed")}
        tie_ok = any(
            e.get("is_tie_switch")
            and not e.get("active", True)
            and e.get("switch_status") != "fault_locked"
            and e.get("source") not in failed_ids
            and e.get("target") not in failed_ids
            for e in edges
        )

        valid = []
        if gen_exists:
            valid.append(0)
        if battery_ok:
            valid.append(1)
        if supercap_ok:
            valid.append(2)
        if load_ok:
            valid.append(3)
        if tie_ok:
            valid.append(4)
        return valid

    def select_action(self, state: list, predicted_load: float = 0.5,
                      grid_state: Optional[dict] = None) -> dict:
        """
        Choose an action given the current state vector and context.
        Builds a human-readable reasoning string explaining the choice.

        Returns dict with: action_id, action_name, label, color, reasoning
        """
        state_vec = np.array(state, dtype=np.float32)
        # EHM-CRIT-006: in eval mode, disable exploration (ε forced to 0)
        # and don't increment the training step counter (which drives
        # ε decay and target-net sync).
        if self._training:
            self.epsilon = self._get_epsilon()
            self.steps_done += 1
        else:
            self.epsilon = 0.0
        
        # ── Action Masking — physical validity ONLY (Stage-43 Repair 11).
        # The mask may exclude actions that are *physically impossible*
        # at this timestep; it must NOT encode the desired policy
        # (e.g. "choose battery when demand is high"). Learning and
        # behaviour live in the Q-network, never in the mask.
        valid_actions = self._valid_actions_mask(grid_state)
        if not valid_actions:
            valid_actions = [0, 1, 2, 3, 4]

        # Action Selection and Confidence
        confidence = 0.0
        with torch.no_grad():
            q_vals = self.policy_net(torch.tensor(state_vec).unsqueeze(0))  # type: ignore
            mask = torch.full((1, N_ACTIONS), float('-inf'))
            for a in valid_actions:
                mask[0, a] = 0.0
            
            masked_q = q_vals + mask
            best_action = masked_q.argmax(dim=1).item()
            
            # Extract confidence using Softmax over valid actions
            valid_q = q_vals[mask == 0.0]
            if len(valid_q) > 0:
                probs = torch.nn.functional.softmax(valid_q, dim=0)
                confidence = probs.max().item()

        # Epsilon Greedy Override. Stage-43 (RNG isolation): randomness is
        # drawn ONLY during training. In eval mode epsilon is forced to 0.0
        # above and no global-RNG draw is consumed, so inference is
        # RNG-neutral and cannot perturb the environment noise stream.
        if self._training and random.random() < self.epsilon:
            action_id = random.choice(valid_actions)
            confidence = 1.0 / len(valid_actions)  # Low confidence on random jump
        else:
            action_id = best_action

        self._last_action_id = action_id
        action = ACTIONS[action_id]

        # Build reasoning
        reasoning = self._build_reasoning(action_id, predicted_load, grid_state)
        self._last_reasoning = reasoning

        return {
            "action_id": action_id,
            "action_name": action["name"],
            "label": action["label"],
            "color": action["color"],
            "reasoning": reasoning,
            "epsilon": round(float(self.epsilon), 3),  # type: ignore
            "confidence": round(float(confidence), 3),
        }

    def _build_reasoning(self, action_id: int, predicted_load: float,
                          grid_state: Optional[dict]) -> str:
        """Generate a human-readable explanation of why this action was chosen."""
        ctx_parts = []

        if grid_state:
            sys = grid_state.get("system", {})
            balance = sys.get("balance", 0)
            health = sys.get("health_score", 1.0)
            avg_v = sys.get("avg_voltage", 1.0)
            storm = grid_state.get("storm_active", False)
            failed = [nid for nid, n in grid_state.get("nodes", {}).items() if n.get("failed")]

            if storm:
                ctx_parts.append("🌩️ Storm active — high demand")
            if failed:
                ctx_parts.append(f"⚠️ Node(s) {failed} are failed")
            if predicted_load > 0.8:
                ctx_parts.append(f"📈 High demand predicted ({predicted_load:.2f} MW)")
            elif predicted_load < 0.3:
                ctx_parts.append(f"📉 Low demand predicted ({predicted_load:.2f} MW)")
            if balance < -0.3:
                ctx_parts.append("🔴 Grid deficit detected")
            elif balance > 0.5:
                ctx_parts.append("🟢 Grid surplus — stable")
            if health < 0.5:
                ctx_parts.append(f"🚨 System health low ({health:.0%})")
            if abs(avg_v - 1.0) > 0.08:
                ctx_parts.append(f"⚡ Voltage deviation ({avg_v:.3f} p.u.)")

        context = " | ".join(ctx_parts) if ctx_parts else "Routine monitoring"
        action_label = ACTIONS[action_id]["label"]

        return f"{context} → {action_label}"

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    def store_experience(self, state: list, action_id: int, reward: float,
                         next_state: list, done: bool = False):
        """Push a transition to the replay buffer and train.

        EHM-CRIT-006: in evaluation mode the transition is **not** stored,
        no gradient step is taken, and the target network is not synced.
        This keeps the policy frozen for reproducible evaluation.
        """
        if not self._training:
            self._dropped_experiences += 1
            return

        s = np.array(state, dtype=np.float32)
        ns = np.array(next_state, dtype=np.float32)
        self.buffer.push(s, action_id, reward, ns, done)

        if len(self.buffer) >= self.BATCH_SIZE:
            self._train_step()

        # Periodically sync target network
        if self.steps_done % self.TARGET_UPDATE == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

    def _train_step(self):
        """One gradient-descent step on a random batch from the replay buffer."""
        if len(self.buffer) < self.BATCH_SIZE:
            return

        states, actions, rewards, next_states, dones = self.buffer.sample(self.BATCH_SIZE)

        # Zero gradients BEFORE forward pass to avoid stale graph references
        self.optimizer.zero_grad()

        # Current Q-values for taken actions (fresh forward pass)
        q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(-1)

        # Target Q-values (Bellman equation) — fully detached from computation graph
        with torch.no_grad():
            next_q = self.target_net(next_states).max(1)[0]
            targets = (rewards + self.GAMMA * next_q * (1 - dones)).detach()

        loss = self.criterion(q_values, targets)
        loss.backward()
        # Gradient clipping for stability
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()

    # ------------------------------------------------------------------
    # Reward Computation
    # ------------------------------------------------------------------

    @staticmethod
    def compute_reward(grid_state: dict, action_name: str = "") -> float:
        """
        Compute a sharp, intentional reward focused on stability, balance, and minimizing failure.
        """
        reward = 0.0
        nodes = grid_state.get("nodes", {})
        system = grid_state.get("system", {})

        avg_voltage = system.get("avg_voltage", 1.0)
        avg_freq = system.get("avg_frequency", 50.0)
        balance = system.get("balance", 0.0)
        total_energy_loss = system.get("total_energy_loss", 0.0)

        num_failed = sum(1 for n in nodes.values() if n.get("failed"))
        num_isolated = sum(1 for n in nodes.values() if n.get("isolated"))

        # Stability (HIGH priority)
        reward += 5.0 * (1.0 - abs(avg_voltage - 1.0) / 0.1)
        reward += 3.0 * (1.0 - abs(avg_freq - 50.0) / 1.5)

        # Balance (VERY IMPORTANT)
        reward -= 4.0 * abs(balance)

        # Failure penalty (CRITICAL)
        reward -= 10.0 * num_failed
        reward -= 6.0 * num_isolated

        # Efficiency
        reward -= 0.2 * total_energy_loss

        # Smart behavior conditional bonuses
        if action_name == "use_supercapacitor" and any(n.get("load", 0) > 1.2 for n in nodes.values()):
            reward += 2.0
            
        if action_name == "reroute_energy" and (num_failed > 0 or num_isolated > 0):
            reward += 3.0

        return float(reward)

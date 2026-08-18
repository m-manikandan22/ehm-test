"""
experiment_config.py — Central configuration for scientific experiments.

This is the *single source of truth* for what is enabled and disabled
during an experimental run. Every flag below is consumed by the
experiment runner, the controller factory, the predictor, the digital
twin, and the FLISR module — flipping a flag genuinely alters runtime
behaviour. There is no "label-only" mode.

Why this exists
---------------
The previous ablation harness described configurations in comments but
did not actually switch off the underlying modules. This led to
ablation runs where "no_lstm" still consumed LSTM features. The
ExperimentConfig below fixes that by being the only path through which
controllers and assistants are constructed.

Status
------
Demonstrative, not research-grade — the configuration is structurally
correct and the flags are wired through to runtime behaviour, but the
underlying models (DQN, LSTM) are still small, CPU-only, and not
trained to publication-grade convergence.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple


# ── Weather mode vocabulary ─────────────────────────────────────────────
WEATHER_NORMAL       = "normal"
WEATHER_HIGH_DEMAND  = "high_demand"
WEATHER_STORM        = "storm"

WEATHER_MODES: Tuple[str, ...] = (
    WEATHER_NORMAL, WEATHER_HIGH_DEMAND, WEATHER_STORM,
)


@dataclass
class ExperimentConfig:
    """Central experiment configuration.

    Every boolean flag below genuinely disables the named component at
    runtime. ``active_modules`` / ``disabled_modules`` are derived from
    the flags and exposed in JSON so the experiment consumer can verify
    the configuration matches the description.
    """

    # ── Module toggles ──────────────────────────────────────────────────
    enable_dqn: bool = True
    enable_lstm: bool = True
    enable_twin: bool = True
    enable_predictive_healing: bool = True
    enable_reward_shaping: bool = True
    enable_flisr: bool = True
    enable_ems: bool = True
    enable_storage: bool = True
    enable_xai: bool = True

    # ── Reproducibility knobs ───────────────────────────────────────────
    seed: int = 42

    # ── Scenario parameters ────────────────────────────────────────────
    weather_mode: str = WEATHER_NORMAL
    fault_count: int = 1
    simulation_steps: int = 100

    # ── Telemetry / observability ──────────────────────────────────────
    label: str = "default"
    notes: str = ""

    # ── Convenience ────────────────────────────────────────────────────
    def active_modules(self) -> List[str]:
        """Return the names of modules this configuration enables.

        This is the *definitive* answer to "is LSTM actually on in this
        run?". Downstream JSON serialisation should always include
        ``active_modules`` so the table cannot drift from the run.
        """
        active = []
        if self.enable_dqn:                active.append("dqn")
        if self.enable_lstm:               active.append("lstm")
        if self.enable_twin:               active.append("digital_twin")
        if self.enable_predictive_healing: active.append("predictive_healing")
        if self.enable_reward_shaping:     active.append("reward_shaping")
        if self.enable_flisr:              active.append("flisr")
        if self.enable_ems:                active.append("ems")
        if self.enable_storage:            active.append("storage")
        if self.enable_xai:                active.append("xai")
        return active

    def disabled_modules(self) -> List[str]:
        """Return the names of modules this configuration disables."""
        all_modules = (
            "dqn", "lstm", "digital_twin", "predictive_healing",
            "reward_shaping", "flisr", "ems", "storage", "xai",
        )
        flags = {
            "dqn":                 self.enable_dqn,
            "lstm":                self.enable_lstm,
            "digital_twin":        self.enable_twin,
            "predictive_healing":  self.enable_predictive_healing,
            "reward_shaping":      self.enable_reward_shaping,
            "flisr":               self.enable_flisr,
            "ems":                 self.enable_ems,
            "storage":             self.enable_storage,
            "xai":                 self.enable_xai,
        }
        return [m for m in all_modules if not flags[m]]

    def to_dict(self) -> Dict[str, object]:
        """Serialise to a JSON-friendly dict, including active/disabled."""
        out = asdict(self)
        out["active_modules"]   = self.active_modules()
        out["disabled_modules"] = self.disabled_modules()
        return out

    # ── Pre-baked configurations for ablation studies ──────────────────
    @classmethod
    def full_stack(cls, seed: int = 42) -> "ExperimentConfig":
        return cls(
            enable_dqn=True, enable_lstm=True, enable_twin=True,
            enable_predictive_healing=True, enable_reward_shaping=True,
            enable_flisr=True, enable_ems=True, enable_storage=True,
            enable_xai=True, seed=seed, label="full_stack",
        )

    @classmethod
    def no_lstm(cls, seed: int = 42) -> "ExperimentConfig":
        return cls(
            enable_dqn=True, enable_lstm=False, enable_twin=True,
            enable_predictive_healing=True, enable_reward_shaping=True,
            enable_flisr=True, enable_ems=True, enable_storage=True,
            enable_xai=True, seed=seed, label="no_lstm",
            notes="LSTM forecaster disabled; persistence fallback used.",
        )

    @classmethod
    def no_twin(cls, seed: int = 42) -> "ExperimentConfig":
        return cls(
            enable_dqn=True, enable_lstm=True, enable_twin=False,
            enable_predictive_healing=True, enable_reward_shaping=True,
            enable_flisr=True, enable_ems=True, enable_storage=True,
            enable_xai=True, seed=seed, label="no_twin",
            notes="Digital twin registry bypassed; no health-aware action selection.",
        )

    @classmethod
    def no_predictive(cls, seed: int = 42) -> "ExperimentConfig":
        return cls(
            enable_dqn=True, enable_lstm=True, enable_twin=True,
            enable_predictive_healing=False, enable_reward_shaping=True,
            enable_flisr=True, enable_ems=True, enable_storage=True,
            enable_xai=True, seed=seed, label="no_predictive",
            notes="Predictive self-healing disabled; faults handled reactively by FLISR only.",
        )

    @classmethod
    def no_reward(cls, seed: int = 42) -> "ExperimentConfig":
        return cls(
            enable_dqn=True, enable_lstm=True, enable_twin=True,
            enable_predictive_healing=True, enable_reward_shaping=False,
            enable_flisr=True, enable_ems=True, enable_storage=True,
            enable_xai=True, seed=seed, label="no_reward",
            notes="Reward shaping replaced with a single penalty on outage count.",
        )

    @classmethod
    def dqn_core_only(cls, seed: int = 42) -> "ExperimentConfig":
        return cls(
            enable_dqn=True, enable_lstm=False, enable_twin=False,
            enable_predictive_healing=False, enable_reward_shaping=False,
            enable_flisr=True, enable_ems=False, enable_storage=False,
            enable_xai=False, seed=seed, label="dqn_core_only",
            notes="DQN core only — no LSTM, no Twin, no Predictive, "
                  "no reward shaping, no EMS, no XAI.",
        )

    @classmethod
    def rule_based(cls, seed: int = 42) -> "ExperimentConfig":
        return cls(
            enable_dqn=False, enable_lstm=False, enable_twin=False,
            enable_predictive_healing=False, enable_reward_shaping=False,
            enable_flisr=True, enable_ems=False, enable_storage=False,
            enable_xai=False, seed=seed, label="rule_based",
            notes="Deterministic rule-based FLISR; no learned control.",
        )

    @classmethod
    def random_baseline(cls, seed: int = 42) -> "ExperimentConfig":
        return cls(
            enable_dqn=False, enable_lstm=False, enable_twin=False,
            enable_predictive_healing=False, enable_reward_shaping=False,
            enable_flisr=False, enable_ems=False, enable_storage=False,
            enable_xai=False, seed=seed, label="random",
            notes="Random policy baseline.",
        )

    @classmethod
    def persistence(cls, seed: int = 42) -> "ExperimentConfig":
        return cls(
            enable_dqn=False, enable_lstm=False, enable_twin=False,
            enable_predictive_healing=False, enable_reward_shaping=False,
            enable_flisr=False, enable_ems=False, enable_storage=False,
            enable_xai=False, seed=seed, label="persistence",
            notes="No-AI controller — no actions are ever issued.",
        )


# Pre-baked configurations used by the paper-experiment runner.
ABLATION_CONFIGS: Dict[str, "ExperimentConfig"] = {
    "full_stack":     ExperimentConfig.full_stack(),
    "no_lstm":        ExperimentConfig.no_lstm(),
    "no_twin":        ExperimentConfig.no_twin(),
    "no_predictive":  ExperimentConfig.no_predictive(),
    "no_reward":      ExperimentConfig.no_reward(),
    "dqn_core_only":  ExperimentConfig.dqn_core_only(),
    "rule_based":     ExperimentConfig.rule_based(),
    "random":         ExperimentConfig.random_baseline(),
    "persistence":    ExperimentConfig.persistence(),
}


def list_ablation_labels() -> List[str]:
    """Return the labels of all pre-baked ablation configurations."""
    return list(ABLATION_CONFIGS.keys())
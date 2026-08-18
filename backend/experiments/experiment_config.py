"""experiment_config.py — Pre-baked controller configurations.

The ablation study (Stage 19) requires a *table* of pre-baked
``ExperimentConfig`` records, one per row of the table. Each row
turns on / off a single capability so the ablation cleanly attributes
the marginal benefit to that capability.

``ABLATION_CONFIGS`` is the canonical mapping; constructors like
``ExperimentConfig.full_stack(...)`` and ``ExperimentConfig.no_lstm(...)``
return identical records to the matching dict entry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List


@dataclass
class ExperimentConfig:
    """One row in the ablation table.

    Every boolean toggles a single named capability. ``active_modules``
    and ``disabled_modules`` are *derived* from these flags — they
    are computed (not stored) so a config cannot lie about which modules
    are active.
    """
    # Toggles
    enable_dqn: bool = True
    enable_lstm: bool = True
    enable_twin: bool = True
    enable_predictive_healing: bool = True
    enable_reward_shaping: bool = True
    enable_flisr: bool = True
    enable_ems: bool = True
    enable_storage: bool = True
    enable_xai: bool = True

    # Bookkeeping
    seed: int = 0
    label: str = "config"

    # Stage-43 (Repair 4): path to a frozen DQN policy checkpoint
    # produced by ``dqn_training.py``. When set AND the file exists, the
    # runner evaluates that policy; without it the DQN runs on freshly
    # seeded random weights — that is the ``untrained_dqn`` baseline.
    # The runner NEVER trains; training happens only in ``dqn_training.py``.
    checkpoint_path: str = ""

    # ------------------------------------------------------------------
    # Module alias mapping — keep these in sync with the test contract.
    # ------------------------------------------------------------------
    @property
    def module_flags(self) -> Dict[str, bool]:
        return {
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

    def active_modules(self) -> List[str]:
        return sorted(name for name, on in self.module_flags.items() if on)

    def disabled_modules(self) -> List[str]:
        return sorted(name for name, on in self.module_flags.items() if not on)

    # ------------------------------------------------------------------
    # Pre-baked configurations
    # ------------------------------------------------------------------

    @classmethod
    def full_stack(cls, seed: int = 0) -> "ExperimentConfig":
        return cls(seed=seed, label="full_stack")

    @classmethod
    def no_lstm(cls, seed: int = 0) -> "ExperimentConfig":
        return cls(enable_lstm=False, seed=seed, label="no_lstm")

    @classmethod
    def no_twin(cls, seed: int = 0) -> "ExperimentConfig":
        return cls(enable_twin=False, seed=seed, label="no_twin")

    @classmethod
    def no_predictive(cls, seed: int = 0) -> "ExperimentConfig":
        return cls(enable_predictive_healing=False,
                   seed=seed, label="no_predictive")

    @classmethod
    def no_reward(cls, seed: int = 0) -> "ExperimentConfig":
        return cls(enable_reward_shaping=False,
                   seed=seed, label="no_reward")

    @classmethod
    def dqn_core_only(cls, seed: int = 0) -> "ExperimentConfig":
        return cls(
            enable_lstm=False,
            enable_twin=False,
            enable_predictive_healing=False,
            enable_reward_shaping=False,
            enable_ems=False,
            enable_storage=False,
            enable_xai=False,
            seed=seed,
            label="dqn_core_only",
        )

    @classmethod
    def rule_based(cls, seed: int = 0) -> "ExperimentConfig":
        return cls(
            enable_dqn=False,
            enable_lstm=False,
            enable_reward_shaping=False,
            enable_xai=False,
            seed=seed,
            label="rule_based",
        )

    @classmethod
    def random(cls, seed: int = 0) -> "ExperimentConfig":
        """Disable everything that requires deterministic behaviour.

        We keep FLISR and EMS on so the random baseline still respects
        physical constraints (it just picks actions uniformly).
        """
        return cls(
            enable_dqn=False,
            enable_lstm=False,
            enable_twin=False,
            enable_predictive_healing=False,
            enable_reward_shaping=False,
            enable_xai=False,
            seed=seed,
            label="random",
        )

    @classmethod
    def persistence(cls, seed: int = 0) -> "ExperimentConfig":
        """The 'no-action' baseline: do nothing, just let faults run.

        All healing capabilities are off.
        """
        return cls(
            enable_dqn=False,
            enable_lstm=False,
            enable_twin=False,
            enable_predictive_healing=False,
            enable_reward_shaping=False,
            enable_ems=False,
            enable_storage=False,
            enable_xai=False,
            enable_flisr=False,
            seed=seed,
            label="persistence",
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        d = asdict(self)
        d["active_modules"] = self.active_modules()
        d["disabled_modules"] = self.disabled_modules()
        return d


# ----------------------------------------------------------------------
# Canonical ablation table (Stage 19).
# ----------------------------------------------------------------------

ABLATION_CONFIGS: Dict[str, ExperimentConfig] = {
    "full_stack":  ExperimentConfig.full_stack(),
    "no_lstm":     ExperimentConfig.no_lstm(),
    "no_twin":     ExperimentConfig.no_twin(),
    "no_predictive": ExperimentConfig.no_predictive(),
    "no_reward":   ExperimentConfig.no_reward(),
    "dqn_core_only": ExperimentConfig.dqn_core_only(),
    "rule_based":  ExperimentConfig.rule_based(),
    "random":      ExperimentConfig.random(),
    "persistence": ExperimentConfig.persistence(),
}


def get_config(label: str) -> ExperimentConfig:
    """Return a fresh ``ExperimentConfig`` for ``label``.

    Falls back to ``full_stack`` if the label is unknown — but the
    caller will get a copy of the full-stack config, which is the
    expected debug default.
    """
    if label in ABLATION_CONFIGS:
        # Return a copy with a fresh label-override
        cfg = ABLATION_CONFIGS[label]
        return ExperimentConfig(
            enable_dqn=cfg.enable_dqn,
            enable_lstm=cfg.enable_lstm,
            enable_twin=cfg.enable_twin,
            enable_predictive_healing=cfg.enable_predictive_healing,
            enable_reward_shaping=cfg.enable_reward_shaping,
            enable_flisr=cfg.enable_flisr,
            enable_ems=cfg.enable_ems,
            enable_storage=cfg.enable_storage,
            enable_xai=cfg.enable_xai,
            label=label,
        )
    return ExperimentConfig(label=label)


def list_ablation_labels() -> List[str]:
    """Return the canonical list of ablation labels (sorted).

    Backward-compat shim used by the legacy ``experiments/runner.py``
    in the repository root.
    """
    return sorted(ABLATION_CONFIGS.keys())

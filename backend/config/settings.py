"""
settings.py — pydantic-settings based configuration.

Why
---
A research-grade project must be reproducible.  Hard-coded
constants scatter across modules; environment variables let
reviewers re-run a benchmark with the same RNG, log level, and
scenario file without editing code.

Design notes:
  - Uses pydantic-settings if available; otherwise falls back to
    a plain dataclass so the package can be installed without
    pydantic-settings (a stated requirement in M0).
  - Singleton accessor ``get_settings`` is process-global — fine
    for a single-process API server.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    """Process-wide configuration."""

    ehm_log_level: str = "INFO"
    ehm_city_profile: str = "default"
    ehm_city_seed: int = 42
    ehm_weather_seed: int = 42
    ehm_advanced_rl: bool = True
    ehm_xai: bool = True
    ehm_industry_metrics: bool = True
    ehm_run_id: str = "default"
    ehm_extra_scenarios: List[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "Settings":
        """Build a Settings from environment variables, with defaults."""
        return cls(
            ehm_log_level=os.environ.get("EHM_LOG_LEVEL", "INFO"),
            ehm_city_profile=os.environ.get("EHM_CITY_PROFILE", "default"),
            ehm_city_seed=int(os.environ.get("EHM_CITY_SEED", "42")),
            ehm_weather_seed=int(os.environ.get("EHM_WEATHER_SEED", "42")),
            ehm_advanced_rl=os.environ.get("EHM_ADVANCED_RL", "true").lower()
                           in {"1", "true", "yes", "on"},
            ehm_xai=os.environ.get("EHM_XAI", "true").lower()
                    in {"1", "true", "yes", "on"},
            ehm_industry_metrics=os.environ.get("EHM_INDUSTRY_METRICS", "true").lower()
                                  in {"1", "true", "yes", "on"},
            ehm_run_id=os.environ.get("EHM_RUN_ID", "default"),
            ehm_extra_scenarios=[
                s for s in os.environ.get("EHM_EXTRA_SCENARIOS", "").split(",")
                if s
            ],
        )

    def describe(self) -> dict:
        return {
            "log_level": self.ehm_log_level,
            "city_profile": self.ehm_city_profile,
            "city_seed": self.ehm_city_seed,
            "weather_seed": self.ehm_weather_seed,
            "advanced_rl": self.ehm_advanced_rl,
            "xai": self.ehm_xai,
            "industry_metrics": self.ehm_industry_metrics,
            "run_id": self.ehm_run_id,
            "extra_scenarios": self.ehm_extra_scenarios,
        }


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings
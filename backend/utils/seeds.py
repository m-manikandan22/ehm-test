"""
seeds.py — single source of RNG for reproducibility.

Why does this exist?
--------------------
A research-grade digital-twin paper must be *reproducible* — given the
same seed, the same scenario must produce the same fault pattern, the
same load curve, the same RL trajectory, and the same IEEE 1366 metric.
The original codebase called `random.seed(...)` and `np.random.seed(...)`
inline, which is fragile and easy to forget.

This module exposes a `make_rng(seed=None)` factory that returns a
`numpy.random.Generator`.  The Generator is the modern NumPy API
(`np.random.default_rng`) and is thread-safe at the per-step level.

It also exposes `ehm_global_seed()` which returns the seed currently
in effect (read from `EHM_SEED` env var if set, else 42), so tests can
pin the seed without re-wiring every entry point.

It also exposes `set_global_seed(seed=None)` which seeds the *global*
PRNG state of `random`, `numpy.random`, and (when present) `torch`.
That is the entry point every experiment runner should call before
running any number of steps.
"""
from __future__ import annotations

import os
import random
from typing import Optional

import numpy as np


_DEFAULT_SEED = 42
_ENV_SEED = "EHM_SEED"


def ehm_global_seed() -> int:
    """Return the process-wide RNG seed.

    Order of precedence:
      1. The `EHM_SEED` env var, if set to a valid integer.
      2. Otherwise the default (42).
    """
    raw = os.environ.get(_ENV_SEED)
    if raw is None:
        return _DEFAULT_SEED
    try:
        return int(raw)
    except ValueError:
        return _DEFAULT_SEED


def make_rng(seed: Optional[int] = None) -> np.random.Generator:
    """Return a numpy random Generator.

    Parameters
    ----------
    seed : int, optional
        Explicit seed.  If omitted, the value of `EHM_SEED` is used
        (or the default 42).
    """
    if seed is None:
        seed = ehm_global_seed()
    return np.random.default_rng(seed)


def make_random_state(seed: Optional[int] = None):
    """Return a `random.Random` (stdlib) instance, for code that uses
    the older Python API."""
    if seed is None:
        seed = ehm_global_seed()
    return random.Random(seed)


def derive_stream_seeds(master_seed: Optional[int] = None) -> dict:
    """Split a master seed into independent per-stream seeds.

    Stage-43 RNG isolation: a single master seed must not make the
    environment (grid physics), the controller (random/heuristic
    policies) and the training (torch / DQN / LSTM) share one PRNG
    stream — otherwise a controller's inference draws perturb grid
    noise and paired comparisons are unfair.

    Streams returned (all ``int``):
      - ``master``      : the input seed (as recorded in results)
      - ``environment`` : grid construction + physics noise
      - ``controller``  : random / heuristic controller draws
      - ``training``    : torch RNG for LSTM / DQN construction + training

    The derivation is a deterministic integer transform: the same master
    seed always yields the same three stream seeds, and the streams are
    mutually independent (different seeds ⇒ different sequences).
    """
    if master_seed is None:
        master_seed = ehm_global_seed()
    master_seed = int(master_seed)
    return {
        "master": master_seed,
        "environment": (master_seed * 7919 + 17) % (2 ** 31),
        "controller": (master_seed * 104729 + 31) % (2 ** 31),
        "training": (master_seed * 15485863 + 47) % (2 ** 31),
    }


def set_global_seed(seed: Optional[int] = None) -> int:
    """Seed every global PRNG in this process.

    Covers:
      - Python stdlib ``random``
      - NumPy (``numpy.random.seed`` and a default ``Generator``)
      - PyTorch (``torch.manual_seed``, ``torch.cuda.manual_seed_all``,
        cuDNN deterministic flags) when torch is importable.

    Returns the seed actually applied (always an ``int``).
    """
    if seed is None:
        seed = ehm_global_seed()
    seed = int(seed)

    # Python stdlib
    random.seed(seed)
    # NumPy legacy + Generator default
    try:
        np.random.seed(seed)
    except Exception:  # noqa: BLE001 - last-ditch; numpy should never fail
        pass
    try:
        np.random.default_rng(seed)
    except Exception:  # noqa: BLE001
        pass

    # PyTorch — optional, never required for the simulation to start.
    try:
        import torch  # type: ignore
        torch.manual_seed(seed)
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            try:
                torch.cuda.manual_seed_all(seed)
            except Exception:  # noqa: BLE001
                pass
        try:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
        except Exception:  # noqa: BLE001
            pass
    except ImportError:
        pass

    # Make the resolved seed visible to anyone reading env later.
    os.environ[_ENV_SEED] = str(seed)
    return seed

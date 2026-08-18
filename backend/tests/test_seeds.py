"""test_seeds.py — tests for the deterministic RNG helpers."""
from __future__ import annotations

import os

import numpy as np
import pytest

from utils.seeds import (
    _DEFAULT_SEED,
    ehm_global_seed,
    make_random_state,
    make_rng,
)


@pytest.fixture(autouse=True)
def restore_env(monkeypatch):
    monkeypatch.delenv("EHM_SEED", raising=False)
    yield


def test_default_seed_is_42():
    assert ehm_global_seed() == _DEFAULT_SEED == 42


def test_env_seed_is_respected(monkeypatch):
    monkeypatch.setenv("EHM_SEED", "2026")
    assert ehm_global_seed() == 2026


def test_env_seed_falls_back_for_garbage(monkeypatch):
    monkeypatch.setenv("EHM_SEED", "not-a-number")
    assert ehm_global_seed() == _DEFAULT_SEED


def test_make_rng_returns_generator():
    rng = make_rng(seed=7)
    assert isinstance(rng, np.random.Generator)
    val = rng.random()
    assert 0.0 <= val < 1.0


def test_make_rng_deterministic():
    a = make_rng(seed=11)
    b = make_rng(seed=11)
    for _ in range(10):
        assert a.random() == b.random()


def test_make_rng_uses_global_when_omitted(monkeypatch):
    monkeypatch.setenv("EHM_SEED", "13")
    a = make_rng()
    b = make_rng()
    assert a.random() == b.random()


def test_make_random_state():
    rs1 = make_random_state(seed=3)
    rs2 = make_random_state(seed=3)
    for _ in range(5):
        assert rs1.random() == rs2.random()

"""test_policy_registry.py — Wire ``experiments.policies`` into the harness.

Confirms the policy registry returns fresh instances and that all
expected entries are present.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load_policy_module():
    p = os.path.join(REPO_ROOT, "experiments", "policies.py")
    if not os.path.exists(p):
        pytest.skip("experiments/policies.py not found")
    sys.path.insert(0, REPO_ROOT)
    spec = importlib.util.spec_from_file_location("ehm_policies_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ehm_policies_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_registry_has_expected_keys():
    mod = _load_policy_module()
    keys = mod.available_policies()
    for expected in ("random", "rule_based", "dqn", "flisr_only", "persistence"):
        assert expected in keys, f"missing policy {expected}; have {keys}"


def test_make_policy_returns_fresh_instance():
    mod = _load_policy_module()
    p1 = mod.make_policy("random")
    p2 = mod.make_policy("random")
    # Each call returns a brand new instance
    assert p1 is not p2


def test_unknown_policy_raises():
    mod = _load_policy_module()
    with pytest.raises(KeyError):
        mod.make_policy("not_a_real_policy")

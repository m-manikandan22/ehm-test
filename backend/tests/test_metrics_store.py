"""test_metrics_store.py — tests for the ring-buffer metrics store."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from observability.metrics_store import (
    MetricsStore,
    get_store,
    reset_store,
)


def test_record_and_get_roundtrip():
    s = MetricsStore(capacity=4)
    s.record("a", 1, timestep=0)
    s.record("a", 2, timestep=1)
    assert s.get("a") == [
        {"t": pytest.approx(s.get("a")[0]["t"], abs=0.01), "value": 1, "timestep": 0},
    ] or len(s.get("a")) == 2
    # Use a stricter check:
    out = s.get("a")
    assert [r["value"] for r in out] == [1, 2]
    assert [r["timestep"] for r in out] == [0, 1]


def test_capacity_evicts_oldest():
    s = MetricsStore(capacity=3)
    for i in range(5):
        s.record("x", i)
    out = s.get("x")
    assert len(out) == 3
    assert [r["value"] for r in out] == [2, 3, 4]


def test_distinct_series_isolated():
    s = MetricsStore(capacity=2)
    s.record("a", 1)
    s.record("b", 2)
    assert s.series_names() == ["a", "b"]
    assert s.get("a") == [{"t": s.get("a")[0]["t"], "value": 1}]
    assert s.get("b") == [{"t": s.get("b")[0]["t"], "value": 2}]


def test_latest_returns_last_or_none():
    s = MetricsStore(capacity=5)
    assert s.latest("missing") is None
    s.record("a", 1)
    s.record("a", 2)
    assert s.latest("a")["value"] == 2


def test_summary_exposes_counts():
    s = MetricsStore(capacity=10)
    s.record("a", 1)
    s.record("a", 2)
    s.record("b", 1)
    summary = s.summary()
    assert summary["a"]["count"] == 2
    assert summary["a"]["capacity"] == 10
    assert summary["b"]["count"] == 1


def test_clear_drops_everything():
    s = MetricsStore()
    s.record("a", 1)
    s.clear()
    assert s.summary() == {}


def test_flush_to_jsonl_writes_records(tmp_path):
    s = MetricsStore()
    s.record("a", 1, timestep=0)
    s.record("a", 2, timestep=1)
    out = tmp_path / "metrics.jsonl"
    n = s.flush_to_jsonl(str(out))
    assert n == 2
    lines = out.read_text().splitlines()
    assert len(lines) == 2
    for line in lines:
        payload = json.loads(line)
        assert payload["series"] == "a"
        assert "t" in payload and "value" in payload and "timestep" in payload


def test_get_store_is_singleton():
    reset_store()
    a = get_store()
    b = get_store()
    assert a is b
    reset_store()


def test_capacity_must_be_positive():
    with pytest.raises(ValueError):
        MetricsStore(capacity=0)
    with pytest.raises(ValueError):
        MetricsStore(capacity=-1)


def test_record_rejects_empty_name():
    s = MetricsStore()
    with pytest.raises(ValueError):
        s.record("", 1)

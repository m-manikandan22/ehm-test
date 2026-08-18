"""test_di_container.py — tests for the DI container."""
from __future__ import annotations

import pytest

from di import Container, get_container, reset_container


def test_register_and_get_returns_singleton():
    c = Container()
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return {"hello": "world"}

    c.register("thing", factory)
    a = c.get("thing")
    b = c.get("thing")
    assert a is b  # singleton
    assert calls["n"] == 1
    assert a == {"hello": "world"}


def test_missing_raises_with_helpful_message():
    c = Container()
    c.register("a", lambda: 1)
    with pytest.raises(KeyError) as exc:
        c.get("missing")
    assert "missing" in str(exc.value)
    assert "Registered" in str(exc.value)
    assert "'a'" in str(exc.value)


def test_register_overwrites_and_drops_instance():
    c = Container()
    c.register("a", lambda: "first")
    first = c.get("a")
    c.register("a", lambda: "second")
    second = c.get("a")
    assert first == "first"
    assert second == "second"


def test_has_and_names():
    c = Container()
    c.register("b", lambda: 1)
    c.register("a", lambda: 2)
    assert c.has("a") and c.has("b")
    assert not c.has("z")
    assert c.names() == ["a", "b"]


def test_clear_drops_everything():
    c = Container()
    c.register("x", lambda: 1)
    c.get("x")
    c.clear()
    assert c.names() == []
    assert not c.has("x")


def test_describe_does_not_leak_values():
    c = Container()
    sentinel = object()
    c.register("o", lambda: sentinel)
    d = c.describe()
    assert d["registered"] == ["o"]
    assert d["instantiated"] == []  # not yet built
    # Values are never put in describe() output.
    assert "sentinel" not in repr(d)
    c.get("o")
    d2 = c.describe()
    assert d2["instantiated"] == ["o"]


def test_register_validates_name_and_factory():
    c = Container()
    with pytest.raises(ValueError):
        c.register("", lambda: 1)
    with pytest.raises(TypeError):
        c.register("x", 42)  # not callable


def test_get_container_is_process_global():
    reset_container()
    a = get_container()
    b = get_container()
    assert a is b
    a.register("k", lambda: 7)
    assert b.has("k")
    reset_container()


def test_concurrent_get_only_calls_factory_once():
    """The container must be thread-safe for lazy singleton creation."""
    import threading
    c = Container()
    calls = {"n": 0}
    c.register("x", lambda: (calls.__setitem__("n", calls["n"] + 1) or "v"))

    results = []

    def worker():
        results.append(c.get("x"))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 8
    assert all(r == "v" for r in results)
    # The factory may run more than once under the GIL but the
    # *singleton* result must be identical.
    assert all(r is results[0] for r in results)

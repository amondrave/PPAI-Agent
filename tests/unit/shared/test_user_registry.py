"""Unit tests for UserRegistry."""

from __future__ import annotations

import threading

from ppai.shared.infrastructure.user_registry import UserRegistry


class TestUserRegistry:
    def test_register_and_get_all(self):
        registry = UserRegistry()
        registry.register("111")
        registry.register("222")
        assert sorted(registry.get_all()) == ["111", "222"]

    def test_register_is_idempotent(self):
        registry = UserRegistry()
        registry.register("111")
        registry.register("111")
        assert len(registry) == 1

    def test_get_all_returns_snapshot(self):
        registry = UserRegistry()
        registry.register("111")
        snapshot = registry.get_all()
        registry.register("222")
        assert len(snapshot) == 1  # original snapshot unchanged

    def test_contains(self):
        registry = UserRegistry()
        registry.register("111")
        assert "111" in registry
        assert "999" not in registry

    def test_empty_registry(self):
        registry = UserRegistry()
        assert registry.get_all() == []
        assert len(registry) == 0

    def test_thread_safety(self):
        registry = UserRegistry()
        errors = []

        def register_batch(start: int) -> None:
            try:
                for i in range(start, start + 100):
                    registry.register(str(i))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_batch, args=(i * 100,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(registry) == 500

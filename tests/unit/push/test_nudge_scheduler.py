"""Unit tests for NudgeScheduler."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, call

import pytest

from ppai.push.application.nudge_scheduler import NudgeScheduler
from ppai.push.domain.value_objects import DispatchOutcome, NudgeDispatchStatus


def make_scheduler(service=None, user_ids=None, interval=1):
    if service is None:
        service = MagicMock()
        service.run_tick.return_value = []
    if user_ids is None:
        user_ids = ["u1", "u2"]
    return NudgeScheduler(
        nudge_service=service,
        user_ids_provider=lambda: user_ids,
        tick_interval_minutes=interval,
    )


class TestNudgeScheduler:
    def test_tick_calls_run_tick_with_user_ids(self):
        service = MagicMock()
        service.run_tick.return_value = []
        svc = make_scheduler(service=service)
        svc._tick()
        service.run_tick.assert_called_once()
        args, kwargs = service.run_tick.call_args
        assert args[0] == ["u1", "u2"]

    def test_tick_with_empty_user_ids_does_not_call_service(self):
        service = MagicMock()
        svc = NudgeScheduler(
            nudge_service=service,
            user_ids_provider=lambda: [],
            tick_interval_minutes=1,
        )
        svc._tick()
        service.run_tick.assert_not_called()

    def test_exception_in_run_tick_does_not_propagate(self):
        service = MagicMock()
        service.run_tick.side_effect = RuntimeError("db error")
        svc = make_scheduler(service=service)
        # Should not raise
        svc._tick()

    def test_exception_in_user_ids_provider_does_not_propagate(self):
        def broken_provider():
            raise RuntimeError("cannot list users")
        svc = NudgeScheduler(
            nudge_service=MagicMock(),
            user_ids_provider=broken_provider,
            tick_interval_minutes=1,
        )
        svc._tick()  # Should not raise

    def test_start_and_stop(self):
        svc = make_scheduler()
        svc.start()
        assert svc._thread is not None
        assert svc._thread.is_alive()
        svc.stop()
        assert not svc._thread.is_alive()

    def test_start_is_idempotent(self):
        svc = make_scheduler()
        svc.start()
        thread_id = svc._thread.ident
        svc.start()  # Second call should not spawn new thread
        assert svc._thread.ident == thread_id
        svc.stop()

    def test_stop_without_start_does_not_raise(self):
        svc = make_scheduler()
        svc.stop()  # Should not raise

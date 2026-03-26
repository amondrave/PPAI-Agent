"""Unit tests for NudgeScheduler UOW-05 — dynamic interval (DP-SCHED-01)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ppai.push.application.nudge_scheduler import NudgeScheduler


def _make_scheduler(interval_provider=None, base_interval=15):
    service = MagicMock()
    service.run_tick.return_value = []
    return NudgeScheduler(
        nudge_service=service,
        user_ids_provider=lambda: ["u1"],
        tick_interval_minutes=base_interval,
        interval_provider=interval_provider,
    )


class TestDynamicInterval:
    def test_interval_changes_with_zen_active(self):
        """When interval_provider returns shorter interval, scheduler uses it."""
        sched = _make_scheduler(interval_provider=lambda: 5)
        sched._recalculate_interval()
        assert sched._interval_seconds == 5 * 60

    def test_restores_base_interval_without_zen(self):
        """When interval_provider returns None, scheduler reverts to base interval."""
        sched = _make_scheduler(interval_provider=lambda: None, base_interval=15)
        sched._recalculate_interval()
        assert sched._interval_seconds == 15 * 60

    def test_floor_of_5_minutes(self):
        """Interval never goes below 5 minutes (DP-SCHED-01)."""
        sched = _make_scheduler(interval_provider=lambda: 2)
        sched._recalculate_interval()
        assert sched._interval_seconds == 5 * 60

    def test_backward_compatible_without_provider(self):
        """Without interval_provider, scheduler keeps static interval."""
        sched = _make_scheduler(interval_provider=None, base_interval=15)
        assert sched._interval_seconds == 15 * 60
        sched._recalculate_interval()
        assert sched._interval_seconds == 15 * 60

    def test_provider_error_keeps_current_interval(self):
        """If interval_provider raises, current interval is preserved."""
        def broken():
            raise RuntimeError("zen error")
        sched = _make_scheduler(interval_provider=broken, base_interval=15)
        sched._recalculate_interval()
        assert sched._interval_seconds == 15 * 60

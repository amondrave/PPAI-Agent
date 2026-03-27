"""Unit tests for UOW-05 domain extensions: UserNudgePreferences windows + value objects."""

from datetime import datetime, timezone

import pytest

from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import (
    DailySummary,
    RescueSuggestion,
    TaskSummaryItem,
    ZenSession,
)


# --- UserNudgePreferences defaults ---


class TestUserNudgePreferencesDefaults:
    def test_default_daily_start_time(self):
        prefs = UserNudgePreferences(user_id="u1")
        assert prefs.daily_start_time == "08:00"

    def test_default_daily_end_time(self):
        prefs = UserNudgePreferences(user_id="u1")
        assert prefs.daily_end_time == "18:00"

    def test_default_zen_inactive(self):
        prefs = UserNudgePreferences(user_id="u1")
        assert prefs.zen_active is False

    def test_default_zen_interval(self):
        prefs = UserNudgePreferences(user_id="u1")
        assert prefs.zen_interval_minutes == 15

    def test_default_zen_max_nudges(self):
        prefs = UserNudgePreferences(user_id="u1")
        assert prefs.zen_max_nudges == 10

    def test_default_motivational_message(self):
        prefs = UserNudgePreferences(user_id="u1")
        assert prefs.motivational_message == "A darle con todo hoy"


# --- is_within_start_window ---


class TestIsWithinStartWindow:
    def test_exact_match(self):
        prefs = UserNudgePreferences(user_id="u1", daily_start_time="08:00")
        local_now = datetime(2026, 3, 27, 8, 0)
        assert prefs.is_within_start_window(local_now) is True

    def test_within_tolerance(self):
        prefs = UserNudgePreferences(user_id="u1", daily_start_time="08:00")
        local_now = datetime(2026, 3, 27, 8, 5)
        assert prefs.is_within_start_window(local_now) is True

    def test_at_tolerance_boundary(self):
        prefs = UserNudgePreferences(user_id="u1", daily_start_time="08:00")
        local_now = datetime(2026, 3, 27, 8, 7)
        assert prefs.is_within_start_window(local_now) is True

    def test_outside_tolerance(self):
        prefs = UserNudgePreferences(user_id="u1", daily_start_time="08:00")
        local_now = datetime(2026, 3, 27, 8, 8)
        assert prefs.is_within_start_window(local_now) is False

    def test_before_tolerance(self):
        prefs = UserNudgePreferences(user_id="u1", daily_start_time="08:00")
        local_now = datetime(2026, 3, 27, 7, 53)
        assert prefs.is_within_start_window(local_now) is True

    def test_well_outside(self):
        prefs = UserNudgePreferences(user_id="u1", daily_start_time="08:00")
        local_now = datetime(2026, 3, 27, 10, 0)
        assert prefs.is_within_start_window(local_now) is False


# --- is_within_end_window ---


class TestIsWithinEndWindow:
    def test_exact_match(self):
        prefs = UserNudgePreferences(user_id="u1", daily_end_time="18:00")
        local_now = datetime(2026, 3, 27, 18, 0)
        assert prefs.is_within_end_window(local_now) is True

    def test_outside_tolerance(self):
        prefs = UserNudgePreferences(user_id="u1", daily_end_time="18:00")
        local_now = datetime(2026, 3, 27, 18, 10)
        assert prefs.is_within_end_window(local_now) is False


# --- Cross-midnight tolerance ---


class TestCrossMidnightTolerance:
    def test_target_2355_now_0002(self):
        """Target 23:55, now 00:02 → delta 7 min → within tolerance."""
        prefs = UserNudgePreferences(user_id="u1", daily_start_time="23:55")
        local_now = datetime(2026, 3, 28, 0, 2)
        assert prefs.is_within_start_window(local_now) is True

    def test_target_0005_now_2358(self):
        """Target 00:05, now 23:58 → delta 7 min → within tolerance."""
        prefs = UserNudgePreferences(user_id="u1", daily_end_time="00:05")
        local_now = datetime(2026, 3, 27, 23, 58)
        assert prefs.is_within_end_window(local_now) is True


# --- should_zen_override_silence ---


class TestZenOverrideSilence:
    def test_zen_active_overrides(self):
        prefs = UserNudgePreferences(user_id="u1", zen_active=True)
        assert prefs.should_zen_override_silence() is True

    def test_zen_inactive_no_override(self):
        prefs = UserNudgePreferences(user_id="u1", zen_active=False)
        assert prefs.should_zen_override_silence() is False


# --- ZenSession ---


class TestZenSession:
    def test_has_reached_cap_false(self):
        session = ZenSession(
            user_id="u1",
            started_at=datetime.now(timezone.utc),
            nudges_sent=5,
            max_nudges=10,
        )
        assert session.has_reached_cap is False

    def test_has_reached_cap_true(self):
        session = ZenSession(
            user_id="u1",
            started_at=datetime.now(timezone.utc),
            nudges_sent=10,
            max_nudges=10,
        )
        assert session.has_reached_cap is True


# --- Value object construction ---


class TestValueObjects:
    def test_task_summary_item(self):
        item = TaskSummaryItem(task_id="t1", title="Do thing", status="completed")
        assert item.task_id == "t1"
        assert item.status == "completed"

    def test_rescue_suggestion(self):
        task = TaskSummaryItem(task_id="t1", title="Do thing", status="pending")
        rescue = RescueSuggestion(
            key_task=task,
            micro_action="Dedícale solo 5 minutos a: Do thing",
        )
        assert rescue.tone == "empathetic"

    def test_daily_summary_defaults(self):
        summary = DailySummary(user_id="u1", date="2026-03-27")
        assert summary.completed_tasks == []
        assert summary.rescue_triggered is False
        assert summary.rescue_suggestion is None

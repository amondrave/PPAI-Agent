from datetime import datetime, timezone

import pytest

from ppai.push.domain.entities import NudgeMessage, UserNudgePreferences
from ppai.push.domain.exceptions import (
    DailyCapReachedError,
    NoTop3AvailableError,
    NudgeDispatchFailedError,
    PushError,
    SilenceWindowActiveError,
)
from ppai.push.domain.value_objects import DispatchOutcome, NudgeDispatchStatus, WindowEvaluation


# ---------------------------------------------------------------------------
# NudgeDispatchStatus
# ---------------------------------------------------------------------------

class TestNudgeDispatchStatus:
    def test_all_values_defined(self):
        values = {s.value for s in NudgeDispatchStatus}
        assert values == {"scheduled", "sent", "skipped_activity", "skipped_no_top3", "failed"}

    def test_is_str(self):
        assert NudgeDispatchStatus.sent == "sent"
        assert isinstance(NudgeDispatchStatus.failed, str)


# ---------------------------------------------------------------------------
# UserNudgePreferences
# ---------------------------------------------------------------------------

class TestUserNudgePreferences:
    def test_defaults(self):
        prefs = UserNudgePreferences(user_id="u1")
        assert prefs.timezone == "America/Bogota"
        assert prefs.max_nudges_per_day == 3
        assert prefs.silence_start is None
        assert prefs.silence_end is None
        assert prefs.updated_at is None

    def test_custom_values(self):
        prefs = UserNudgePreferences(
            user_id="u1",
            timezone="America/New_York",
            max_nudges_per_day=5,
            silence_start="22:00",
            silence_end="08:00",
        )
        assert prefs.timezone == "America/New_York"
        assert prefs.max_nudges_per_day == 5

    def test_has_silence_window_false_when_unset(self):
        prefs = UserNudgePreferences(user_id="u1")
        assert prefs.has_silence_window() is False

    def test_has_silence_window_true_when_both_set(self):
        prefs = UserNudgePreferences(user_id="u1", silence_start="22:00", silence_end="08:00")
        assert prefs.has_silence_window() is True

    def test_has_silence_window_false_when_only_start(self):
        prefs = UserNudgePreferences(user_id="u1", silence_start="22:00")
        assert prefs.has_silence_window() is False


# ---------------------------------------------------------------------------
# WindowEvaluation
# ---------------------------------------------------------------------------

class TestWindowEvaluation:
    def _make_window(self, is_silence=False, recent_activity=False):
        now = datetime(2026, 3, 25, 9, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 25, 9, 15, tzinfo=timezone.utc)
        return WindowEvaluation(
            window_start=now,
            window_end=end,
            is_silence_window=is_silence,
            recent_activity=recent_activity,
        )

    def test_can_dispatch_when_no_blockers(self):
        w = self._make_window()
        assert w.can_dispatch is True

    def test_cannot_dispatch_during_silence(self):
        w = self._make_window(is_silence=True)
        assert w.can_dispatch is False

    def test_cannot_dispatch_with_recent_activity(self):
        w = self._make_window(recent_activity=True)
        assert w.can_dispatch is False

    def test_cannot_dispatch_when_both_blockers(self):
        w = self._make_window(is_silence=True, recent_activity=True)
        assert w.can_dispatch is False

    def test_is_frozen(self):
        w = self._make_window()
        with pytest.raises(Exception):
            w.is_silence_window = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DispatchOutcome
# ---------------------------------------------------------------------------

class TestDispatchOutcome:
    def test_sent_outcome(self):
        now = datetime(2026, 3, 25, 9, 0, tzinfo=timezone.utc)
        outcome = DispatchOutcome(
            status=NudgeDispatchStatus.sent,
            user_id="u1",
            task_id="t1",
            cycle_id="c1",
            sent_at=now,
        )
        assert outcome.status == NudgeDispatchStatus.sent
        assert outcome.task_id == "t1"
        assert outcome.reason is None

    def test_skipped_outcome_with_reason(self):
        outcome = DispatchOutcome(
            status=NudgeDispatchStatus.skipped_activity,
            user_id="u1",
            reason="activity 10 min ago",
        )
        assert outcome.task_id is None
        assert outcome.reason == "activity 10 min ago"

    def test_is_frozen(self):
        outcome = DispatchOutcome(status=NudgeDispatchStatus.failed, user_id="u1")
        with pytest.raises(Exception):
            outcome.user_id = "u2"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# NudgeMessage
# ---------------------------------------------------------------------------

class TestNudgeMessage:
    def test_construction(self):
        msg = NudgeMessage(
            task_id="t1",
            task_title="Enviar propuesta al cliente",
            priority_reason="Va primero porque vence hoy",
        )
        assert msg.task_id == "t1"
        assert msg.tone_profile == "soft_motivational"
        assert "done" in msg.buttons
        assert "snooze" in msg.buttons
        assert "clarify" in msg.buttons

    def test_is_frozen(self):
        msg = NudgeMessage(task_id="t1", task_title="T", priority_reason="R")
        with pytest.raises(Exception):
            msg.task_title = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Exceptions hierarchy
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_all_inherit_from_push_error(self):
        assert issubclass(NoTop3AvailableError, PushError)
        assert issubclass(SilenceWindowActiveError, PushError)
        assert issubclass(DailyCapReachedError, PushError)
        assert issubclass(NudgeDispatchFailedError, PushError)

    def test_nudge_dispatch_failed_attributes(self):
        err = NudgeDispatchFailedError(task_id="t1", attempt_count=3, cause="timeout")
        assert err.task_id == "t1"
        assert err.attempt_count == 3
        assert "timeout" in err.cause
        assert "t1" in str(err)

"""Unit tests for NudgeService — all repos/ports are fakes (no DynamoDB/Telegram)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.push.application.nudge_service import NudgeService, _PROHIBITED_PHRASES
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import NudgeDispatchStatus


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakePreferencesRepo:
    def __init__(self, prefs: Optional[UserNudgePreferences] = None):
        self._prefs = prefs

    def get(self, user_id: str):
        return self._prefs

    def save(self, prefs):
        self._prefs = prefs


class FakeCycleEventRepo:
    def __init__(self, active_cycle=None, nudge_count=0, last_activity=None):
        self._cycle = active_cycle
        self._nudge_count = nudge_count
        self._last_activity = last_activity
        self.events: list[dict] = []

    def get_active(self, user_id, for_date):
        return self._cycle

    def create(self, cycle):
        self._cycle = cycle

    def record_nudge_event(self, cycle_id, event_type, metadata):
        self.events.append({"cycle_id": cycle_id, "event_type": event_type, **metadata})

    def get_nudge_count(self, cycle_id):
        return self._nudge_count

    def get_last_activity_at(self, user_id):
        return self._last_activity


class FakeTaskRepo:
    def __init__(self, task: Optional[TaskState] = None):
        self._task = task
        self.saved: list[TaskState] = []

    def get_by_id(self, user_id, task_id):
        return self._task

    def save(self, task):
        self.saved.append(task)


class FakeTelegramPort:
    def __init__(self, should_succeed=True, fail_attempts=0):
        self._succeed = should_succeed
        self._fail_attempts = fail_attempts
        self._call_count = 0

    def send_nudge(self, chat_id, message):
        self._call_count += 1
        if self._call_count <= self._fail_attempts:
            raise Exception("telegram error")
        return self._succeed


class FakeDecisionService:
    def __init__(self, top3: Optional[Top3Result] = None):
        self._top3 = top3

    def get_top3(self, user_id, now=None):
        if self._top3 is None:
            raise Exception("no top3")
        return self._top3


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_task(task_id="t1", deadline=None):
    return TaskState(
        user_id="u1",
        original_text="Enviar propuesta al cliente",
        normalized_text="Enviar propuesta al cliente",
        source_intent_id="intent-1",
        status=TaskStatus.PRIORITIZED,
        task_id=task_id,
        deadline=deadline,
    )


def make_top3(task_id="t1"):
    score = PriorityScore(
        task_id=task_id,
        urgency_score=10,
        age_score=5,
        snooze_score=0,
        total_score=15,
        explanation="vence hoy",
    )
    cycle = ExecutionCycle(user_id="u1", date="2026-03-25")
    return Top3Result(cycle_id=cycle.cycle_id, user_id="u1", ranked_scores=(score,))


def make_service(
    prefs=None,
    active_cycle=None,
    nudge_count=0,
    last_activity=None,
    top3=None,
    telegram_succeeds=True,
    telegram_fail_attempts=0,
    task=None,
):
    if task is None:
        task = make_task()
    if top3 is None:
        top3 = make_top3()
    return NudgeService(
        prefs_repo=FakePreferencesRepo(prefs),
        cycle_event_repo=FakeCycleEventRepo(active_cycle, nudge_count, last_activity),
        task_repo=FakeTaskRepo(task),
        telegram_port=FakeTelegramPort(telegram_succeeds, telegram_fail_attempts),
        decision_service=FakeDecisionService(top3),
    )


NOW = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)  # 09:00 Bogota


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_dispatch_succeeds_returns_sent(self):
        svc = make_service()
        outcomes = svc.run_tick(["u1"], now=NOW)
        assert outcomes[0].status == NudgeDispatchStatus.sent

    def test_dispatch_sets_task_to_nudged(self):
        task_repo = FakeTaskRepo(make_task())
        top3 = make_top3()
        svc = NudgeService(
            prefs_repo=FakePreferencesRepo(),
            cycle_event_repo=FakeCycleEventRepo(),
            task_repo=task_repo,
            telegram_port=FakeTelegramPort(True),
            decision_service=FakeDecisionService(top3),
        )
        svc.run_tick(["u1"], now=NOW)
        assert task_repo.saved[0].status == TaskStatus.NUDGED

    def test_dispatch_records_nudge_sent_event(self):
        cycle_repo = FakeCycleEventRepo()
        svc = NudgeService(
            prefs_repo=FakePreferencesRepo(),
            cycle_event_repo=cycle_repo,
            task_repo=FakeTaskRepo(make_task()),
            telegram_port=FakeTelegramPort(True),
            decision_service=FakeDecisionService(make_top3()),
        )
        svc.run_tick(["u1"], now=NOW)
        event_types = [e["event_type"] for e in cycle_repo.events]
        assert "NUDGE_SCHEDULED" in event_types
        assert "NUDGE_SENT" in event_types


# ---------------------------------------------------------------------------
# Guard conditions
# ---------------------------------------------------------------------------

class TestGuards:
    def test_skipped_when_silence_window_active(self):
        # 14:00 UTC = 09:00 Bogota; set silence 08:00-10:00
        prefs = UserNudgePreferences(user_id="u1", silence_start="08:00", silence_end="10:00")
        svc = make_service(prefs=prefs)
        outcomes = svc.run_tick(["u1"], now=NOW)
        assert outcomes[0].status == NudgeDispatchStatus.skipped_activity
        assert outcomes[0].reason == "silence_window_active"

    def test_skipped_when_recent_activity(self):
        recent = NOW - timedelta(minutes=30)
        svc = make_service(last_activity=recent)
        outcomes = svc.run_tick(["u1"], now=NOW)
        assert outcomes[0].status == NudgeDispatchStatus.skipped_activity
        assert outcomes[0].reason == "recent_activity"

    def test_skipped_when_daily_cap_reached(self):
        svc = make_service(nudge_count=3)
        outcomes = svc.run_tick(["u1"], now=NOW)
        assert outcomes[0].status == NudgeDispatchStatus.skipped_activity
        assert outcomes[0].reason == "daily_cap_reached"

    def test_skipped_when_no_top3(self):
        svc = make_service(top3=None)
        # FakeDecisionService raises when top3 is None
        svc._decision = FakeDecisionService(None)
        outcomes = svc.run_tick(["u1"], now=NOW)
        assert outcomes[0].status == NudgeDispatchStatus.skipped_no_top3

    def test_skipped_when_top3_is_empty(self):
        empty_top3 = Top3Result(cycle_id="c1", user_id="u1", ranked_scores=())
        svc = make_service(top3=empty_top3)
        outcomes = svc.run_tick(["u1"], now=NOW)
        assert outcomes[0].status == NudgeDispatchStatus.skipped_no_top3

    def test_silence_window_crossing_midnight(self):
        # 22:00 - 07:00 silence; NOW = 09:00 Bogota (14:00 UTC) → outside window
        prefs = UserNudgePreferences(user_id="u1", silence_start="22:00", silence_end="07:00")
        svc = make_service(prefs=prefs)
        outcomes = svc.run_tick(["u1"], now=NOW)
        # 09:00 is NOT in 22:00-07:00 → should dispatch
        assert outcomes[0].status == NudgeDispatchStatus.sent

    def test_silence_window_crossing_midnight_blocks_at_23h(self):
        # 04:00 UTC = 23:00 Bogota → inside 22:00-07:00 window
        late_now = datetime(2026, 3, 26, 4, 0, tzinfo=timezone.utc)
        prefs = UserNudgePreferences(user_id="u1", silence_start="22:00", silence_end="07:00")
        svc = make_service(prefs=prefs)
        outcomes = svc.run_tick(["u1"], now=late_now)
        assert outcomes[0].status == NudgeDispatchStatus.skipped_activity


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

class TestRetry:
    def test_success_on_first_attempt(self):
        svc = make_service(telegram_fail_attempts=0)
        with patch("time.sleep"):
            outcomes = svc.run_tick(["u1"], now=NOW)
        assert outcomes[0].status == NudgeDispatchStatus.sent

    def test_success_on_second_attempt(self):
        svc = make_service(telegram_fail_attempts=1)
        with patch("time.sleep"):
            outcomes = svc.run_tick(["u1"], now=NOW)
        assert outcomes[0].status == NudgeDispatchStatus.sent

    def test_failure_after_all_retries(self):
        svc = make_service(telegram_fail_attempts=3)
        with patch("time.sleep"):
            outcomes = svc.run_tick(["u1"], now=NOW)
        assert outcomes[0].status == NudgeDispatchStatus.failed

    def test_failure_records_nudge_failed_event(self):
        cycle_repo = FakeCycleEventRepo()
        svc = NudgeService(
            prefs_repo=FakePreferencesRepo(),
            cycle_event_repo=cycle_repo,
            task_repo=FakeTaskRepo(make_task()),
            telegram_port=FakeTelegramPort(False, fail_attempts=3),
            decision_service=FakeDecisionService(make_top3()),
        )
        with patch("time.sleep"):
            svc.run_tick(["u1"], now=NOW)
        event_types = [e["event_type"] for e in cycle_repo.events]
        assert "NUDGE_FAILED" in event_types


# ---------------------------------------------------------------------------
# Nudge message tone guardrails (BR-PUSH-10)
# ---------------------------------------------------------------------------

class TestNudgeMessageTone:
    def test_build_nudge_message_no_prohibited_phrases(self):
        svc = make_service()
        task = make_task()
        prefs = UserNudgePreferences(user_id="u1")
        msg = svc._build_nudge_message(task, prefs)
        lower = msg.task_title.lower() + " " + msg.priority_reason.lower()
        for phrase in _PROHIBITED_PHRASES:
            assert phrase not in lower, f"Prohibited phrase found: {phrase!r}"

    def test_build_nudge_message_with_deadline(self):
        from datetime import date
        svc = make_service()
        task = make_task(deadline=datetime(2026, 3, 25, 18, 0, tzinfo=timezone.utc))
        prefs = UserNudgePreferences(user_id="u1")
        msg = svc._build_nudge_message(task, prefs)
        assert "vence" in msg.priority_reason.lower()

    def test_build_reengagement_message(self):
        svc = make_service()
        task = make_task()
        prefs = UserNudgePreferences(user_id="u1")
        msg = svc._build_nudge_message(task, prefs, is_reengagement=True)
        assert "listo" in msg.task_title.lower() or "retomar" in msg.task_title.lower()


# ---------------------------------------------------------------------------
# Re-engagement (BR-PUSH-15)
# ---------------------------------------------------------------------------

class TestReEngagement:
    def test_re_engagement_true_after_24h(self):
        svc = make_service()
        old = NOW - timedelta(hours=25)
        assert svc._check_re_engagement("u1", NOW, old) is True

    def test_re_engagement_false_under_24h(self):
        svc = make_service()
        recent = NOW - timedelta(hours=10)
        assert svc._check_re_engagement("u1", NOW, recent) is False

    def test_re_engagement_false_when_no_activity(self):
        svc = make_service()
        assert svc._check_re_engagement("u1", NOW, None) is False

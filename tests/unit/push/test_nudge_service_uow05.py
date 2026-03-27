"""Unit tests for NudgeService UOW-05 extensions — daily start/end, zen, rescue."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.push.application.daily_summary_builder import DailySummaryBuilder
from ppai.push.application.nudge_service import NudgeService
from ppai.push.application.rescue_evaluator import RescueEvaluator
from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import (
    DailySummary,
    DispatchOutcome,
    NudgeDispatchStatus,
    RescueSuggestion,
    TaskSummaryItem,
    ZenSession,
)


# ---------------------------------------------------------------------------
# Fakes (extended from test_nudge_service.py)
# ---------------------------------------------------------------------------

class FakePreferencesRepo:
    def __init__(self, prefs: Optional[UserNudgePreferences] = None):
        self._prefs = prefs
        self.saved_prefs: list[UserNudgePreferences] = []

    def get(self, user_id: str):
        return self._prefs

    def save(self, prefs):
        self._prefs = prefs
        self.saved_prefs.append(prefs)

    def get_all(self):
        return [self._prefs] if self._prefs else []


class FakeCycleEventRepo:
    def __init__(self, active_cycle=None, nudge_count=0, last_activity=None):
        self._cycle = active_cycle
        self._nudge_count = nudge_count
        self._last_activity = last_activity
        self.events: list[dict] = []
        self._events_today: dict[str, set[str]] = {}  # cycle_id -> set of event_types

    def get_active(self, user_id, for_date):
        return self._cycle

    def create(self, cycle):
        self._cycle = cycle

    def record_nudge_event(self, cycle_id, event_type, metadata):
        self.events.append({"cycle_id": cycle_id, "event_type": event_type, **metadata})
        self._events_today.setdefault(cycle_id, set()).add(event_type)

    def get_nudge_count(self, cycle_id):
        return self._nudge_count

    def get_last_activity_at(self, user_id):
        return self._last_activity

    def has_event_today(self, cycle_id, event_type):
        return event_type in self._events_today.get(cycle_id, set())


class FakeTaskRepo:
    def __init__(self, task=None, tasks_by_id=None):
        self._task = task
        self._tasks_by_id = tasks_by_id or {}
        self.saved: list = []

    def get_by_id(self, user_id, task_id):
        return self._tasks_by_id.get(task_id, self._task)

    def save(self, task):
        self.saved.append(task)

    def list_by_status(self, user_id, status):
        return []


class FakeTelegramPort:
    def __init__(self, should_succeed=True):
        self._succeed = should_succeed
        self.messages_sent: list[tuple[str, str]] = []
        self.nudges_sent: list = []

    def send_message(self, chat_id, text):
        self.messages_sent.append((chat_id, text))
        return self._succeed

    def send_nudge(self, chat_id, message):
        self.nudges_sent.append((chat_id, message))
        return self._succeed


class FakeDecisionService:
    def __init__(self, top3=None):
        self._top3 = top3

    def get_top3(self, user_id, now=None):
        if self._top3 is None:
            raise Exception("no top3")
        return self._top3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(task_id="t1", text="Enviar propuesta"):
    return TaskState(
        user_id="u1",
        original_text=text,
        normalized_text=text,
        source_intent_id="intent-1",
        status=TaskStatus.PRIORITIZED,
        task_id=task_id,
    )


def _make_top3(task_id="t1"):
    score = PriorityScore(
        task_id=task_id, urgency_score=10, age_score=5,
        snooze_score=0, total_score=15, explanation="vence hoy",
    )
    cycle = ExecutionCycle(user_id="u1", date="2026-03-26")
    return Top3Result(cycle_id=cycle.cycle_id, user_id="u1", ranked_scores=(score,))


def _make_service(
    prefs=None,
    active_cycle=None,
    telegram_succeeds=True,
    top3="default",
    task=None,
    zen_manager=None,
    summary_builder=None,
    rescue_evaluator=None,
    cycle_repo=None,
    task_repo=None,
    prefs_repo=None,
    telegram_port=None,
):
    if prefs is None:
        prefs = UserNudgePreferences(user_id="u1")
    if task is None:
        task = _make_task()
    if top3 == "default":
        top3 = _make_top3()

    pr = prefs_repo or FakePreferencesRepo(prefs)
    cr = cycle_repo or FakeCycleEventRepo(active_cycle)
    tr = task_repo or FakeTaskRepo(task)
    tp = telegram_port or FakeTelegramPort(telegram_succeeds)

    return NudgeService(
        prefs_repo=pr,
        cycle_event_repo=cr,
        task_repo=tr,
        telegram_port=tp,
        decision_service=FakeDecisionService(top3),
        zen_manager=zen_manager,
        daily_summary_builder=summary_builder,
        rescue_evaluator=rescue_evaluator,
    ), pr, cr, tr, tp


# Time: 08:00 Bogota = 13:00 UTC (within default daily_start_time 08:00 ±7min)
NOW_START = datetime(2026, 3, 26, 13, 0, tzinfo=timezone.utc)
# Time: 18:00 Bogota = 23:00 UTC (within default daily_end_time 18:00 ±7min)
NOW_END = datetime(2026, 3, 26, 23, 0, tzinfo=timezone.utc)
# Time: 12:00 Bogota = 17:00 UTC (outside both windows)
NOW_MID = datetime(2026, 3, 26, 17, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Daily Start Tests
# ---------------------------------------------------------------------------

class TestDailyStart:
    def test_morning_reminder_sent_in_window(self):
        """Daily start message sent when tick falls within start window."""
        svc, _, cr, _, tp = _make_service()
        outcomes = svc.run_tick(["u1"], now=NOW_START)

        sent = [o for o in outcomes if o.reason == "daily_start"]
        assert len(sent) == 1
        assert sent[0].status == NudgeDispatchStatus.sent
        assert len(tp.messages_sent) == 1
        assert "Buenos días" in tp.messages_sent[0][1]

    def test_morning_reminder_skip_idempotency(self):
        """Second tick in same window does not send again (DP-SCHED-02)."""
        svc, _, cr, _, tp = _make_service()
        svc.run_tick(["u1"], now=NOW_START)
        svc.run_tick(["u1"], now=NOW_START)

        start_events = [e for e in cr.events if e["event_type"] == "DAILY_START_SENT"]
        assert len(start_events) == 1
        assert len(tp.messages_sent) == 1

    def test_morning_reminder_not_sent_outside_window(self):
        """No daily start sent when tick is outside start window."""
        svc, _, _, _, tp = _make_service()
        outcomes = svc.run_tick(["u1"], now=NOW_MID)

        start_outcomes = [o for o in outcomes if o.reason == "daily_start"]
        assert len(start_outcomes) == 0

    def test_morning_message_with_top3(self):
        """Start message includes Top 3 tasks."""
        task = _make_task("t1", "Preparar informe")
        svc, _, _, _, tp = _make_service(task=task)
        svc.run_tick(["u1"], now=NOW_START)

        msg_text = tp.messages_sent[0][1]
        assert "Top 3" in msg_text
        assert "Preparar informe" in msg_text

    def test_morning_message_with_empty_top3(self):
        """Start message gracefully handles no tasks."""
        empty_top3 = Top3Result(cycle_id="c1", user_id="u1", ranked_scores=())
        svc, _, _, _, tp = _make_service(top3=empty_top3)
        svc.run_tick(["u1"], now=NOW_START)

        msg_text = tp.messages_sent[0][1]
        assert "Buenos días" in msg_text
        assert "No tienes tareas pendientes" in msg_text

    def test_morning_message_includes_motivational(self):
        """Start message includes custom motivational message."""
        prefs = UserNudgePreferences(user_id="u1", motivational_message="Vamos con todo!")
        svc, _, _, _, tp = _make_service(prefs=prefs)
        svc.run_tick(["u1"], now=NOW_START)

        msg_text = tp.messages_sent[0][1]
        assert "Vamos con todo!" in msg_text

    def test_morning_send_failure_returns_failed(self):
        """Failed telegram send returns failed outcome."""
        svc, _, _, _, _ = _make_service(telegram_succeeds=False)
        outcomes = svc.run_tick(["u1"], now=NOW_START)

        start = [o for o in outcomes if o.reason == "daily_start_send_failed"]
        assert len(start) == 1
        assert start[0].status == NudgeDispatchStatus.failed


# ---------------------------------------------------------------------------
# Daily End Tests
# ---------------------------------------------------------------------------

class TestDailyEnd:
    def test_end_summary_sent_in_window(self):
        """Daily end summary sent when tick falls within end window."""
        summary_builder = MagicMock(spec=DailySummaryBuilder)
        summary_builder.build.return_value = DailySummary(
            user_id="u1", date="2026-03-26",
            completed_tasks=[TaskSummaryItem("t1", "Tarea hecha", "completed")],
        )
        svc, _, cr, _, tp = _make_service(summary_builder=summary_builder)
        outcomes = svc.run_tick(["u1"], now=NOW_END)

        end = [o for o in outcomes if o.reason == "daily_end"]
        assert len(end) == 1
        assert end[0].status == NudgeDispatchStatus.sent
        assert "Resumen del día" in tp.messages_sent[0][1]

    def test_end_summary_with_detailed_list(self):
        """End message includes completed, pending, snoozed task lists."""
        summary_builder = MagicMock(spec=DailySummaryBuilder)
        summary_builder.build.return_value = DailySummary(
            user_id="u1", date="2026-03-26",
            completed_tasks=[TaskSummaryItem("t1", "Hecha 1", "completed")],
            pending_tasks=[TaskSummaryItem("t2", "Pendiente 1", "pending")],
            snoozed_tasks=[TaskSummaryItem("t3", "Pospuesta 1", "snoozed")],
        )
        svc, _, _, _, tp = _make_service(summary_builder=summary_builder)
        svc.run_tick(["u1"], now=NOW_END)

        msg = tp.messages_sent[0][1]
        assert "Hecha 1" in msg
        assert "Pendiente 1" in msg
        assert "Pospuesta 1" in msg
        assert "Completadas (1)" in msg

    def test_end_summary_skip_idempotency(self):
        """Second tick does not resend end summary (DP-SCHED-02)."""
        summary_builder = MagicMock(spec=DailySummaryBuilder)
        summary_builder.build.return_value = DailySummary(user_id="u1", date="2026-03-26")

        svc, _, cr, _, tp = _make_service(summary_builder=summary_builder)
        svc.run_tick(["u1"], now=NOW_END)
        svc.run_tick(["u1"], now=NOW_END)

        end_events = [e for e in cr.events if e["event_type"] == "DAILY_END_SENT"]
        assert len(end_events) == 1

    def test_end_with_rescue_mode(self):
        """End summary triggers rescue when día caído detected (BR-SCHED-06)."""
        summary_builder = MagicMock(spec=DailySummaryBuilder)
        summary_builder.build.return_value = DailySummary(
            user_id="u1", date="2026-03-26",
            completed_tasks=[],  # día caído
            pending_tasks=[TaskSummaryItem("t1", "Tarea pendiente", "pending")],
        )
        rescue_eval = RescueEvaluator()
        svc, _, cr, _, tp = _make_service(
            summary_builder=summary_builder,
            rescue_evaluator=rescue_eval,
            top3=None,  # no top3 available
        )
        svc.run_tick(["u1"], now=NOW_END)

        msg = tp.messages_sent[0][1]
        assert "día difícil" in msg
        assert "Tarea pendiente" in msg
        # Rescue event recorded
        rescue_events = [e for e in cr.events if e["event_type"] == "RESCUE_TRIGGERED"]
        assert len(rescue_events) == 1

    def test_end_without_rescue_productive_day(self):
        """No rescue when day was productive."""
        summary_builder = MagicMock(spec=DailySummaryBuilder)
        summary_builder.build.return_value = DailySummary(
            user_id="u1", date="2026-03-26",
            completed_tasks=[TaskSummaryItem("t1", "Tarea hecha", "completed")],
        )
        rescue_eval = RescueEvaluator()
        svc, _, cr, _, tp = _make_service(
            summary_builder=summary_builder,
            rescue_evaluator=rescue_eval,
        )
        svc.run_tick(["u1"], now=NOW_END)

        msg = tp.messages_sent[0][1]
        assert "Descansa bien" in msg
        assert "día difícil" not in msg

    def test_end_without_summary_builder(self):
        """End message falls back when no summary builder configured."""
        svc, _, _, _, tp = _make_service(summary_builder=None)
        outcomes = svc.run_tick(["u1"], now=NOW_END)

        end = [o for o in outcomes if o.reason == "daily_end"]
        assert len(end) == 1
        msg = tp.messages_sent[0][1]
        assert "No hay datos disponibles" in msg


# ---------------------------------------------------------------------------
# Zen Nudge Tests
# ---------------------------------------------------------------------------

class TestZenNudge:
    def test_zen_nudge_sent(self):
        """Zen nudge dispatched when zen active and session not capped."""
        prefs = UserNudgePreferences(user_id="u1", zen_active=True)
        zen_mgr = ZenSessionManager()
        zen_mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=5)

        svc, _, _, _, tp = _make_service(prefs=prefs, zen_manager=zen_mgr)
        with patch("time.sleep"):
            outcomes = svc.run_tick(["u1"], now=NOW_MID)

        zen_outcomes = [o for o in outcomes if o.status == NudgeDispatchStatus.sent]
        assert len(zen_outcomes) >= 1

    def test_zen_skip_when_cap_reached(self):
        """Zen auto-deactivates when cap is reached (BR-SCHED-10)."""
        prefs = UserNudgePreferences(user_id="u1", zen_active=True, zen_max_nudges=3)
        zen_mgr = ZenSessionManager()
        session = zen_mgr.activate("u1", zen_max_nudges=3, zen_interval_minutes=5)
        session.nudges_sent = 3  # Already at cap

        prefs_repo = FakePreferencesRepo(prefs)
        cr = FakeCycleEventRepo()
        tp = FakeTelegramPort()

        svc, _, _, _, _ = _make_service(
            prefs=prefs, zen_manager=zen_mgr,
            prefs_repo=prefs_repo, cycle_repo=cr, telegram_port=tp,
        )
        outcomes = svc.run_tick(["u1"], now=NOW_MID)

        # Auto-deactivation message sent
        deactivation_msgs = [m for m in tp.messages_sent if "completado" in m[1]]
        assert len(deactivation_msgs) == 1
        # Prefs saved with zen_active=False
        assert prefs_repo.saved_prefs[-1].zen_active is False
        # ZEN_DEACTIVATED event recorded
        deact_events = [e for e in cr.events if e["event_type"] == "ZEN_DEACTIVATED"]
        assert len(deact_events) == 1

    def test_zen_override_silence(self):
        """Zen nudges ignore silence window (BR-SCHED-12, DP-SCHED-05)."""
        prefs = UserNudgePreferences(
            user_id="u1",
            zen_active=True,
            silence_start="11:00",
            silence_end="13:00",  # NOW_MID (12:00 Bogota) is inside silence
        )
        zen_mgr = ZenSessionManager()
        zen_mgr.activate("u1", zen_max_nudges=10, zen_interval_minutes=5)

        svc, _, _, _, tp = _make_service(prefs=prefs, zen_manager=zen_mgr)
        with patch("time.sleep"):
            outcomes = svc.run_tick(["u1"], now=NOW_MID)

        # Zen nudge should be sent despite silence window
        sent = [o for o in outcomes if o.status == NudgeDispatchStatus.sent]
        assert len(sent) >= 1

    def test_zen_not_active_no_regular_nudges(self):
        """When zen_active=False, no regular nudges dispatched (BR-SCHED-13)."""
        prefs = UserNudgePreferences(user_id="u1", zen_active=False)
        svc, _, _, _, tp = _make_service(prefs=prefs)
        outcomes = svc.run_tick(["u1"], now=NOW_MID)

        # Outside start/end windows and zen not active → no outcomes
        assert len(outcomes) == 0

    def test_zen_no_session_no_nudge(self):
        """Zen active in prefs but no session in manager → no nudge."""
        prefs = UserNudgePreferences(user_id="u1", zen_active=True)
        zen_mgr = ZenSessionManager()
        # Note: NOT calling zen_mgr.activate()

        svc, _, _, _, tp = _make_service(prefs=prefs, zen_manager=zen_mgr)
        outcomes = svc.run_tick(["u1"], now=NOW_MID)

        zen_sent = [o for o in outcomes if o.status == NudgeDispatchStatus.sent]
        assert len(zen_sent) == 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_tick_error_returns_failed_outcome(self):
        """Unhandled exception in user evaluation returns failed outcome."""
        prefs_repo = MagicMock()
        prefs_repo.get.side_effect = RuntimeError("db down")

        svc = NudgeService(
            prefs_repo=prefs_repo,
            cycle_event_repo=FakeCycleEventRepo(),
            task_repo=FakeTaskRepo(),
            telegram_port=FakeTelegramPort(),
            decision_service=FakeDecisionService(),
        )
        outcomes = svc.run_tick(["u1"], now=NOW_MID)
        assert len(outcomes) == 1
        assert outcomes[0].status == NudgeDispatchStatus.failed
        assert "db down" in outcomes[0].reason

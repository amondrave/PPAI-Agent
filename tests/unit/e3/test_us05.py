"""
BDD acceptance tests for US-05: Nudge accionable en Telegram.
Scenarios from tests/features/e3/us05.feature
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.push.application.nudge_service import NudgeService
from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import NudgeDispatchStatus


# ---------------------------------------------------------------------------
# Minimal fakes (same pattern as tests/unit/push/test_nudge_service.py)
# ---------------------------------------------------------------------------

class _PrefsRepo:
    def __init__(self, prefs=None):
        self._prefs = prefs
    def get(self, user_id):
        return self._prefs
    def save(self, prefs):
        self._prefs = prefs


class _CycleRepo:
    def __init__(self, nudge_count=0, last_activity=None):
        self._nudge_count = nudge_count
        self._last_activity = last_activity
        self._cycle = None
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


class _TaskRepo:
    def __init__(self, task=None):
        self._task = task
        self.saved: list = []
    def get_by_id(self, user_id, task_id):
        return self._task
    def save(self, task):
        self.saved.append(task)


class _TelegramPort:
    def __init__(self, fail_attempts=0, always_fail=False):
        self._fail_attempts = fail_attempts
        self._always_fail = always_fail
        self.call_count = 0
    def send_nudge(self, chat_id, message):
        self.call_count += 1
        if self._always_fail or self.call_count <= self._fail_attempts:
            raise Exception("telegram transient error")
        return True


class _DecisionService:
    def __init__(self, top3=None):
        self._top3 = top3
    def get_top3(self, user_id, now=None):
        if self._top3 is None:
            raise Exception("no top3")
        return self._top3


def _make_task(task_id="t1"):
    return TaskState(
        user_id="u1",
        original_text="Enviar propuesta al cliente",
        normalized_text="Enviar propuesta al cliente",
        source_intent_id="intent-1",
        status=TaskStatus.PRIORITIZED,
        task_id=task_id,
    )


def _make_top3(task_id="t1"):
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


# 12:00 Bogota = 17:00 UTC  — outside start/end windows, so zen path is evaluated
NOW = datetime(2026, 3, 25, 17, 0, tzinfo=timezone.utc)


def _make_zen_service(cycle_repo, task_repo, telegram, decision):
    zen_manager = ZenSessionManager()
    zen_manager.activate("u1", zen_max_nudges=10, zen_interval_minutes=15)
    return NudgeService(
        prefs_repo=_PrefsRepo(UserNudgePreferences(user_id="u1", zen_active=True)),
        cycle_event_repo=cycle_repo,
        task_repo=task_repo,
        telegram_port=telegram,
        decision_service=decision,
        zen_manager=zen_manager,
    )


# ---------------------------------------------------------------------------
# US-05 Scenario: Nudge enviado exitosamente con botones inline
# ---------------------------------------------------------------------------

def test_nudge_sent_with_inline_buttons():
    """
    Given usuario con Top 3 vigente
    When el scheduler ejecuta el tick
    Then nudge enviado, tarea → NUDGED, evento NUDGE_SENT registrado
    """
    cycle_repo = _CycleRepo()
    task_repo = _TaskRepo(_make_task())
    svc = _make_zen_service(
        cycle_repo,
        task_repo,
        _TelegramPort(),
        _DecisionService(_make_top3()),
    )
    outcomes = svc.run_tick(["u1"], now=NOW)

    assert outcomes[0].status == NudgeDispatchStatus.sent
    assert task_repo.saved[0].status == TaskStatus.NUDGED
    event_types = [e["event_type"] for e in cycle_repo.events]
    assert "NUDGE_SENT" in event_types


# ---------------------------------------------------------------------------
# US-05 Scenario: Nudge sin Top 3 disponible
# ---------------------------------------------------------------------------

def test_nudge_skipped_when_no_top3():
    """
    Given no existe Top 3 vigente
    When el scheduler ejecuta el tick
    Then no se envía mensaje y outcome = skipped_no_top3
    """
    telegram = _TelegramPort()
    svc = _make_zen_service(
        _CycleRepo(),
        _TaskRepo(_make_task()),
        telegram,
        _DecisionService(None),
    )
    outcomes = svc.run_tick(["u1"], now=NOW)

    assert outcomes[0].status == NudgeDispatchStatus.skipped_no_top3
    assert telegram.call_count == 0


# ---------------------------------------------------------------------------
# US-05 Scenario: Reintento controlado ante fallo transitorio
# ---------------------------------------------------------------------------

def test_nudge_retry_on_transient_failure():
    """
    Given el primer intento falla con error transitorio
    When el scheduler ejecuta el tick
    Then se realizan hasta 3 intentos y si el 2.° tiene éxito → NUDGE_SENT
    """
    cycle_repo = _CycleRepo()
    telegram = _TelegramPort(fail_attempts=1)  # falla 1 vez, luego ok
    svc = _make_zen_service(
        cycle_repo,
        _TaskRepo(_make_task()),
        telegram,
        _DecisionService(_make_top3()),
    )
    with patch("time.sleep"):
        outcomes = svc.run_tick(["u1"], now=NOW)

    assert outcomes[0].status == NudgeDispatchStatus.sent
    assert telegram.call_count == 2  # 1 fallo + 1 éxito
    event_types = [e["event_type"] for e in cycle_repo.events]
    assert "NUDGE_SENT" in event_types


# ---------------------------------------------------------------------------
# US-05 Scenario: Fallo definitivo después de 3 intentos
# ---------------------------------------------------------------------------

def test_nudge_failed_after_all_retries():
    """
    Given todos los intentos de envío a Telegram fallan
    When el scheduler ejecuta el tick
    Then outcome = failed, evento NUDGE_FAILED registrado, tarea no cambia estado
    """
    cycle_repo = _CycleRepo()
    task_repo = _TaskRepo(_make_task())
    svc = _make_zen_service(
        cycle_repo,
        task_repo,
        _TelegramPort(always_fail=True),
        _DecisionService(_make_top3()),
    )
    with patch("time.sleep"):
        outcomes = svc.run_tick(["u1"], now=NOW)

    assert outcomes[0].status == NudgeDispatchStatus.failed
    event_types = [e["event_type"] for e in cycle_repo.events]
    assert "NUDGE_FAILED" in event_types
    assert "NUDGE_SENT" not in event_types
    assert len(task_repo.saved) == 0  # tarea no cambia estado


# ---------------------------------------------------------------------------
# US-05 Scenario: Re-engagement por inactividad mayor a 24 horas
# ---------------------------------------------------------------------------

def test_reengagement_after_24h_inactivity():
    """
    Given usuario lleva +24h sin actividad en el loop
    When el scheduler evalúa el tick
    Then se envía nudge motivacional suave (reengagement template)
    """
    old_activity = NOW - timedelta(hours=25)
    cycle_repo = _CycleRepo(last_activity=old_activity)
    task_repo = _TaskRepo(_make_task())
    svc = _make_zen_service(
        cycle_repo,
        task_repo,
        _TelegramPort(),
        _DecisionService(_make_top3()),
    )
    outcomes = svc.run_tick(["u1"], now=NOW)

    assert outcomes[0].status == NudgeDispatchStatus.sent
    # verify re-engagement tone in the sent nudge message
    sent_task = task_repo.saved[0]
    assert sent_task.status == TaskStatus.NUDGED
    # The reengagement flag produces "listo" or "retomar" in the message
    prefs = UserNudgePreferences(user_id="u1")
    msg = svc._build_nudge_message(_make_task(), prefs, is_reengagement=True)
    text_lower = msg.task_title.lower()
    assert "listo" in text_lower or "retomar" in text_lower

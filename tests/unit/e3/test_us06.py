"""
BDD acceptance tests for US-06: Control de intensidad y ventana de empuje.
Scenarios from tests/features/e3/us06.feature
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.push.application.nudge_service import NudgeService
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import NudgeDispatchStatus


# ---------------------------------------------------------------------------
# Minimal fakes
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
    def __init__(self):
        self.saved: list = []
    def get_by_id(self, user_id, task_id):
        return TaskState(
            user_id="u1",
            original_text="Enviar propuesta",
            normalized_text="Enviar propuesta",
            source_intent_id="i1",
            status=TaskStatus.PRIORITIZED,
            task_id=task_id,
        )
    def save(self, task):
        self.saved.append(task)


class _TelegramPort:
    def __init__(self):
        self.call_count = 0
    def send_nudge(self, chat_id, message):
        self.call_count += 1
        return True


class _DecisionService:
    def __init__(self, top3=None):
        self._top3 = top3
    def get_top3(self, user_id, now=None):
        if self._top3 is None:
            raise Exception("no top3")
        return self._top3


def _make_top3():
    score = PriorityScore(
        task_id="t1", urgency_score=10, age_score=5,
        snooze_score=0, total_score=15, explanation="prioridad"
    )
    cycle = ExecutionCycle(user_id="u1", date="2026-03-25")
    return Top3Result(cycle_id=cycle.cycle_id, user_id="u1", ranked_scores=(score,))


def _make_service(prefs=None, nudge_count=0, last_activity=None, top3=None, telegram=None):
    if top3 is None:
        top3 = _make_top3()
    if telegram is None:
        telegram = _TelegramPort()
    return NudgeService(
        prefs_repo=_PrefsRepo(prefs),
        cycle_event_repo=_CycleRepo(nudge_count=nudge_count, last_activity=last_activity),
        task_repo=_TaskRepo(),
        telegram_port=telegram,
        decision_service=_DecisionService(top3),
    )


# 09:00 Bogota = 14:00 UTC
NOW = datetime(2026, 3, 25, 14, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# US-06 Scenario: Nudge omitido durante ventana de silencio
# ---------------------------------------------------------------------------

def test_nudge_skipped_during_silence_window():
    """
    Given usuario configuró silencio 22:00 - 08:00
    And hora actual = 23:30 local (03:30 UTC next day)
    When el scheduler evalúa el tick
    Then no se envía nudge
    """
    # 03:30 UTC → 22:30 Bogota (UTC-5) → dentro ventana 22:00-08:00
    late_utc = datetime(2026, 3, 26, 3, 30, tzinfo=timezone.utc)
    prefs = UserNudgePreferences(user_id="u1", silence_start="22:00", silence_end="08:00")
    telegram = _TelegramPort()
    svc = _make_service(prefs=prefs, telegram=telegram)

    outcomes = svc.run_tick(["u1"], now=late_utc)

    assert outcomes[0].status == NudgeDispatchStatus.skipped_activity
    assert "silence" in (outcomes[0].reason or "")
    assert telegram.call_count == 0


# ---------------------------------------------------------------------------
# US-06 Scenario: Ventana de silencio que cruza medianoche
# ---------------------------------------------------------------------------

def test_silence_window_crossing_midnight():
    """
    Given ventana de silencio 23:00 - 07:00
    And hora actual = 01:00 local (06:00 UTC)
    When el scheduler evalúa el tick
    Then no se envía nudge
    """
    # 06:00 UTC → 01:00 Bogota → dentro ventana 23:00-07:00
    early_utc = datetime(2026, 3, 26, 6, 0, tzinfo=timezone.utc)
    prefs = UserNudgePreferences(user_id="u1", silence_start="23:00", silence_end="07:00")
    telegram = _TelegramPort()
    svc = _make_service(prefs=prefs, telegram=telegram)

    outcomes = svc.run_tick(["u1"], now=early_utc)

    assert outcomes[0].status == NudgeDispatchStatus.skipped_activity
    assert telegram.call_count == 0


# ---------------------------------------------------------------------------
# US-06 Scenario: Nudge omitido por actividad reciente < 60 min
# ---------------------------------------------------------------------------

def test_nudge_skipped_with_recent_activity():
    """
    Given usuario tuvo actividad hace 30 minutos
    When el scheduler evalúa el tick
    Then no se envía nudge, motivo = skipped_activity
    """
    recent = NOW - timedelta(minutes=30)
    telegram = _TelegramPort()
    svc = _make_service(last_activity=recent, telegram=telegram)

    outcomes = svc.run_tick(["u1"], now=NOW)

    assert outcomes[0].status == NudgeDispatchStatus.skipped_activity
    assert outcomes[0].reason == "recent_activity"
    assert telegram.call_count == 0


# ---------------------------------------------------------------------------
# US-06 Scenario: Límite diario de nudges alcanzado
# ---------------------------------------------------------------------------

def test_nudge_skipped_when_daily_cap_reached():
    """
    Given usuario ya recibió 3 nudges hoy (cap por defecto)
    When el scheduler evalúa el tick
    Then no se envía nudge adicional
    """
    telegram = _TelegramPort()
    svc = _make_service(nudge_count=3, telegram=telegram)

    outcomes = svc.run_tick(["u1"], now=NOW)

    assert outcomes[0].status == NudgeDispatchStatus.skipped_activity
    assert outcomes[0].reason == "daily_cap_reached"
    assert telegram.call_count == 0


# ---------------------------------------------------------------------------
# US-06 Scenario: Nudge enviado cuando no hay bloqueadores
# ---------------------------------------------------------------------------

def test_nudge_sent_when_no_blockers():
    """
    Given usuario sin ventana de silencio activa
    And sin actividad reciente
    And menos de 3 nudges hoy
    When el scheduler evalúa el tick
    Then nudge enviado normalmente
    """
    telegram = _TelegramPort()
    svc = _make_service(nudge_count=0, last_activity=None, telegram=telegram)

    outcomes = svc.run_tick(["u1"], now=NOW)

    assert outcomes[0].status == NudgeDispatchStatus.sent
    assert telegram.call_count == 1


# ---------------------------------------------------------------------------
# US-06 Scenario: Cambio de configuración afecta solo futuros nudges
# ---------------------------------------------------------------------------

def test_config_change_only_affects_future_nudges():
    """
    Given usuario actualiza ventana de silencio
    Then los próximos ticks respetan la nueva configuración
    And nudges ya enviados no se retroactivan
    """
    prefs_repo = _PrefsRepo()

    # Primera ejecución: sin silencio → nudge enviado
    svc1 = NudgeService(
        prefs_repo=prefs_repo,
        cycle_event_repo=_CycleRepo(),
        task_repo=_TaskRepo(),
        telegram_port=_TelegramPort(),
        decision_service=_DecisionService(_make_top3()),
    )
    outcomes1 = svc1.run_tick(["u1"], now=NOW)
    assert outcomes1[0].status == NudgeDispatchStatus.sent

    # Ahora el usuario actualiza su configuración con ventana de silencio que cubre NOW
    new_prefs = UserNudgePreferences(user_id="u1", silence_start="08:00", silence_end="10:00")
    prefs_repo.save(new_prefs)  # simula cambio de configuración

    # Segunda ejecución con la misma hora: ahora cae dentro del silencio
    telegram2 = _TelegramPort()
    svc2 = NudgeService(
        prefs_repo=prefs_repo,
        cycle_event_repo=_CycleRepo(),
        task_repo=_TaskRepo(),
        telegram_port=telegram2,
        decision_service=_DecisionService(_make_top3()),
    )
    outcomes2 = svc2.run_tick(["u1"], now=NOW)

    # NOW (09:00 Bogota) cae dentro del silencio 08:00-10:00
    assert outcomes2[0].status == NudgeDispatchStatus.skipped_activity
    assert telegram2.call_count == 0

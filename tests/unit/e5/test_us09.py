"""BDD acceptance tests for US-09: reporte diario no acusatorio."""
from __future__ import annotations

from datetime import datetime, timezone

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.push.application.daily_summary_builder import DailySummaryBuilder
from ppai.push.application.nudge_service import NudgeService
from ppai.push.application.rescue_evaluator import RescueEvaluator
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import NudgeDispatchStatus


class _PrefsRepo:
    def __init__(self, prefs=None):
        self._prefs = prefs

    def get(self, user_id):
        return self._prefs

    def save(self, prefs):
        self._prefs = prefs


class _CycleRepo:
    def __init__(self):
        self._cycle = None
        self.events: list[dict] = []
        self._events_today: dict[str, set[str]] = {}

    def get_active(self, user_id, for_date):
        return self._cycle

    def create(self, cycle):
        self._cycle = cycle

    def record_nudge_event(self, cycle_id, event_type, metadata):
        self.events.append({"cycle_id": cycle_id, "event_type": event_type, **metadata})
        self._events_today.setdefault(cycle_id, set()).add(event_type)

    def get_nudge_count(self, cycle_id):
        return 0

    def get_last_activity_at(self, user_id):
        return None

    def has_event_today(self, cycle_id, event_type):
        return event_type in self._events_today.get(cycle_id, set())


class _TaskRepo:
    def __init__(self, tasks_by_status=None, tasks_by_id=None):
        self._tasks_by_status = tasks_by_status or {}
        self._tasks_by_id = tasks_by_id or {}

    def list_by_status(self, user_id, status):
        return self._tasks_by_status.get(status, [])

    def get_by_id(self, user_id, task_id):
        return self._tasks_by_id.get(task_id)

    def save(self, task):
        self._tasks_by_id[task.task_id] = task


class _Telegram:
    def __init__(self):
        self.messages_sent: list[str] = []

    def send_message(self, chat_id, text):
        self.messages_sent.append(text)
        return True

    def send_nudge(self, chat_id, message):
        return True


class _Decision:
    def __init__(self, top3):
        self._top3 = top3

    def get_top3(self, user_id, now=None):
        return self._top3


def _task(task_id: str, title: str, status: TaskStatus, completed_at=None):
    return TaskState(
        user_id="u1",
        original_text=title,
        normalized_text=title,
        source_intent_id=f"intent-{task_id}",
        status=status,
        task_id=task_id,
        completed_at=completed_at,
    )


def _top3(*task_ids: str):
    scores = tuple(
        PriorityScore(
            task_id=task_id,
            urgency_score=10,
            age_score=5,
            snooze_score=0,
            total_score=15,
            explanation="prioridad",
        )
        for task_id in task_ids
    )
    cycle = ExecutionCycle(user_id="u1", date="2026-03-27")
    return Top3Result(cycle_id=cycle.cycle_id, user_id="u1", ranked_scores=scores)


START_NOW = datetime(2026, 3, 27, 13, 0, tzinfo=timezone.utc)
END_NOW = datetime(2026, 3, 27, 23, 0, tzinfo=timezone.utc)


def test_recibo_top3_automaticamente_cada_manana():
    prefs = UserNudgePreferences(user_id="u1")
    cycle_repo = _CycleRepo()
    task_repo = _TaskRepo(
        tasks_by_id={"t1": _task("t1", "Preparar propuesta", TaskStatus.PENDING)}
    )
    telegram = _Telegram()
    service = NudgeService(
        prefs_repo=_PrefsRepo(prefs),
        cycle_event_repo=cycle_repo,
        task_repo=task_repo,
        telegram_port=telegram,
        decision_service=_Decision(_top3("t1")),
        daily_summary_builder=DailySummaryBuilder(task_repo),
        rescue_evaluator=RescueEvaluator(),
    )

    outcomes = service.run_tick(["u1"], now=START_NOW)

    assert any(o.reason == "daily_start" and o.status == NudgeDispatchStatus.sent for o in outcomes)
    assert "Top 3 para hoy" in telegram.messages_sent[0]
    assert any(e["event_type"] == "DAILY_START_SENT" for e in cycle_repo.events)


def test_recibo_resumen_de_cierre_con_detalle_del_dia():
    prefs = UserNudgePreferences(user_id="u1")
    cycle_repo = _CycleRepo()
    task_repo = _TaskRepo(
        tasks_by_status={
            TaskStatus.DONE: [_task("d1", "Cerrar propuesta", TaskStatus.DONE, completed_at=END_NOW)],
            TaskStatus.PENDING: [_task("p1", "Llamar lead", TaskStatus.PENDING)],
            TaskStatus.SNOOZED: [_task("s1", "Actualizar dashboard", TaskStatus.SNOOZED)],
        },
        tasks_by_id={"p1": _task("p1", "Llamar lead", TaskStatus.PENDING)},
    )
    telegram = _Telegram()
    service = NudgeService(
        prefs_repo=_PrefsRepo(prefs),
        cycle_event_repo=cycle_repo,
        task_repo=task_repo,
        telegram_port=telegram,
        decision_service=_Decision(_top3("p1")),
        daily_summary_builder=DailySummaryBuilder(task_repo),
        rescue_evaluator=RescueEvaluator(),
    )

    outcomes = service.run_tick(["u1"], now=END_NOW)

    assert any(o.reason == "daily_end" and o.status == NudgeDispatchStatus.sent for o in outcomes)
    message = telegram.messages_sent[0]
    assert "Completadas (1)" in message
    assert "Pendientes (1)" in message
    assert "Pospuestas (1)" in message
    assert any(e["event_type"] == "DAILY_END_SENT" for e in cycle_repo.events)


def test_configuro_horarios_de_inicio_y_cierre_en_preferencias():
    prefs = UserNudgePreferences(user_id="u1")
    repo = _PrefsRepo(prefs)

    updated = repo.get("u1")
    updated.daily_start_time = "09:15"
    updated.daily_end_time = "19:30"
    repo.save(updated)

    saved = repo.get("u1")
    assert saved.daily_start_time == "09:15"
    assert saved.daily_end_time == "19:30"

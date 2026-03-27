"""BDD acceptance tests for US-10: rescue mode y modo zen."""
from __future__ import annotations

from datetime import datetime, timezone

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.push.application.daily_summary_builder import DailySummaryBuilder
from ppai.push.application.nudge_service import NudgeService
from ppai.push.application.rescue_evaluator import RescueEvaluator
from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import NudgeDispatchStatus


class _PrefsRepo:
    def __init__(self, prefs=None):
        self._prefs = prefs
        self.saved: list[UserNudgePreferences] = []

    def get(self, user_id):
        return self._prefs

    def save(self, prefs):
        self._prefs = prefs
        self.saved.append(prefs)


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
        self.saved: list[TaskState] = []

    def list_by_status(self, user_id, status):
        return self._tasks_by_status.get(status, [])

    def get_by_id(self, user_id, task_id):
        return self._tasks_by_id.get(task_id)

    def save(self, task):
        self.saved.append(task)
        self._tasks_by_id[task.task_id] = task


class _Telegram:
    def __init__(self):
        self.messages_sent: list[str] = []
        self.nudges_sent: list[object] = []

    def send_message(self, chat_id, text):
        self.messages_sent.append(text)
        return True

    def send_nudge(self, chat_id, message):
        self.nudges_sent.append(message)
        return True


class _Decision:
    def __init__(self, top3):
        self._top3 = top3

    def get_top3(self, user_id, now=None):
        return self._top3


def _task(task_id: str, title: str, status: TaskStatus):
    return TaskState(
        user_id="u1",
        original_text=title,
        normalized_text=title,
        source_intent_id=f"intent-{task_id}",
        status=status,
        task_id=task_id,
    )


def _top3(task_id: str):
    cycle = ExecutionCycle(user_id="u1", date="2026-03-27")
    score = PriorityScore(
        task_id=task_id,
        urgency_score=10,
        age_score=5,
        snooze_score=0,
        total_score=15,
        explanation="prioridad",
    )
    return Top3Result(cycle_id=cycle.cycle_id, user_id="u1", ranked_scores=(score,))


MID_NOW = datetime(2026, 3, 27, 17, 0, tzinfo=timezone.utc)
END_NOW = datetime(2026, 3, 27, 23, 0, tzinfo=timezone.utc)
SILENCE_NOW = datetime(2026, 3, 27, 4, 0, tzinfo=timezone.utc)  # 23:00 Bogota previous day


def test_recibo_propuesta_de_rescate_en_dia_caido():
    prefs = UserNudgePreferences(user_id="u1")
    cycle_repo = _CycleRepo()
    pending = _task("p1", "Retomar onboarding", TaskStatus.PENDING)
    task_repo = _TaskRepo(
        tasks_by_status={
            TaskStatus.DONE: [],
            TaskStatus.PENDING: [pending],
            TaskStatus.SNOOZED: [],
        },
        tasks_by_id={"p1": pending},
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

    assert any(o.reason == "daily_end" for o in outcomes)
    assert "Dedícale solo 5 minutos" in telegram.messages_sent[0]
    assert any(e["event_type"] == "RESCUE_TRIGGERED" for e in cycle_repo.events)


def test_activo_modo_zen_y_recibo_nudge_durante_la_sesion():
    prefs = UserNudgePreferences(user_id="u1", zen_active=True)
    cycle_repo = _CycleRepo()
    task = _task("t1", "Preparar release", TaskStatus.PRIORITIZED)
    task_repo = _TaskRepo(tasks_by_id={"t1": task})
    telegram = _Telegram()
    zen_manager = ZenSessionManager()
    zen_manager.activate("u1", zen_max_nudges=3, zen_interval_minutes=10)
    service = NudgeService(
        prefs_repo=_PrefsRepo(prefs),
        cycle_event_repo=cycle_repo,
        task_repo=task_repo,
        telegram_port=telegram,
        decision_service=_Decision(_top3("t1")),
        zen_manager=zen_manager,
        daily_summary_builder=DailySummaryBuilder(task_repo),
        rescue_evaluator=RescueEvaluator(),
    )

    outcomes = service.run_tick(["u1"], now=MID_NOW)

    assert any(o.status == NudgeDispatchStatus.sent for o in outcomes)
    assert len(telegram.nudges_sent) == 1


def test_modo_zen_ignora_ventana_de_silencio():
    prefs = UserNudgePreferences(
        user_id="u1",
        zen_active=True,
        silence_start="22:00",
        silence_end="08:00",
    )
    cycle_repo = _CycleRepo()
    task = _task("t1", "Escribir follow-up", TaskStatus.PRIORITIZED)
    task_repo = _TaskRepo(tasks_by_id={"t1": task})
    telegram = _Telegram()
    zen_manager = ZenSessionManager()
    zen_manager.activate("u1", zen_max_nudges=3, zen_interval_minutes=10)
    service = NudgeService(
        prefs_repo=_PrefsRepo(prefs),
        cycle_event_repo=cycle_repo,
        task_repo=task_repo,
        telegram_port=telegram,
        decision_service=_Decision(_top3("t1")),
        zen_manager=zen_manager,
        daily_summary_builder=DailySummaryBuilder(task_repo),
        rescue_evaluator=RescueEvaluator(),
    )

    outcomes = service.run_tick(["u1"], now=SILENCE_NOW)

    assert any(o.status == NudgeDispatchStatus.sent for o in outcomes)
    assert len(telegram.nudges_sent) == 1

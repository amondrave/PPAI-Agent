"""
BDD acceptance tests for US-08: Registro mínimo de eventos del loop.
Scenarios from tests/features/e4/us08.feature
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.domain.entities import ExecutionCycle
from ppai.respond.application.response_service import ResponseService
from ppai.respond.domain.entities import InteractionEvent

NOW = datetime(2026, 3, 26, 14, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Minimal fakes
# ---------------------------------------------------------------------------

class _TaskRepo:
    def __init__(self, tasks=None):
        self._tasks = {(t.user_id, t.task_id): t for t in (tasks or [])}
        self.saved = []

    def get_by_id(self, user_id, task_id):
        return self._tasks.get((user_id, task_id))

    def save(self, task):
        self.saved.append(task)
        self._tasks[(task.user_id, task.task_id)] = task

    def count_active(self, user_id):
        return 0

    def list_by_status(self, user_id, status):
        return [t for t in self._tasks.values() if t.user_id == user_id and t.status == status]


class _EventRepo:
    def __init__(self, fail=False):
        self.events = []
        self._fail = fail

    def append(self, event):
        if self._fail:
            raise RuntimeError("event write failed")
        self.events.append(event)


class _CycleEventRepo:
    def __init__(self):
        self.events = []

    def record_nudge_event(self, cycle_id, event_type, metadata):
        self.events.append({"cycle_id": cycle_id, "event_type": event_type, **metadata})

    def get_active(self, *a):
        return None

    def create(self, *a):
        pass

    def get_nudge_count(self, *a):
        return 0

    def get_last_activity_at(self, *a):
        return None


class _CycleRepo:
    def __init__(self):
        self._cycle = ExecutionCycle(user_id="u1", date="2026-03-26")

    def get_active(self, user_id, date):
        return self._cycle

    def save(self, cycle):
        pass

    def update_top3(self, *a):
        pass

    def increment_reorders(self, *a):
        pass


class _DecisionService:
    def __init__(self):
        self.invalidated = []

    def invalidate_cache(self, user_id):
        self.invalidated.append(user_id)


def _task(status=TaskStatus.NUDGED, snooze_count=0):
    return TaskState(
        user_id="u1",
        original_text="Enviar propuesta",
        normalized_text="enviar propuesta",
        source_intent_id="i1",
        status=status,
        task_id="t1",
        snooze_count=snooze_count,
    )


def _svc(tasks, event_fail=False):
    task_repo = _TaskRepo(tasks)
    event_repo = _EventRepo(fail=event_fail)
    cycle_event_repo = _CycleEventRepo()
    svc = ResponseService(
        task_repo=task_repo,
        event_repo=event_repo,
        cycle_event_repo=cycle_event_repo,
        cycle_repo=_CycleRepo(),
        decision_service=_DecisionService(),
    )
    return svc, task_repo, event_repo, cycle_event_repo


# ---------------------------------------------------------------------------
# US-08 Scenario: Evento TASK_DONE registrado al completar tarea
# ---------------------------------------------------------------------------

def test_task_done_event_recorded():
    """
    Given usuario confirma Done
    Then InteractionEvent con TASK_DONE, task_id, user_id, correlation_id
    And cycle event registrado en ppai-cycles
    """
    task = _task()
    svc, _, event_repo, cycle_event_repo = _svc([task])

    svc.confirm_done("u1", "t1")

    assert len(event_repo.events) == 1
    evt = event_repo.events[0]
    assert evt.event_type == "TASK_DONE"
    assert evt.task_id == "t1"
    assert evt.user_id == "u1"
    assert evt.correlation_id  # has cycle correlation

    # Cycle event also recorded
    cycle_events = [e for e in cycle_event_repo.events if e["event_type"] == "TASK_DONE"]
    assert len(cycle_events) == 1


# ---------------------------------------------------------------------------
# US-08 Scenario: Evento TASK_SNOOZED registrado al posponer tarea
# ---------------------------------------------------------------------------

def test_task_snoozed_event_recorded():
    """
    Given usuario presiona Snooze
    Then InteractionEvent con TASK_SNOOZED, metadata incluye snooze_count
    """
    task = _task()
    svc, _, event_repo, _ = _svc([task])

    svc.handle_snooze("u1", "t1")

    assert len(event_repo.events) == 1
    evt = event_repo.events[0]
    assert evt.event_type == "TASK_SNOOZED"
    assert evt.metadata["snooze_count"] == 1


# ---------------------------------------------------------------------------
# US-08 Scenario: Evento TASK_CLARIFIED registrado al solicitar aclaración
# ---------------------------------------------------------------------------

def test_task_clarified_event_recorded():
    """
    Given usuario presiona Clarify
    Then InteractionEvent con TASK_CLARIFIED
    """
    task = _task()
    svc, _, event_repo, _ = _svc([task])

    svc.handle_clarify("u1", "t1")

    assert len(event_repo.events) == 1
    assert event_repo.events[0].event_type == "TASK_CLARIFIED"


# ---------------------------------------------------------------------------
# US-08 Scenario: Evento TASK_CLARIFY_RESOLVED al responder aclaración
# ---------------------------------------------------------------------------

def test_task_clarify_resolved_event_recorded():
    """
    Given tarea en NEEDS_CLARIFICATION, usuario responde con texto
    Then InteractionEvent con TASK_CLARIFY_RESOLVED, metadata con texto
    """
    task = _task(status=TaskStatus.NEEDS_CLARIFICATION)
    svc, _, event_repo, _ = _svc([task])

    svc.handle_clarify_response("u1", "Necesito cotizar")

    assert len(event_repo.events) == 1
    evt = event_repo.events[0]
    assert evt.event_type == "TASK_CLARIFY_RESOLVED"
    assert evt.metadata["response_text"] == "Necesito cotizar"


# ---------------------------------------------------------------------------
# US-08 Scenario: Fallo en registro de evento — best-effort sin rollback
# ---------------------------------------------------------------------------

def test_event_failure_does_not_rollback_transition():
    """
    Given repositorio de eventos falla
    When usuario confirma Done
    Then tarea → DONE (no rollback), warning logged
    """
    task = _task()
    svc, task_repo, event_repo, _ = _svc([task], event_fail=True)

    result = svc.confirm_done("u1", "t1")

    assert result.success is True
    assert result.new_status == TaskStatus.DONE
    assert task_repo.saved[-1].status == TaskStatus.DONE
    assert len(event_repo.events) == 0  # failed but transition OK

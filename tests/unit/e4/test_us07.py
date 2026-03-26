"""
BDD acceptance tests for US-07: Cierre inmediato de estado por respuesta de usuario.
Scenarios from tests/features/e4/us07.feature
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.domain.entities import ExecutionCycle
from ppai.respond.application.response_service import ResponseService
from ppai.respond.domain.entities import InteractionEvent
from ppai.respond.domain.value_objects import ResponseAction, SNOOZE_COOLDOWN

NOW = datetime(2026, 3, 26, 14, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Minimal fakes (same pattern as test_response_service.py)
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
    def __init__(self):
        self.events = []

    def append(self, event):
        self.events.append(event)


class _CycleEventRepo:
    def __init__(self):
        self.events = []

    def record_nudge_event(self, cycle_id, event_type, metadata):
        self.events.append({"cycle_id": cycle_id, "event_type": event_type})

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


def _task(status=TaskStatus.NUDGED, snooze_count=0, user_id="u1"):
    return TaskState(
        user_id=user_id,
        original_text="Enviar propuesta",
        normalized_text="enviar propuesta",
        source_intent_id="i1",
        status=status,
        task_id="t1",
        snooze_count=snooze_count,
    )


def _svc(tasks, event_fail=False):
    task_repo = _TaskRepo(tasks)
    event_repo = _EventRepo()
    decision_svc = _DecisionService()
    svc = ResponseService(
        task_repo=task_repo,
        event_repo=event_repo,
        cycle_event_repo=_CycleEventRepo(),
        cycle_repo=_CycleRepo(),
        decision_service=decision_svc,
    )
    return svc, task_repo, event_repo, decision_svc


# ---------------------------------------------------------------------------
# US-07 Scenario: Done con confirmación — flujo completo
# ---------------------------------------------------------------------------

def test_done_with_confirmation_full_flow():
    """
    Given usuario con tarea nudged
    When presiona Done → confirma Sí
    Then tarea → DONE, completed_at set, cache invalidado
    """
    task = _task()
    svc, task_repo, event_repo, decision_svc = _svc([task])

    # Step 1: handle_done → requires confirmation
    r1 = svc.handle_done("u1", "t1")
    assert r1.requires_confirmation is True

    # Step 2: confirm_done → DONE
    r2 = svc.confirm_done("u1", "t1")
    assert r2.success is True
    assert r2.new_status == TaskStatus.DONE

    saved = task_repo.saved[-1]
    assert saved.status == TaskStatus.DONE
    assert saved.completed_at is not None
    assert "u1" in decision_svc.invalidated


# ---------------------------------------------------------------------------
# US-07 Scenario: Done cancelado — sin cambio de estado
# ---------------------------------------------------------------------------

def test_done_cancelled_no_state_change():
    """
    Given usuario con tarea nudged
    When presiona Done → responde No
    Then tarea permanece en estado original, sin evento
    """
    task = _task()
    svc, task_repo, event_repo, _ = _svc([task])

    r = svc.handle_done("u1", "t1")
    assert r.requires_confirmation is True

    # User says No — no confirm_done call, no state change
    current = task_repo.get_by_id("u1", "t1")
    assert current.status == TaskStatus.NUDGED
    assert len(event_repo.events) == 0


# ---------------------------------------------------------------------------
# US-07 Scenario: Snooze con cooldown de 1 hora
# ---------------------------------------------------------------------------

def test_snooze_with_cooldown():
    """
    Given usuario con tarea nudged
    When presiona Snooze
    Then tarea → SNOOZED, snooze_count++, snoozed_until = now+1h, cache invalidado
    """
    task = _task()
    svc, task_repo, _, decision_svc = _svc([task])

    r = svc.handle_snooze("u1", "t1")
    assert r.success is True
    assert r.new_status == TaskStatus.SNOOZED

    saved = task_repo.saved[-1]
    assert saved.snooze_count == 1
    assert saved.snoozed_until is not None
    assert "u1" in decision_svc.invalidated


# ---------------------------------------------------------------------------
# US-07 Scenario: Snooze limit alcanzado — auto-clarify
# ---------------------------------------------------------------------------

def test_snooze_limit_triggers_auto_clarify():
    """
    Given tarea con snooze_count=3
    When presiona Snooze
    Then mensaje "Ya pospusiste esta tarea 3 veces", tarea → NEEDS_CLARIFICATION
    """
    task = _task(snooze_count=3)
    svc, task_repo, *_ = _svc([task])

    r = svc.handle_snooze("u1", "t1")
    assert r.success is True
    assert "3 veces" in r.message
    assert r.new_status == TaskStatus.NEEDS_CLARIFICATION
    assert task_repo.saved[-1].status == TaskStatus.NEEDS_CLARIFICATION


# ---------------------------------------------------------------------------
# US-07 Scenario: Clarify — flujo de aclaración con respuesta de texto
# ---------------------------------------------------------------------------

def test_clarify_flow_with_text_response():
    """
    Given usuario con tarea nudged
    When presiona Clarify → responde con texto libre
    Then tarea → NEEDS_CLARIFICATION → PENDING, normalized_text actualizado, snooze_count=0
    """
    task = _task(snooze_count=2)
    svc, task_repo, *_ = _svc([task])

    # Clarify
    r1 = svc.handle_clarify("u1", "t1")
    assert r1.new_status == TaskStatus.NEEDS_CLARIFICATION

    # Text response
    r2 = svc.handle_clarify_response("u1", "Necesito cotizar primero")
    assert r2.success is True
    assert r2.new_status == TaskStatus.PENDING

    saved = task_repo.saved[-1]
    assert "Aclarado: Necesito cotizar primero" in saved.normalized_text
    assert saved.snooze_count == 0


# ---------------------------------------------------------------------------
# US-07 Scenario: Idempotencia — doble press en Done
# ---------------------------------------------------------------------------

def test_idempotent_done_callback():
    """
    Given tarea ya en DONE
    When presiona Done de nuevo
    Then mensaje informativo, sin cambio de estado
    """
    task = _task(status=TaskStatus.DONE)
    svc, task_repo, *_ = _svc([task])

    r = svc.handle_done("u1", "t1")
    assert r.success is True
    assert "ya fue completada" in r.message
    assert len(task_repo.saved) == 0


# ---------------------------------------------------------------------------
# US-07 Scenario: Autorización — callback de otro usuario rechazado
# ---------------------------------------------------------------------------

def test_unauthorized_callback_rejected():
    """
    Given tarea pertenece a u1
    When u2 presiona Done
    Then mensaje "No tienes permiso", sin cambio de estado
    """
    task = _task(user_id="u1")
    repo = _TaskRepo([task])
    repo._tasks[("u2", "t1")] = task  # simulate cross-user lookup
    svc = ResponseService(
        task_repo=repo,
        event_repo=_EventRepo(),
        cycle_event_repo=_CycleEventRepo(),
        cycle_repo=_CycleRepo(),
        decision_service=_DecisionService(),
    )

    r = svc.handle_done("u2", "t1")
    assert r.success is False
    assert "No tienes permiso" in r.message

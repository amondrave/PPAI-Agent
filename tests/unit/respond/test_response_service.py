"""Unit tests for ResponseService (Step 6 — US-07, US-08)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.domain.entities import ExecutionCycle
from ppai.respond.application.response_service import ResponseService
from ppai.respond.domain.entities import InteractionEvent
from ppai.respond.domain.value_objects import ResponseAction

NOW = datetime(2026, 3, 26, 14, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Minimal fakes
# ---------------------------------------------------------------------------

class _TaskRepo:
    def __init__(self, tasks: list[TaskState] | None = None):
        self._tasks = {(t.user_id, t.task_id): t for t in (tasks or [])}
        self.saved: list[TaskState] = []

    def get_by_id(self, user_id: str, task_id: str) -> TaskState | None:
        return self._tasks.get((user_id, task_id))

    def save(self, task: TaskState) -> None:
        self.saved.append(task)
        self._tasks[(task.user_id, task.task_id)] = task

    def count_active(self, user_id: str) -> int:
        return 0

    def list_by_status(self, user_id: str, status: TaskStatus) -> list[TaskState]:
        return [t for t in self._tasks.values() if t.user_id == user_id and t.status == status]


class _EventRepo:
    def __init__(self, fail: bool = False):
        self.events: list[InteractionEvent] = []
        self._fail = fail

    def append(self, event: InteractionEvent) -> None:
        if self._fail:
            raise RuntimeError("event write failed")
        self.events.append(event)


class _CycleEventRepo:
    def __init__(self):
        self.events: list[dict] = []

    def get_active(self, user_id, for_date):
        return None

    def create(self, cycle):
        pass

    def record_nudge_event(self, cycle_id, event_type, metadata):
        self.events.append({"cycle_id": cycle_id, "event_type": event_type, **metadata})

    def get_nudge_count(self, cycle_id):
        return 0

    def get_last_activity_at(self, user_id):
        return None


class _CycleRepo:
    def __init__(self, cycle: ExecutionCycle | None = None):
        self._cycle = cycle

    def get_active(self, user_id, date):
        return self._cycle

    def save(self, cycle):
        self._cycle = cycle

    def update_top3(self, cycle_id, top3_task_ids):
        pass

    def increment_reorders(self, cycle_id):
        pass


class _DecisionService:
    def __init__(self):
        self.invalidated: list[str] = []

    def invalidate_cache(self, user_id: str) -> None:
        self.invalidated.append(user_id)


def _make_task(
    task_id="t1",
    user_id="u1",
    status=TaskStatus.NUDGED,
    snooze_count=0,
) -> TaskState:
    return TaskState(
        user_id=user_id,
        original_text="Enviar propuesta",
        normalized_text="enviar propuesta",
        source_intent_id="i1",
        status=status,
        task_id=task_id,
        snooze_count=snooze_count,
    )


def _make_service(
    tasks: list[TaskState] | None = None,
    event_fail: bool = False,
    cycle: ExecutionCycle | None = None,
):
    task_repo = _TaskRepo(tasks)
    event_repo = _EventRepo(fail=event_fail)
    cycle_event_repo = _CycleEventRepo()
    cycle_repo = _CycleRepo(cycle or ExecutionCycle(user_id="u1", date="2026-03-26"))
    decision_svc = _DecisionService()
    svc = ResponseService(
        task_repo=task_repo,
        event_repo=event_repo,
        cycle_event_repo=cycle_event_repo,
        cycle_repo=cycle_repo,
        decision_service=decision_svc,
    )
    return svc, task_repo, event_repo, cycle_event_repo, decision_svc


# ---------------------------------------------------------------------------
# handle_done: requires_confirmation=True
# ---------------------------------------------------------------------------

class TestHandleDone:
    def test_happy_path_requires_confirmation(self):
        task = _make_task()
        svc, *_ = _make_service([task])
        result = svc.handle_done("u1", "t1")

        assert result.success is True
        assert result.requires_confirmation is True
        assert "Confirmas" in result.message

    def test_idempotent_already_done(self):
        task = _make_task(status=TaskStatus.DONE)
        svc, *_ = _make_service([task])
        result = svc.handle_done("u1", "t1")

        assert result.success is True
        assert "ya fue completada" in result.message


# ---------------------------------------------------------------------------
# confirm_done
# ---------------------------------------------------------------------------

class TestConfirmDone:
    def test_happy_path(self):
        task = _make_task()
        svc, task_repo, event_repo, cycle_event_repo, decision_svc = _make_service([task])
        result = svc.confirm_done("u1", "t1")

        assert result.success is True
        assert result.new_status == TaskStatus.DONE
        assert task_repo.saved[-1].status == TaskStatus.DONE
        assert task_repo.saved[-1].completed_at is not None
        assert len(event_repo.events) == 1
        assert event_repo.events[0].event_type == "TASK_DONE"
        assert "u1" in decision_svc.invalidated

    def test_idempotent_already_done(self):
        task = _make_task(status=TaskStatus.DONE)
        svc, task_repo, *_ = _make_service([task])
        result = svc.confirm_done("u1", "t1")

        assert result.success is True
        assert "ya fue completada" in result.message
        assert len(task_repo.saved) == 0  # no save


# ---------------------------------------------------------------------------
# handle_snooze
# ---------------------------------------------------------------------------

class TestHandleSnooze:
    def test_happy_path(self):
        task = _make_task()
        svc, task_repo, event_repo, _, decision_svc = _make_service([task])
        result = svc.handle_snooze("u1", "t1")

        assert result.success is True
        assert result.new_status == TaskStatus.SNOOZED
        saved = task_repo.saved[-1]
        assert saved.snooze_count == 1
        assert saved.snoozed_until is not None
        assert "1/3" in result.message
        assert event_repo.events[0].event_type == "TASK_SNOOZED"
        assert "u1" in decision_svc.invalidated

    def test_limit_reached_auto_clarify(self):
        task = _make_task(snooze_count=3)
        svc, task_repo, event_repo, *_ = _make_service([task])
        result = svc.handle_snooze("u1", "t1")

        assert result.success is True
        assert result.new_status == TaskStatus.NEEDS_CLARIFICATION
        assert "3 veces" in result.message
        assert task_repo.saved[-1].status == TaskStatus.NEEDS_CLARIFICATION

    def test_idempotent_already_snoozed(self):
        task = _make_task(status=TaskStatus.SNOOZED)
        svc, task_repo, *_ = _make_service([task])
        result = svc.handle_snooze("u1", "t1")

        assert result.success is True
        assert "ya fue pospuesta" in result.message
        assert len(task_repo.saved) == 0


# ---------------------------------------------------------------------------
# handle_clarify
# ---------------------------------------------------------------------------

class TestHandleClarify:
    def test_happy_path(self):
        task = _make_task()
        svc, task_repo, event_repo, _, decision_svc = _make_service([task])
        result = svc.handle_clarify("u1", "t1")

        assert result.success is True
        assert result.new_status == TaskStatus.NEEDS_CLARIFICATION
        assert task_repo.saved[-1].status == TaskStatus.NEEDS_CLARIFICATION
        assert event_repo.events[0].event_type == "TASK_CLARIFIED"
        assert "u1" in decision_svc.invalidated


# ---------------------------------------------------------------------------
# handle_clarify_response
# ---------------------------------------------------------------------------

class TestHandleClarifyResponse:
    def test_happy_path(self):
        task = _make_task(status=TaskStatus.NEEDS_CLARIFICATION, snooze_count=2)
        svc, task_repo, event_repo, _, decision_svc = _make_service([task])
        result = svc.handle_clarify_response("u1", "Necesito cotizar primero")

        assert result is not None
        assert result.success is True
        assert result.new_status == TaskStatus.PENDING
        saved = task_repo.saved[-1]
        assert "Aclarado: Necesito cotizar primero" in saved.normalized_text
        assert saved.snooze_count == 0
        assert event_repo.events[0].event_type == "TASK_CLARIFY_RESOLVED"
        assert "u1" in decision_svc.invalidated

    def test_no_task_needing_clarification(self):
        task = _make_task()  # status=NUDGED, not NEEDS_CLARIFICATION
        svc, *_ = _make_service([task])
        result = svc.handle_clarify_response("u1", "algo")

        assert result is None


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

class TestAuthorization:
    def test_unauthorized_callback_rejected(self):
        """BR-RSP-07: callback user != task owner → rejected."""
        task = _make_task(user_id="u1")
        # Simulate repo returning task even when queried by different user
        repo = _TaskRepo([task])
        repo._tasks[("u2", "t1")] = task  # cross-user access
        svc = ResponseService(
            task_repo=repo,
            event_repo=_EventRepo(),
            cycle_event_repo=_CycleEventRepo(),
            cycle_repo=_CycleRepo(ExecutionCycle(user_id="u1", date="2026-03-26")),
            decision_service=_DecisionService(),
        )
        result = svc.handle_done("u2", "t1")

        assert result.success is False
        assert "No tienes permiso" in result.message


# ---------------------------------------------------------------------------
# Event recording failure — best-effort
# ---------------------------------------------------------------------------

class TestEventRecordingFailure:
    def test_transition_not_reverted_on_event_failure(self):
        task = _make_task()
        svc, task_repo, event_repo, *_ = _make_service([task], event_fail=True)
        result = svc.confirm_done("u1", "t1")

        assert result.success is True
        assert result.new_status == TaskStatus.DONE
        assert task_repo.saved[-1].status == TaskStatus.DONE
        assert len(event_repo.events) == 0  # event failed but transition OK

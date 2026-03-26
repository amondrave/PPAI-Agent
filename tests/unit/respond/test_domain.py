"""Unit tests for UOW-04 Domain Layer — TaskState transitions, InteractionEvent, TransitionResult."""

from datetime import datetime, timedelta, timezone

import pytest

from ppai.capture.domain.entities import TaskState, MAX_SNOOZE_COUNT
from ppai.capture.domain.value_objects import TaskStatus
from ppai.respond.domain.entities import InteractionEvent, TransitionResult
from ppai.respond.domain.exceptions import InvalidTransitionError
from ppai.respond.domain.value_objects import ResponseAction, SNOOZE_COOLDOWN


NOW = datetime(2026, 3, 26, 12, 0, 0, tzinfo=timezone.utc)


def _pending_task(**overrides) -> TaskState:
    defaults = dict(
        user_id="u1",
        original_text="Comprar leche",
        normalized_text="comprar leche",
        source_intent_id="i1",
    )
    defaults.update(overrides)
    t = TaskState(**defaults)
    t.transition_to_pending()
    return t


# ── TaskState.transition_to_done ──────────────────────────────────────


class TestTransitionToDone:
    @pytest.mark.parametrize("status", [TaskStatus.PENDING, TaskStatus.PRIORITIZED, TaskStatus.NUDGED])
    def test_valid_status_transitions_to_done(self, status):
        task = _pending_task()
        task.status = status
        task.transition_to_done(NOW)
        assert task.status == TaskStatus.DONE
        assert task.completed_at == NOW
        assert task.updated_at == NOW

    @pytest.mark.parametrize("status", [
        TaskStatus.CAPTURED, TaskStatus.DONE, TaskStatus.SNOOZED,
        TaskStatus.NEEDS_CLARIFICATION, TaskStatus.CLARIFYING,
    ])
    def test_invalid_status_raises(self, status):
        task = _pending_task()
        task.status = status
        with pytest.raises(InvalidTransitionError, match="Cannot transition from"):
            task.transition_to_done(NOW)


# ── TaskState.transition_to_snoozed ──────────────────────────────────


class TestTransitionToSnoozed:
    def test_happy_path(self):
        task = _pending_task()
        task.transition_to_snoozed(NOW, SNOOZE_COOLDOWN)
        assert task.status == TaskStatus.SNOOZED
        assert task.snooze_count == 1
        assert task.snoozed_until == NOW + SNOOZE_COOLDOWN
        assert task.updated_at == NOW

    def test_increments_snooze_count(self):
        task = _pending_task(snooze_count=1)
        task.transition_to_snoozed(NOW, SNOOZE_COOLDOWN)
        assert task.snooze_count == 2

    def test_snooze_limit_reached_raises(self):
        task = _pending_task(snooze_count=3)
        with pytest.raises(InvalidTransitionError, match="Snooze limit reached"):
            task.transition_to_snoozed(NOW, SNOOZE_COOLDOWN)

    @pytest.mark.parametrize("status", [
        TaskStatus.CAPTURED, TaskStatus.DONE, TaskStatus.NEEDS_CLARIFICATION,
    ])
    def test_invalid_status_raises(self, status):
        task = _pending_task()
        task.status = status
        with pytest.raises(InvalidTransitionError):
            task.transition_to_snoozed(NOW, SNOOZE_COOLDOWN)


# ── TaskState.transition_to_needs_clarification ──────────────────────


class TestTransitionToNeedsClarification:
    @pytest.mark.parametrize("status", [
        TaskStatus.PENDING, TaskStatus.PRIORITIZED, TaskStatus.NUDGED, TaskStatus.SNOOZED,
    ])
    def test_valid_status(self, status):
        task = _pending_task()
        task.status = status
        task.transition_to_needs_clarification(NOW)
        assert task.status == TaskStatus.NEEDS_CLARIFICATION
        assert task.updated_at == NOW

    @pytest.mark.parametrize("status", [
        TaskStatus.CAPTURED, TaskStatus.DONE, TaskStatus.NEEDS_CLARIFICATION,
    ])
    def test_invalid_status_raises(self, status):
        task = _pending_task()
        task.status = status
        with pytest.raises(InvalidTransitionError):
            task.transition_to_needs_clarification(NOW)


# ── TaskState.resolve_clarification ──────────────────────────────────


class TestResolveClarification:
    def test_happy_path(self):
        task = _pending_task(snooze_count=2)
        task.transition_to_needs_clarification(NOW)
        later = NOW + timedelta(minutes=5)
        task.resolve_clarification("texto actualizado", later)
        assert task.status == TaskStatus.PENDING
        assert task.normalized_text == "texto actualizado"
        assert task.snooze_count == 0
        assert task.snoozed_until is None
        assert task.updated_at == later

    def test_not_in_needs_clarification_raises(self):
        task = _pending_task()
        with pytest.raises(InvalidTransitionError, match="Cannot resolve clarification"):
            task.resolve_clarification("texto", NOW)


# ── TaskState.is_snooze_limit_reached ────────────────────────────────


class TestIsSnoozeLimit:
    def test_below_limit(self):
        task = _pending_task(snooze_count=2)
        assert task.is_snooze_limit_reached() is False

    def test_at_limit(self):
        task = _pending_task(snooze_count=MAX_SNOOZE_COUNT)
        assert task.is_snooze_limit_reached() is True

    def test_above_limit(self):
        task = _pending_task(snooze_count=MAX_SNOOZE_COUNT + 1)
        assert task.is_snooze_limit_reached() is True


# ── InteractionEvent ─────────────────────────────────────────────────


class TestInteractionEvent:
    def test_construction(self):
        evt = InteractionEvent(
            user_id="u1",
            task_id="t1",
            event_type="DONE",
            correlation_id="cycle-1",
            metadata={"action": "done"},
        )
        assert evt.user_id == "u1"
        assert evt.task_id == "t1"
        assert evt.event_type == "DONE"
        assert evt.correlation_id == "cycle-1"
        assert evt.metadata == {"action": "done"}
        assert evt.event_id  # auto-generated
        assert evt.timestamp  # auto-generated

    def test_defaults(self):
        evt = InteractionEvent(
            user_id="u1", task_id="t1", event_type="SNOOZE", correlation_id="c1"
        )
        assert evt.metadata == {}


# ── TransitionResult ─────────────────────────────────────────────────


class TestTransitionResult:
    def test_without_confirmation(self):
        r = TransitionResult(
            success=True,
            task_id="t1",
            action=ResponseAction.DONE,
            message="Tarea completada",
            previous_status=TaskStatus.PENDING,
            new_status=TaskStatus.DONE,
        )
        assert r.success is True
        assert r.requires_confirmation is False

    def test_with_confirmation(self):
        r = TransitionResult(
            success=True,
            task_id="t1",
            action=ResponseAction.DONE,
            message="¿Confirmas?",
            requires_confirmation=True,
            previous_status=TaskStatus.PENDING,
            new_status=None,
        )
        assert r.requires_confirmation is True
        assert r.new_status is None

    def test_failed_result(self):
        r = TransitionResult(
            success=False,
            task_id="t1",
            action=ResponseAction.SNOOZE,
            message="No autorizado",
        )
        assert r.success is False
        assert r.previous_status is None
        assert r.new_status is None

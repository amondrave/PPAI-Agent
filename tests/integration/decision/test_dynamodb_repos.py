"""Integration tests for UOW-02 DynamoDB repositories (moto mock).

Covers: DynamoDBCycleRepository + DynamoDBTaskStateRepository.list_pending
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.decision.domain.entities import ExecutionCycle
from ppai.decision.domain.exceptions import CycleConflictError
from ppai.decision.domain.value_objects import CycleStatus
from ppai.decision.infrastructure.dynamodb_cycle_repo import DynamoDBCycleRepository

USER = "user-integ-01"
TODAY = "2026-03-21"
NOW = datetime(2026, 3, 21, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def cycle_repo(dynamodb_resource):
    table = dynamodb_resource.Table("ppai-cycles")
    return DynamoDBCycleRepository(table)


@pytest.fixture()
def task_repo(dynamodb_resource):
    table = dynamodb_resource.Table("ppai-tasks")
    return DynamoDBTaskStateRepository(table)


def make_task(user_id: str = USER, status: TaskStatus = TaskStatus.PENDING, snooze_count: int = 0) -> TaskState:
    task = TaskState(
        user_id=user_id,
        original_text="test task",
        normalized_text="Test task",
        source_intent_id="intent-1",
        status=status,
        snooze_count=snooze_count,
    )
    return task


# ---------------------------------------------------------------------------
# DynamoDBCycleRepository
# ---------------------------------------------------------------------------

class TestDynamoDBCycleRepository:
    def test_save_and_get_active_cycle(self, cycle_repo):
        cycle = ExecutionCycle(user_id=USER, date=TODAY)
        cycle_repo.save(cycle)

        found = cycle_repo.get_active(USER, TODAY)
        assert found is not None
        assert found.cycle_id == cycle.cycle_id
        assert found.user_id == USER
        assert found.date == TODAY
        assert found.status == CycleStatus.ACTIVE

    def test_get_active_returns_none_if_not_exists(self, cycle_repo):
        result = cycle_repo.get_active("nonexistent-user", TODAY)
        assert result is None

    def test_get_active_returns_none_for_closed_cycle(self, cycle_repo):
        cycle = ExecutionCycle(user_id=USER, date=TODAY, status=CycleStatus.CLOSED)
        cycle_repo.save(cycle)

        result = cycle_repo.get_active(USER, TODAY)
        assert result is None

    def test_save_prevents_duplicate_cycle(self, cycle_repo):
        cycle = ExecutionCycle(user_id=USER, date=TODAY)
        cycle_repo.save(cycle)

        duplicate = ExecutionCycle(cycle_id=cycle.cycle_id, user_id=USER, date=TODAY)
        with pytest.raises(CycleConflictError):
            cycle_repo.save(duplicate)

    def test_update_top3_sets_task_ids(self, cycle_repo):
        cycle = ExecutionCycle(user_id=USER, date=TODAY)
        cycle_repo.save(cycle)

        task_ids = ["t-1", "t-2", "t-3"]
        cycle_repo.update_top3(cycle.cycle_id, task_ids)

        found = cycle_repo.get_active(USER, TODAY)
        assert found.top3_task_ids == task_ids

    def test_update_top3_replaces_previous_ids(self, cycle_repo):
        cycle = ExecutionCycle(user_id=USER, date=TODAY)
        cycle_repo.save(cycle)

        cycle_repo.update_top3(cycle.cycle_id, ["old-1", "old-2"])
        cycle_repo.update_top3(cycle.cycle_id, ["new-1"])

        found = cycle_repo.get_active(USER, TODAY)
        assert found.top3_task_ids == ["new-1"]

    def test_increment_reorders(self, cycle_repo):
        cycle = ExecutionCycle(user_id=USER, date=TODAY)
        cycle_repo.save(cycle)

        cycle_repo.increment_reorders(cycle.cycle_id)
        cycle_repo.increment_reorders(cycle.cycle_id)

        found = cycle_repo.get_active(USER, TODAY)
        assert found.manual_reorders == 2

    def test_roundtrip_preserves_fields(self, cycle_repo):
        cycle = ExecutionCycle(user_id=USER, date=TODAY)
        cycle_repo.save(cycle)

        found = cycle_repo.get_active(USER, TODAY)
        assert found.manual_reorders == 0
        assert found.top3_task_ids == []
        assert found.closed_at is None


# ---------------------------------------------------------------------------
# DynamoDBTaskStateRepository.list_pending (UOW-01 extension)
# ---------------------------------------------------------------------------

class TestTaskRepoListPending:
    def test_list_pending_returns_pending_tasks(self, task_repo):
        t1 = make_task(status=TaskStatus.PENDING)
        t2 = make_task(status=TaskStatus.PENDING)
        task_repo.save(t1)
        task_repo.save(t2)

        results = task_repo.list_pending(USER)
        result_ids = {t.task_id for t in results}
        assert t1.task_id in result_ids
        assert t2.task_id in result_ids

    def test_list_pending_excludes_non_pending(self, task_repo):
        pending = make_task(status=TaskStatus.PENDING)
        captured = make_task(status=TaskStatus.CAPTURED)
        prioritized = make_task(status=TaskStatus.PRIORITIZED)
        task_repo.save(pending)
        task_repo.save(captured)
        task_repo.save(prioritized)

        results = task_repo.list_pending(USER)
        result_ids = {t.task_id for t in results}
        assert pending.task_id in result_ids
        assert captured.task_id not in result_ids
        assert prioritized.task_id not in result_ids

    def test_list_pending_empty_for_new_user(self, task_repo):
        results = task_repo.list_pending("brand-new-user")
        assert results == []

    def test_list_pending_preserves_snooze_count(self, task_repo):
        task = make_task(status=TaskStatus.PENDING, snooze_count=3)
        task_repo.save(task)

        results = task_repo.list_pending(USER)
        found = next(t for t in results if t.task_id == task.task_id)
        assert found.snooze_count == 3

    def test_list_pending_snooze_count_defaults_to_zero(self, task_repo):
        # Task saved without explicit snooze_count
        task = make_task(status=TaskStatus.PENDING, snooze_count=0)
        task_repo.save(task)

        results = task_repo.list_pending(USER)
        found = next(t for t in results if t.task_id == task.task_id)
        assert found.snooze_count == 0

    def test_list_pending_scoped_to_user(self, task_repo):
        alice_task = make_task(user_id="alice", status=TaskStatus.PENDING)
        bob_task = make_task(user_id="bob", status=TaskStatus.PENDING)
        task_repo.save(alice_task)
        task_repo.save(bob_task)

        alice_results = task_repo.list_pending("alice")
        assert all(t.user_id == "alice" for t in alice_results)
        assert bob_task.task_id not in {t.task_id for t in alice_results}

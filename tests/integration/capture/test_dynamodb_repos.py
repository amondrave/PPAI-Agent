from __future__ import annotations

import time

import pytest

from ppai.capture.domain.entities import CaptureEvent, TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.capture.infrastructure.dynamodb_event_repo import DynamoDBEventRepository
from ppai.capture.infrastructure.dynamodb_dedup_repo import DynamoDBDedupRepository
from ppai.shared.infrastructure.config import Settings


@pytest.fixture()
def task_repo(dynamodb_resource):
    table = dynamodb_resource.Table("ppai-tasks")
    return DynamoDBTaskStateRepository(table)


@pytest.fixture()
def event_repo(dynamodb_resource):
    table = dynamodb_resource.Table("ppai-events")
    return DynamoDBEventRepository(table)


@pytest.fixture()
def dedup_repo(dynamodb_resource):
    table = dynamodb_resource.Table("ppai-dedup")
    settings = Settings(telegram_bot_token="fake-token", dedup_window_seconds=300)
    return DynamoDBDedupRepository(table, settings)


# -- TaskStateRepository ------------------------------------------------------


class TestTaskStateRepository:
    def test_save_and_get_by_id(self, task_repo):
        task = TaskState(
            user_id="u1",
            original_text="comprar leche",
            normalized_text="comprar leche",
            source_intent_id="i1",
            tag="compras",
        )
        task.transition_to_pending()

        task_repo.save(task)
        result = task_repo.get_by_id("u1", task.task_id)

        assert result is not None
        assert result.user_id == "u1"
        assert result.original_text == "comprar leche"
        assert result.normalized_text == "comprar leche"
        assert result.tag == "compras"
        assert result.status == TaskStatus.PENDING
        assert result.source_intent_id == "i1"

    def test_get_by_id_not_found(self, task_repo):
        result = task_repo.get_by_id("u1", "nonexistent")
        assert result is None

    def test_save_without_optional_fields(self, task_repo):
        task = TaskState(
            user_id="u1",
            original_text="test",
            normalized_text="test",
            source_intent_id="i1",
        )
        task_repo.save(task)
        result = task_repo.get_by_id("u1", task.task_id)

        assert result is not None
        assert result.tag is None
        assert result.deadline is None

    def test_count_active_empty(self, task_repo):
        count = task_repo.count_active("u1")
        assert count == 0

    def test_count_active_with_tasks(self, task_repo):
        for i in range(3):
            task = TaskState(
                user_id="u1",
                original_text=f"task {i}",
                normalized_text=f"task {i}",
                source_intent_id="i1",
            )
            task.transition_to_pending()
            task_repo.save(task)

        assert task_repo.count_active("u1") == 3

    def test_count_active_excludes_done(self, task_repo):
        pending = TaskState(
            user_id="u1",
            original_text="active",
            normalized_text="active",
            source_intent_id="i1",
        )
        pending.transition_to_pending()
        task_repo.save(pending)

        done = TaskState(
            user_id="u1",
            original_text="done",
            normalized_text="done",
            source_intent_id="i1",
            status=TaskStatus.DONE,
        )
        task_repo.save(done)

        assert task_repo.count_active("u1") == 1

    def test_count_active_scoped_to_user(self, task_repo):
        for uid in ("u1", "u2"):
            task = TaskState(
                user_id=uid,
                original_text="task",
                normalized_text="task",
                source_intent_id="i1",
            )
            task.transition_to_pending()
            task_repo.save(task)

        assert task_repo.count_active("u1") == 1
        assert task_repo.count_active("u2") == 1


# -- EventRepository ----------------------------------------------------------


class TestEventRepository:
    def test_append(self, event_repo, dynamodb_resource):
        event = CaptureEvent(
            task_id="t1",
            user_id="u1",
            original_text="comprar leche",
            correlation_id="c1",
        )
        event_repo.append(event)

        table = dynamodb_resource.Table("ppai-events")
        resp = table.scan()
        assert resp["Count"] == 1
        item = resp["Items"][0]
        assert item["userId"] == "u1"
        assert item["eventType"] == "INTENT_CAPTURED"
        assert item["taskId"] == "t1"
        assert item["correlationId"] == "c1"

    def test_append_multiple(self, event_repo, dynamodb_resource):
        for i in range(3):
            event = CaptureEvent(
                task_id=f"t{i}",
                user_id="u1",
                original_text=f"task {i}",
                correlation_id="c1",
            )
            event_repo.append(event)

        table = dynamodb_resource.Table("ppai-events")
        resp = table.scan()
        assert resp["Count"] == 3


# -- DedupRepository ----------------------------------------------------------


class TestDedupRepository:
    def test_exists_not_found(self, dedup_repo):
        assert dedup_repo.exists("u1", "new text") is False

    def test_record_then_exists(self, dedup_repo):
        dedup_repo.record("u1", "comprar leche", "t1")
        assert dedup_repo.exists("u1", "comprar leche") is True

    def test_different_text_not_found(self, dedup_repo):
        dedup_repo.record("u1", "comprar leche", "t1")
        assert dedup_repo.exists("u1", "llamar doctor") is False

    def test_different_user_not_found(self, dedup_repo):
        dedup_repo.record("u1", "comprar leche", "t1")
        assert dedup_repo.exists("u2", "comprar leche") is False

    def test_expired_record_not_found(self, dedup_repo, dynamodb_resource, monkeypatch):
        dedup_repo.record("u1", "comprar leche", "t1")

        future = int(time.time()) + 600
        monkeypatch.setattr(time, "time", lambda: future)

        assert dedup_repo.exists("u1", "comprar leche") is False

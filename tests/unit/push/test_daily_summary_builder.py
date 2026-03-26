"""Unit tests for DailySummaryBuilder."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.push.application.daily_summary_builder import DailySummaryBuilder


def _make_task(task_id, status, completed_at=None, normalized_text="task"):
    t = MagicMock(spec=TaskState)
    t.task_id = task_id
    t.normalized_text = normalized_text
    t.status = status
    t.completed_at = completed_at
    return t


class TestDailySummaryBuilder:
    def test_completed_today_included(self):
        today = date(2026, 3, 27)
        task_repo = MagicMock()
        task_repo.list_by_status.side_effect = lambda uid, status: {
            TaskStatus.DONE: [
                _make_task("t1", TaskStatus.DONE, datetime(2026, 3, 27, 14, 0, tzinfo=timezone.utc), "Done task"),
            ],
            TaskStatus.PENDING: [],
            TaskStatus.SNOOZED: [],
        }[status]

        builder = DailySummaryBuilder(task_repo)
        summary = builder.build("u1", today)
        assert len(summary.completed_tasks) == 1
        assert summary.completed_tasks[0].title == "Done task"

    def test_completed_yesterday_excluded(self):
        today = date(2026, 3, 27)
        task_repo = MagicMock()
        task_repo.list_by_status.side_effect = lambda uid, status: {
            TaskStatus.DONE: [
                _make_task("t1", TaskStatus.DONE, datetime(2026, 3, 26, 10, 0, tzinfo=timezone.utc)),
            ],
            TaskStatus.PENDING: [],
            TaskStatus.SNOOZED: [],
        }[status]

        builder = DailySummaryBuilder(task_repo)
        summary = builder.build("u1", today)
        assert len(summary.completed_tasks) == 0

    def test_pending_tasks_included(self):
        today = date(2026, 3, 27)
        task_repo = MagicMock()
        task_repo.list_by_status.side_effect = lambda uid, status: {
            TaskStatus.DONE: [],
            TaskStatus.PENDING: [
                _make_task("t2", TaskStatus.PENDING, normalized_text="Pending task"),
            ],
            TaskStatus.SNOOZED: [],
        }[status]

        builder = DailySummaryBuilder(task_repo)
        summary = builder.build("u1", today)
        assert len(summary.pending_tasks) == 1

    def test_snoozed_tasks_included(self):
        today = date(2026, 3, 27)
        task_repo = MagicMock()
        task_repo.list_by_status.side_effect = lambda uid, status: {
            TaskStatus.DONE: [],
            TaskStatus.PENDING: [],
            TaskStatus.SNOOZED: [
                _make_task("t3", TaskStatus.SNOOZED, normalized_text="Snoozed task"),
            ],
        }[status]

        builder = DailySummaryBuilder(task_repo)
        summary = builder.build("u1", today)
        assert len(summary.snoozed_tasks) == 1

    def test_empty_day(self):
        today = date(2026, 3, 27)
        task_repo = MagicMock()
        task_repo.list_by_status.return_value = []

        builder = DailySummaryBuilder(task_repo)
        summary = builder.build("u1", today)
        assert len(summary.completed_tasks) == 0
        assert len(summary.pending_tasks) == 0
        assert len(summary.snoozed_tasks) == 0

    def test_summary_date_format(self):
        today = date(2026, 3, 27)
        task_repo = MagicMock()
        task_repo.list_by_status.return_value = []

        builder = DailySummaryBuilder(task_repo)
        summary = builder.build("u1", today)
        assert summary.date == "2026-03-27"

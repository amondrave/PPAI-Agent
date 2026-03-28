"""Builds DailySummary from task state for end-of-day report (US-09)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from ppai.capture.domain.value_objects import TaskStatus
from ppai.profile.domain.entities import UserProfile
from ppai.push.domain.value_objects import DailySummary, TaskSummaryItem


class DailySummaryBuilder:
    """Queries task repository and builds a DailySummary for a user on a given date."""

    def __init__(self, task_repo) -> None:
        self._task_repo = task_repo

    def build(self, user_id: str, for_date: date, profile: Optional[UserProfile] = None) -> DailySummary:
        completed = []
        for task in self._task_repo.list_by_status(user_id, TaskStatus.DONE):
            if task.completed_at and task.completed_at.date() == for_date:
                completed.append(
                    TaskSummaryItem(
                        task_id=task.task_id,
                        title=task.normalized_text,
                        status="completed",
                    )
                )

        pending = [
            TaskSummaryItem(
                task_id=t.task_id,
                title=t.normalized_text,
                status="pending",
            )
            for t in self._task_repo.list_by_status(user_id, TaskStatus.PENDING)
        ]

        snoozed = [
            TaskSummaryItem(
                task_id=t.task_id,
                title=t.normalized_text,
                status="snoozed",
            )
            for t in self._task_repo.list_by_status(user_id, TaskStatus.SNOOZED)
        ]

        return DailySummary(
            user_id=user_id,
            date=for_date.isoformat(),
            completed_tasks=completed,
            pending_tasks=pending,
            snoozed_tasks=snoozed,
        )

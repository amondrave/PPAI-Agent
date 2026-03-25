from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import ACTIVE_STATUSES, TaskStatus


class DynamoDBTaskStateRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def save(self, task: TaskState) -> None:
        item: dict[str, Any] = {
            "userId": task.user_id,
            "taskId": task.task_id,
            "originalText": task.original_text,
            "normalizedText": task.normalized_text,
            "status": task.status.value,
            "sourceIntentId": task.source_intent_id,
            "createdAt": task.created_at.isoformat(),
            "updatedAt": task.updated_at.isoformat(),
        }
        if task.tag is not None:
            item["tag"] = task.tag
        if task.deadline is not None:
            item["deadline"] = task.deadline.isoformat()
        if task.snooze_count:
            item["snoozeCount"] = task.snooze_count
        self._table.put_item(Item=item)

    def get_by_id(self, user_id: str, task_id: str) -> TaskState | None:
        resp = self._table.get_item(Key={"userId": user_id, "taskId": task_id})
        item = resp.get("Item")
        if item is None:
            return None
        return self._to_entity(item)

    def list_pending(self, user_id: str) -> list[TaskState]:
        """Query all pending tasks for a user via userId-status-index (BR-DEC-01)."""
        resp = self._table.query(
            IndexName="userId-status-index",
            KeyConditionExpression="userId = :uid AND #s = :st",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":uid": user_id,
                ":st": TaskStatus.PENDING.value,
            },
        )
        return [self._to_entity(item) for item in resp.get("Items", [])]

    def list_prioritized(self, user_id: str) -> list[TaskState]:
        """Query all prioritized tasks for a user via userId-status-index."""
        resp = self._table.query(
            IndexName="userId-status-index",
            KeyConditionExpression="userId = :uid AND #s = :st",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":uid": user_id,
                ":st": TaskStatus.PRIORITIZED.value,
            },
        )
        return [self._to_entity(item) for item in resp.get("Items", [])]

    def count_active(self, user_id: str) -> int:
        count = 0
        for status in ACTIVE_STATUSES:
            resp = self._table.query(
                IndexName="userId-status-index",
                KeyConditionExpression="userId = :uid AND #s = :st",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":uid": user_id,
                    ":st": status.value,
                },
                Select="COUNT",
            )
            count += resp["Count"]
        return count

    @staticmethod
    def _to_entity(item: dict[str, Any]) -> TaskState:
        return TaskState(
            user_id=item["userId"],
            task_id=item["taskId"],
            original_text=item["originalText"],
            normalized_text=item["normalizedText"],
            status=TaskStatus(item["status"]),
            source_intent_id=item["sourceIntentId"],
            tag=item.get("tag"),
            deadline=(
                datetime.fromisoformat(item["deadline"])
                if item.get("deadline")
                else None
            ),
            snooze_count=int(item.get("snoozeCount", 0)),
            created_at=datetime.fromisoformat(item["createdAt"]),
            updated_at=datetime.fromisoformat(item["updatedAt"]),
        )

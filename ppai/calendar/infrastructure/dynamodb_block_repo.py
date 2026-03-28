from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ppai.calendar.domain.entities import TimeBlock
from ppai.calendar.domain.value_objects import BlockStatus, TaskCategory

_TABLE_SUFFIX = "time-blocks"


class DynamoDBTimeBlockRepository:
    """DynamoDB repository for TimeBlock entities. PK: userId, SK: date#blockId."""

    def __init__(self, table: Any) -> None:
        self._table = table

    def save_plan(self, blocks: list[TimeBlock]) -> None:
        """Save all blocks in a plan using batch writer."""
        with self._table.batch_writer() as batch:
            for block in blocks:
                item = self._to_item(block)
                batch.put_item(Item=item)

    def get_plan(self, user_id: str, date: str) -> list[TimeBlock]:
        """Get all blocks for a user on a specific date."""
        resp = self._table.query(
            KeyConditionExpression="userId = :uid AND begins_with(#sk, :prefix)",
            ExpressionAttributeNames={"#sk": "date#blockId"},
            ExpressionAttributeValues={
                ":uid": user_id,
                ":prefix": f"{date}#",
            },
        )
        return [self._to_entity(item) for item in resp.get("Items", [])]

    def update_block_status(self, block_id: str, user_id: str, date: str, status: BlockStatus) -> None:
        """Update the status of a specific block."""
        sk = f"{date}#{block_id}"
        self._table.update_item(
            Key={"userId": user_id, "date#blockId": sk},
            UpdateExpression="SET #st = :status",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={":status": status.value},
        )

    def get_block(self, block_id: str, user_id: str, date: str) -> TimeBlock | None:
        """Get a specific block by its ID."""
        sk = f"{date}#{block_id}"
        resp = self._table.get_item(Key={"userId": user_id, "date#blockId": sk})
        item = resp.get("Item")
        if item is None:
            return None
        return self._to_entity(item)

    @staticmethod
    def _to_item(block: TimeBlock) -> dict[str, Any]:
        item: dict[str, Any] = {
            "userId": block.user_id,
            "date#blockId": f"{block.date}#{block.block_id}",
            "blockId": block.block_id,
            "taskId": block.task_id,
            "taskTitle": block.task_title,
            "date": block.date,
            "start": block.start.isoformat(),
            "end": block.end.isoformat(),
            "status": block.status.value,
            "category": block.category.value,
            "createdAt": block.created_at.isoformat(),
        }
        if block.calendar_event_id is not None:
            item["calendarEventId"] = block.calendar_event_id
        return item

    @staticmethod
    def _to_entity(item: dict[str, Any]) -> TimeBlock:
        return TimeBlock(
            block_id=item["blockId"],
            user_id=item["userId"],
            task_id=item["taskId"],
            task_title=item["taskTitle"],
            date=item["date"],
            start=datetime.fromisoformat(item["start"]),
            end=datetime.fromisoformat(item["end"]),
            status=BlockStatus(item["status"]),
            category=TaskCategory(item["category"]),
            calendar_event_id=item.get("calendarEventId"),
            created_at=datetime.fromisoformat(item["createdAt"]),
        )

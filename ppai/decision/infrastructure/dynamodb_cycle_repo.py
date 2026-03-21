from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from boto3.dynamodb.conditions import Attr, Key

from ppai.decision.domain.entities import ExecutionCycle
from ppai.decision.domain.exceptions import CycleConflictError
from ppai.decision.domain.value_objects import CycleStatus


class DynamoDBCycleRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def get_active(self, user_id: str, date: str) -> ExecutionCycle | None:
        resp = self._table.query(
            IndexName="userId-date-index",
            KeyConditionExpression=Key("userId").eq(user_id) & Key("date").eq(date),
            FilterExpression=Attr("status").eq(CycleStatus.ACTIVE.value),
            Limit=1,
        )
        items = resp.get("Items", [])
        return self._to_entity(items[0]) if items else None

    def save(self, cycle: ExecutionCycle) -> None:
        item: dict[str, Any] = {
            "cycleId": cycle.cycle_id,
            "userId": cycle.user_id,
            "date": cycle.date,
            "status": cycle.status.value,
            "top3TaskIds": cycle.top3_task_ids,
            "manualReorders": cycle.manual_reorders,
            "createdAt": cycle.created_at.isoformat(),
        }
        if cycle.closed_at is not None:
            item["closedAt"] = cycle.closed_at.isoformat()

        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(cycleId)",
            )
        except self._table.meta.client.exceptions.ConditionalCheckFailedException as exc:
            raise CycleConflictError(
                f"Active cycle already exists for user={cycle.user_id} date={cycle.date}"
            ) from exc

    def update_top3(self, cycle_id: str, top3_task_ids: list[str]) -> None:
        self._table.update_item(
            Key={"cycleId": cycle_id},
            UpdateExpression="SET top3TaskIds = :ids",
            ExpressionAttributeValues={":ids": top3_task_ids},
        )

    def increment_reorders(self, cycle_id: str) -> None:
        self._table.update_item(
            Key={"cycleId": cycle_id},
            UpdateExpression="ADD manualReorders :one",
            ExpressionAttributeValues={":one": 1},
        )

    @staticmethod
    def _to_entity(item: dict[str, Any]) -> ExecutionCycle:
        return ExecutionCycle(
            cycle_id=item["cycleId"],
            user_id=item["userId"],
            date=item["date"],
            status=CycleStatus(item["status"]),
            top3_task_ids=list(item.get("top3TaskIds", [])),
            manual_reorders=int(item.get("manualReorders", 0)),
            created_at=datetime.fromisoformat(item["createdAt"]),
            closed_at=(
                datetime.fromisoformat(item["closedAt"])
                if item.get("closedAt")
                else None
            ),
        )

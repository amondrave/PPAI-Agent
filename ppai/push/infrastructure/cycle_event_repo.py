from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Optional

from boto3.dynamodb.conditions import Attr, Key

from ppai.decision.domain.entities import ExecutionCycle
from ppai.decision.domain.value_objects import CycleStatus


class DynamoDBCycleEventRepository:
    """
    Reads ExecutionCycle state and appends nudge dispatch events to ppai-cycles.
    Reuses the same table as UOW-02's DynamoDBCycleRepository.
    """

    def __init__(self, table: Any) -> None:
        self._table = table

    # ------------------------------------------------------------------
    # CycleEventRepository protocol
    # ------------------------------------------------------------------

    def get_active(self, user_id: str, for_date: date) -> Optional[ExecutionCycle]:
        date_str = for_date.strftime("%Y-%m-%d")
        resp = self._table.query(
            IndexName="userId-date-index",
            KeyConditionExpression=Key("userId").eq(user_id) & Key("date").eq(date_str),
            FilterExpression=Attr("status").eq(CycleStatus.ACTIVE.value),
            Limit=1,
        )
        items = resp.get("Items", [])
        return self._to_entity(items[0]) if items else None

    def create(self, cycle: ExecutionCycle) -> None:
        item: dict[str, Any] = {
            "cycleId": cycle.cycle_id,
            "userId": cycle.user_id,
            "date": cycle.date,
            "status": cycle.status.value,
            "top3TaskIds": cycle.top3_task_ids,
            "manualReorders": cycle.manual_reorders,
            "nudgeEvents": [],
            "createdAt": cycle.created_at.isoformat(),
        }
        self._table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(cycleId)",
        )

    def record_nudge_event(
        self,
        cycle_id: str,
        event_type: str,
        metadata: dict,
    ) -> None:
        event = {
            "eventType": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **{k: str(v) for k, v in metadata.items()},
        }
        self._table.update_item(
            Key={"cycleId": cycle_id},
            UpdateExpression="SET nudgeEvents = list_append(if_not_exists(nudgeEvents, :empty), :evt)",
            ExpressionAttributeValues={
                ":evt": [event],
                ":empty": [],
            },
        )

    def get_nudge_count(self, cycle_id: str) -> int:
        resp = self._table.get_item(
            Key={"cycleId": cycle_id},
            ProjectionExpression="nudgeEvents",
        )
        item = resp.get("Item", {})
        events = item.get("nudgeEvents", [])
        return sum(1 for e in events if e.get("eventType") == "NUDGE_SENT")

    def has_event_today(self, cycle_id: str, event_type: str) -> bool:
        resp = self._table.get_item(
            Key={"cycleId": cycle_id},
            ProjectionExpression="nudgeEvents",
        )
        item = resp.get("Item", {})
        events = item.get("nudgeEvents", [])
        return any(e.get("eventType") == event_type for e in events)

    def get_last_activity_at(self, user_id: str) -> Optional[datetime]:
        """
        Query all events for user and return the most recent activity timestamp.
        Activity types: NUDGE_SENT, NUDGE_SCHEDULED, any external interaction.
        Uses a scan with filter — acceptable for MVP volume.
        """
        resp = self._table.query(
            IndexName="userId-date-index",
            KeyConditionExpression=Key("userId").eq(user_id),
            ScanIndexForward=False,  # most recent first
            Limit=5,
        )
        latest: Optional[datetime] = None
        for item in resp.get("Items", []):
            for event in item.get("nudgeEvents", []):
                ts_str = event.get("timestamp")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str)
                    if latest is None or ts > latest:
                        latest = ts
        return latest

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

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
        )

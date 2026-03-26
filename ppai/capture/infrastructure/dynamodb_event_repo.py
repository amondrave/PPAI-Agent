from __future__ import annotations

import json
from typing import Any

from ppai.capture.domain.entities import CaptureEvent
from ppai.respond.domain.entities import InteractionEvent

_TTL_90_DAYS = 7_776_000  # 90 days in seconds


class DynamoDBEventRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def append(self, event: CaptureEvent) -> None:
        self._table.put_item(
            Item={
                "userId": event.user_id,
                "timestamp#eventId": f"{event.timestamp.isoformat()}#{event.event_id}",
                "eventType": event.event_type,
                "taskId": event.task_id,
                "originalText": event.original_text,
                "correlationId": event.correlation_id,
            }
        )

    def append_interaction(self, event: InteractionEvent) -> None:
        """Persist an InteractionEvent with TTL (90 days)."""
        ttl = int(event.timestamp.timestamp()) + _TTL_90_DAYS
        item: dict[str, Any] = {
            "userId": event.user_id,
            "timestamp#eventId": f"{event.timestamp.isoformat()}#{event.event_id}",
            "eventType": event.event_type,
            "taskId": event.task_id,
            "correlationId": event.correlation_id,
            "ttl": ttl,
        }
        if event.metadata:
            item["metadata"] = json.dumps(event.metadata)
        self._table.put_item(Item=item)

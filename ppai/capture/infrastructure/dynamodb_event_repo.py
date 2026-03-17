from __future__ import annotations

from typing import Any

from ppai.capture.domain.entities import CaptureEvent


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

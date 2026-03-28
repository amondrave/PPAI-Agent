from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ppai.calendar.domain.entities import CalendarAuth

_TABLE_SUFFIX = "calendar-auth"


class DynamoDBCalendarAuthRepository:
    """DynamoDB repository for CalendarAuth entities. Table PK: userId."""

    def __init__(self, table: Any) -> None:
        self._table = table

    def get(self, user_id: str) -> CalendarAuth | None:
        resp = self._table.get_item(Key={"userId": user_id})
        item = resp.get("Item")
        if item is None:
            return None
        return self._to_entity(item)

    def save(self, auth: CalendarAuth) -> None:
        item: dict[str, Any] = {
            "userId": auth.user_id,
            "accessToken": auth.access_token,
            "refreshToken": auth.refresh_token,
            "tokenExpiry": auth.token_expiry.isoformat(),
            "calendarConnected": auth.calendar_connected,
            "createdAt": auth.created_at.isoformat(),
            "updatedAt": auth.updated_at.isoformat(),
        }
        self._table.put_item(Item=item)

    def delete(self, user_id: str) -> None:
        self._table.delete_item(Key={"userId": user_id})

    @staticmethod
    def _to_entity(item: dict[str, Any]) -> CalendarAuth:
        return CalendarAuth(
            user_id=item["userId"],
            access_token=item["accessToken"],
            refresh_token=item["refreshToken"],
            token_expiry=datetime.fromisoformat(item["tokenExpiry"]),
            calendar_connected=item.get("calendarConnected", True),
            created_at=datetime.fromisoformat(item["createdAt"]),
            updated_at=datetime.fromisoformat(item["updatedAt"]),
        )

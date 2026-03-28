"""DynamoDB repository for UserProfile entities."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any, Optional

from ppai.profile.domain.entities import UserProfile
from ppai.profile.domain.value_objects import CommunicationStyle, WeekendMode


class DynamoDBProfileRepository:
    """
    Persists UserProfile in ppai-user-profiles DynamoDB table.
    PK: userId (String), no SK, no GSI.
    """

    def __init__(self, table: Any) -> None:
        self._table = table

    def get(self, user_id: str) -> Optional[UserProfile]:
        resp = self._table.get_item(Key={"userId": user_id})
        item = resp.get("Item")
        return self._to_entity(item) if item else None

    def save(self, profile: UserProfile) -> None:
        item: dict[str, Any] = {
            "userId": profile.user_id,
            "name": profile.name,
            "occupation": profile.occupation,
            "workStart": profile.work_start.strftime("%H:%M") if profile.work_start else None,
            "workEnd": profile.work_end.strftime("%H:%M") if profile.work_end else None,
            "protectedBlocks": profile.protected_blocks,
            "communicationStyle": profile.communication_style.value,
            "timezone": profile.timezone,
            "daysOff": profile.days_off,
            "weekendMode": profile.weekend_mode.value,
            "onboardingCompleted": profile.onboarding_completed,
            "createdAt": profile.created_at.isoformat(),
            "updatedAt": profile.updated_at.isoformat(),
        }
        if profile.holidays_country is not None:
            item["holidaysCountry"] = profile.holidays_country
        # Remove None values to avoid DynamoDB type errors
        item = {k: v for k, v in item.items() if v is not None}
        self._table.put_item(Item=item)

    def exists(self, user_id: str) -> bool:
        resp = self._table.get_item(
            Key={"userId": user_id},
            ProjectionExpression="userId",
        )
        return "Item" in resp

    @staticmethod
    def _to_entity(item: dict[str, Any]) -> UserProfile:
        work_start = None
        if item.get("workStart"):
            parts = item["workStart"].split(":")
            work_start = time(int(parts[0]), int(parts[1]))

        work_end = None
        if item.get("workEnd"):
            parts = item["workEnd"].split(":")
            work_end = time(int(parts[0]), int(parts[1]))

        return UserProfile(
            user_id=item["userId"],
            name=item.get("name", ""),
            occupation=item.get("occupation", ""),
            work_start=work_start,
            work_end=work_end,
            protected_blocks=item.get("protectedBlocks", []),
            communication_style=CommunicationStyle(
                item.get("communicationStyle", CommunicationStyle.GENTLE.value)
            ),
            timezone=item.get("timezone", "America/Bogota"),
            days_off=item.get("daysOff", []),
            holidays_country=item.get("holidaysCountry"),
            weekend_mode=WeekendMode(
                item.get("weekendMode", WeekendMode.DESCANSO.value)
            ),
            onboarding_completed=item.get("onboardingCompleted", False),
            created_at=datetime.fromisoformat(item["createdAt"])
            if item.get("createdAt")
            else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(item["updatedAt"])
            if item.get("updatedAt")
            else datetime.now(timezone.utc),
        )

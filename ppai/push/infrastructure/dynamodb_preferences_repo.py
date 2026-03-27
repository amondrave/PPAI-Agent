from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from ppai.push.domain.entities import UserNudgePreferences


class DynamoDBPreferencesRepository:
    """
    Persists UserNudgePreferences in ppai-preferences DynamoDB table.
    PK: userId (String), no SK, no GSI.
    """

    def __init__(self, table: Any) -> None:
        self._table = table

    def get(self, user_id: str) -> Optional[UserNudgePreferences]:
        resp = self._table.get_item(Key={"userId": user_id})
        item = resp.get("Item")
        return self._to_entity(item) if item else None

    def get_all(self) -> list[UserNudgePreferences]:
        resp = self._table.scan()
        items = resp.get("Items", [])
        return [self._to_entity(item) for item in items]

    def save(self, prefs: UserNudgePreferences) -> None:
        item: dict[str, Any] = {
            "userId": prefs.user_id,
            "timezone": prefs.timezone,
            "maxNudgesPerDay": prefs.max_nudges_per_day,
            "updatedAt": datetime.utcnow().isoformat(),
            # UOW-05 fields
            "dailyStartTime": prefs.daily_start_time,
            "dailyEndTime": prefs.daily_end_time,
            "zenActive": prefs.zen_active,
            "zenIntervalMinutes": prefs.zen_interval_minutes,
            "zenMaxNudges": prefs.zen_max_nudges,
            "motivationalMessage": prefs.motivational_message,
        }
        if prefs.silence_start is not None:
            item["silenceStart"] = prefs.silence_start
        if prefs.silence_end is not None:
            item["silenceEnd"] = prefs.silence_end
        self._table.put_item(Item=item)

    @staticmethod
    def _to_entity(item: dict[str, Any]) -> UserNudgePreferences:
        return UserNudgePreferences(
            user_id=item["userId"],
            timezone=item.get("timezone", "America/Bogota"),
            max_nudges_per_day=int(item.get("maxNudgesPerDay", 3)),
            silence_start=item.get("silenceStart"),
            silence_end=item.get("silenceEnd"),
            updated_at=(
                datetime.fromisoformat(item["updatedAt"])
                if item.get("updatedAt")
                else None
            ),
            # UOW-05 fields with defaults
            daily_start_time=item.get("dailyStartTime", "08:00"),
            daily_end_time=item.get("dailyEndTime", "18:00"),
            zen_active=item.get("zenActive", False),
            zen_interval_minutes=int(item.get("zenIntervalMinutes", 15)),
            zen_max_nudges=int(item.get("zenMaxNudges", 10)),
            motivational_message=item.get("motivationalMessage", "A darle con todo hoy"),
        )

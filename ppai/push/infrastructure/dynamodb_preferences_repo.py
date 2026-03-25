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

    def save(self, prefs: UserNudgePreferences) -> None:
        item: dict[str, Any] = {
            "userId": prefs.user_id,
            "timezone": prefs.timezone,
            "maxNudgesPerDay": prefs.max_nudges_per_day,
            "updatedAt": datetime.utcnow().isoformat(),
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
        )

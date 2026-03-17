from __future__ import annotations

import hashlib
import time
from typing import Any

from ppai.shared.infrastructure.config import Settings


class DynamoDBDedupRepository:
    def __init__(self, table: Any, settings: Settings) -> None:
        self._table = table
        self._dedup_window = settings.dedup_window_seconds

    def exists(self, user_id: str, exact_text: str) -> bool:
        key = self._build_key(user_id, exact_text)
        resp = self._table.get_item(Key={"userId#exactTextHash": key})
        item = resp.get("Item")
        if item is None:
            return False
        expires_at = item.get("expiresAt", 0)
        return int(time.time()) < int(expires_at)

    def record(self, user_id: str, exact_text: str, task_id: str) -> None:
        key = self._build_key(user_id, exact_text)
        now = int(time.time())
        self._table.put_item(
            Item={
                "userId#exactTextHash": key,
                "taskId": task_id,
                "lastSeenAt": now,
                "expiresAt": now + self._dedup_window,
            }
        )

    @staticmethod
    def _build_key(user_id: str, exact_text: str) -> str:
        text_hash = hashlib.sha256(exact_text.encode()).hexdigest()
        return f"{user_id}#{text_hash}"

from __future__ import annotations

import time
from collections import defaultdict


class InMemoryRateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str) -> bool:
        now = time.monotonic()
        self._cleanup(user_id, now)
        if len(self._requests[user_id]) >= self._max_requests:
            return False
        self._requests[user_id].append(now)
        return True

    def _cleanup(self, user_id: str, now: float) -> None:
        cutoff = now - self._window_seconds
        self._requests[user_id] = [
            t for t in self._requests[user_id] if t > cutoff
        ]

"""Thread-safe in-memory user registry.

Tracks chat_ids of users who have interacted with the bot so the
NudgeScheduler knows whom to evaluate on each tick.
"""

from __future__ import annotations

import threading


class UserRegistry:
    """Thread-safe set of active user IDs (chat_ids as strings)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._users: set[str] = set()

    def register(self, user_id: str) -> None:
        """Add a user_id to the registry (idempotent)."""
        with self._lock:
            self._users.add(user_id)

    def get_all(self) -> list[str]:
        """Return a snapshot of all registered user IDs."""
        with self._lock:
            return list(self._users)

    def __len__(self) -> int:
        with self._lock:
            return len(self._users)

    def __contains__(self, user_id: str) -> bool:
        with self._lock:
            return user_id in self._users

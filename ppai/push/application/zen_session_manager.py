"""In-memory manager for active zen sessions (DP-SCHED-04)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import ZenSession


class ZenSessionManager:
    """Manages zen sessions in memory. Thread-safe is not required (single scheduler thread)."""

    def __init__(self) -> None:
        self._sessions: dict[str, ZenSession] = {}

    def activate(
        self,
        user_id: str,
        zen_max_nudges: int,
        zen_interval_minutes: int,
    ) -> ZenSession:
        """Create a new zen session. If one already exists, return it."""
        existing = self._sessions.get(user_id)
        if existing is not None:
            return existing
        session = ZenSession(
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            max_nudges=zen_max_nudges,
            interval_minutes=zen_interval_minutes,
        )
        self._sessions[user_id] = session
        return session

    def deactivate(self, user_id: str) -> Optional[ZenSession]:
        """Remove zen session. Returns the session with stats, or None if not active."""
        return self._sessions.pop(user_id, None)

    def get(self, user_id: str) -> Optional[ZenSession]:
        """Return active session or None."""
        return self._sessions.get(user_id)

    def record_nudge(self, user_id: str) -> bool:
        """Increment nudges_sent. Returns False if cap reached after increment."""
        session = self._sessions.get(user_id)
        if session is None:
            return False
        session.nudges_sent += 1
        return not session.has_reached_cap

    def reconstruct_from_prefs(self, prefs_list: list[UserNudgePreferences]) -> None:
        """At bot startup, reconstruct sessions for users with zen_active=True (DP-SCHED-04)."""
        for prefs in prefs_list:
            if prefs.zen_active:
                self.activate(
                    user_id=prefs.user_id,
                    zen_max_nudges=prefs.zen_max_nudges,
                    zen_interval_minutes=prefs.zen_interval_minutes,
                )

    def get_min_interval(self) -> Optional[int]:
        """Return the smallest zen_interval_minutes among active sessions, or None."""
        if not self._sessions:
            return None
        return min(s.interval_minutes for s in self._sessions.values())

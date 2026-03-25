from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Protocol, runtime_checkable

from ppai.push.domain.entities import NudgeMessage, UserNudgePreferences


@runtime_checkable
class PreferencesRepository(Protocol):
    """Port for reading and writing user nudge preferences."""

    def get(self, user_id: str) -> Optional[UserNudgePreferences]:
        """Return preferences for user_id, or None if not configured."""
        ...

    def save(self, prefs: UserNudgePreferences) -> None:
        """Persist (create or update) preferences for a user."""
        ...


@runtime_checkable
class CycleEventRepository(Protocol):
    """Port for reading ExecutionCycle state and appending dispatch events."""

    def get_active(self, user_id: str, for_date: date) -> Optional[object]:
        """Return the active ExecutionCycle for user_id on for_date, or None."""
        ...

    def create(self, cycle: object) -> None:
        """Persist a new ExecutionCycle. Raises if one already exists for the day."""
        ...

    def record_nudge_event(
        self,
        cycle_id: str,
        event_type: str,
        metadata: dict,
    ) -> None:
        """Append a nudge-related event to the cycle's event log."""
        ...

    def get_nudge_count(self, cycle_id: str) -> int:
        """Return the number of NUDGE_SENT events in the given cycle."""
        ...

    def get_last_activity_at(self, user_id: str) -> Optional[datetime]:
        """Return the timestamp of the most recent relevant activity for user_id."""
        ...


@runtime_checkable
class TelegramPushPort(Protocol):
    """Outbound port for sending nudge messages via Telegram."""

    def send_nudge(self, chat_id: str, message: NudgeMessage) -> bool:
        """
        Send a nudge message with inline buttons to the given chat.
        Returns True on success, False on failure.
        """
        ...

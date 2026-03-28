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

    def get_all(self) -> list[UserNudgePreferences]:
        """Return all user preferences. Used for zen session reconstruction at startup."""
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

    def has_event_today(self, cycle_id: str, event_type: str) -> bool:
        """Check if an event of given type exists in the cycle (idempotency guard)."""
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

    def send_message(self, chat_id: str, text: str) -> bool:
        """Send a plain text message (no buttons). Used for daily reminders."""
        ...

    def send_message_with_buttons(
        self,
        chat_id: str,
        text: str,
        buttons: list[list[dict[str, str]]],
    ) -> bool:
        """Send a message with inline keyboard buttons (ER3 block reminders, etc.)."""
        ...

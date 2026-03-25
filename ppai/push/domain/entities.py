from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class UserNudgePreferences:
    """Nudge configuration for a user. Persisted in ppai-preferences DynamoDB table."""

    user_id: str
    timezone: str = "America/Bogota"
    max_nudges_per_day: int = 3
    silence_start: Optional[str] = None  # "HH:MM" format
    silence_end: Optional[str] = None    # "HH:MM" format
    updated_at: Optional[datetime] = None

    def has_silence_window(self) -> bool:
        return self.silence_start is not None and self.silence_end is not None


@dataclass(frozen=True)
class NudgeMessage:
    """Content of a nudge message to be sent via Telegram."""

    task_id: str
    task_title: str
    priority_reason: str
    tone_profile: str = "soft_motivational"
    buttons: tuple[str, ...] = ("done", "snooze", "clarify")

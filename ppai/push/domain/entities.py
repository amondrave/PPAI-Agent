from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time as dtime
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
    # UOW-05: Scheduler bot nativo
    daily_start_time: str = "08:00"       # HH:MM — recordatorio matutino
    daily_end_time: str = "18:00"         # HH:MM — resumen de cierre
    zen_active: bool = False
    zen_interval_minutes: int = 15        # 5-60
    zen_max_nudges: int = 10              # 1-50
    motivational_message: str = "A darle con todo hoy"

    def has_silence_window(self) -> bool:
        return self.silence_start is not None and self.silence_end is not None

    def is_within_start_window(self, local_now: datetime, tolerance_minutes: int = 7) -> bool:
        """True if local_now is within ±tolerance of daily_start_time (BR-SCHED-01)."""
        return self._is_within_window(local_now, self.daily_start_time, tolerance_minutes)

    def is_within_end_window(self, local_now: datetime, tolerance_minutes: int = 7) -> bool:
        """True if local_now is within ±tolerance of daily_end_time (BR-SCHED-01)."""
        return self._is_within_window(local_now, self.daily_end_time, tolerance_minutes)

    def should_zen_override_silence(self) -> bool:
        """True if zen is active — zen overrides silence window (BR-SCHED-12)."""
        return self.zen_active

    def _is_within_window(self, local_now: datetime, target_hhmm: str, tolerance: int) -> bool:
        target = dtime.fromisoformat(target_hhmm)
        now_minutes = local_now.hour * 60 + local_now.minute
        target_minutes = target.hour * 60 + target.minute
        delta = abs(now_minutes - target_minutes)
        # Handle cross-midnight wrap (DP-SCHED-03)
        delta = min(delta, 1440 - delta)
        return delta <= tolerance


@dataclass(frozen=True)
class NudgeMessage:
    """Content of a nudge message to be sent via Telegram."""

    task_id: str
    task_title: str
    priority_reason: str
    tone_profile: str = "soft_motivational"
    buttons: tuple[str, ...] = ("done", "snooze", "clarify")

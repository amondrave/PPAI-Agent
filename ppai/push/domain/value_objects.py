from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Optional


class NudgeDispatchStatus(StrEnum):
    scheduled = "scheduled"
    sent = "sent"
    skipped_activity = "skipped_activity"
    skipped_no_top3 = "skipped_no_top3"
    failed = "failed"


@dataclass(frozen=True)
class WindowEvaluation:
    """Result of evaluating whether a nudge window is active for a user."""

    window_start: datetime
    window_end: datetime
    is_silence_window: bool
    recent_activity: bool

    @property
    def can_dispatch(self) -> bool:
        return not self.is_silence_window and not self.recent_activity


@dataclass(frozen=True)
class DispatchOutcome:
    """Result of a single dispatch attempt for a user."""

    status: NudgeDispatchStatus
    user_id: str
    task_id: Optional[str] = None
    cycle_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    reason: Optional[str] = None

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


# --- UOW-05: Scheduler Bot Nativo value objects ---


@dataclass(frozen=True)
class TaskSummaryItem:
    """A task entry in the daily summary."""

    task_id: str
    title: str
    status: str  # completed / pending / snoozed


@dataclass(frozen=True)
class RescueSuggestion:
    """Rescue proposal for a 'día caído' (BR-SCHED-06..08)."""

    key_task: TaskSummaryItem
    micro_action: str
    tone: str = "empathetic"


@dataclass
class DailySummary:
    """End-of-day summary generated on-the-fly (not persisted)."""

    user_id: str
    date: str  # YYYY-MM-DD
    completed_tasks: list[TaskSummaryItem] = field(default_factory=list)
    pending_tasks: list[TaskSummaryItem] = field(default_factory=list)
    snoozed_tasks: list[TaskSummaryItem] = field(default_factory=list)
    rescue_triggered: bool = False
    rescue_suggestion: Optional[RescueSuggestion] = None


@dataclass
class ZenSession:
    """In-memory tracking of an active zen session (DP-SCHED-04)."""

    user_id: str
    started_at: datetime
    nudges_sent: int = 0
    max_nudges: int = 10
    interval_minutes: int = 15

    @property
    def has_reached_cap(self) -> bool:
        return self.nudges_sent >= self.max_nudges

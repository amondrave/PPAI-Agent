from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ppai.shared.domain.base_entity import generate_id
from ppai.calendar.domain.value_objects import BlockStatus, TaskCategory


@dataclass
class CalendarAuth:
    user_id: str
    access_token: str  # encrypted
    refresh_token: str  # encrypted
    token_expiry: datetime
    calendar_connected: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CalendarEvent:
    event_id: str
    title: str
    start: datetime
    end: datetime
    is_all_day: bool = False
    source: str = "google"


@dataclass
class TimeBlock:
    block_id: str
    user_id: str
    task_id: str
    task_title: str
    date: str  # YYYY-MM-DD
    start: datetime
    end: datetime
    status: BlockStatus = BlockStatus.PLANNED
    category: TaskCategory = TaskCategory.PERSONAL
    calendar_event_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DayPlan:
    user_id: str
    date: str  # YYYY-MM-DD
    blocks: list[TimeBlock] = field(default_factory=list)
    calendar_events: list[CalendarEvent] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FreeSlot:
    start: datetime
    end: datetime
    duration_minutes: int = 0

    def __post_init__(self) -> None:
        if self.duration_minutes == 0:
            delta = self.end - self.start
            self.duration_minutes = int(delta.total_seconds() / 60)

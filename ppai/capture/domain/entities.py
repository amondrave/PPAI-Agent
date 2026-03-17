from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field

from ppai.shared.domain.base_entity import generate_id
from ppai.capture.domain.value_objects import TaskStatus


@dataclass
class Intent:
    user_id: str
    raw_text: str
    source: str = "telegram"
    intent_id: str = field(default_factory=generate_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TaskState:
    user_id: str
    original_text: str
    normalized_text: str
    source_intent_id: str
    tag: str | None = None
    deadline: datetime | None = None
    status: TaskStatus = TaskStatus.CAPTURED
    task_id: str = field(default_factory=generate_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def transition_to_pending(self) -> None:
        self.status = TaskStatus.PENDING
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class CaptureEvent:
    task_id: str
    user_id: str
    original_text: str
    correlation_id: str
    event_type: str = "INTENT_CAPTURED"
    event_id: str = field(default_factory=generate_id)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DedupRecord:
    user_id: str
    exact_text: str
    task_id: str
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

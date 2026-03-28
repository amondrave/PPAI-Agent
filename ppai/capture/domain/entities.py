from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from ppai.shared.domain.base_entity import generate_id
from ppai.capture.domain.value_objects import TaskStatus
from ppai.respond.domain.exceptions import InvalidTransitionError


_TRANSITIONABLE_TO_DONE = frozenset({
    TaskStatus.PENDING,
    TaskStatus.PRIORITIZED,
    TaskStatus.NUDGED,
})

_TRANSITIONABLE_TO_SNOOZED = frozenset({
    TaskStatus.PENDING,
    TaskStatus.PRIORITIZED,
    TaskStatus.NUDGED,
})

_TRANSITIONABLE_TO_CLARIFY = frozenset({
    TaskStatus.PENDING,
    TaskStatus.PRIORITIZED,
    TaskStatus.NUDGED,
    TaskStatus.SNOOZED,
})

MAX_SNOOZE_COUNT = 3


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
    snooze_count: int = 0
    snoozed_until: datetime | None = None
    completed_at: datetime | None = None
    category: str | None = None
    estimated_minutes: int | None = None
    days_in_top3: int = 0
    friction_notes: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.CAPTURED
    task_id: str = field(default_factory=generate_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def transition_to_pending(self) -> None:
        self.status = TaskStatus.PENDING
        self.updated_at = datetime.now(timezone.utc)

    def transition_to_done(self, now: datetime) -> None:
        if self.status not in _TRANSITIONABLE_TO_DONE:
            raise InvalidTransitionError(
                f"Cannot transition from {self.status} to DONE"
            )
        self.status = TaskStatus.DONE
        self.completed_at = now
        self.updated_at = now

    def transition_to_snoozed(self, now: datetime, cooldown: timedelta) -> None:
        if self.is_snooze_limit_reached():
            raise InvalidTransitionError(
                f"Snooze limit reached ({MAX_SNOOZE_COUNT})"
            )
        if self.status not in _TRANSITIONABLE_TO_SNOOZED:
            raise InvalidTransitionError(
                f"Cannot transition from {self.status} to SNOOZED"
            )
        self.status = TaskStatus.SNOOZED
        self.snooze_count += 1
        self.snoozed_until = now + cooldown
        self.updated_at = now

    def transition_to_needs_clarification(self, now: datetime) -> None:
        if self.status not in _TRANSITIONABLE_TO_CLARIFY:
            raise InvalidTransitionError(
                f"Cannot transition from {self.status} to NEEDS_CLARIFICATION"
            )
        self.status = TaskStatus.NEEDS_CLARIFICATION
        self.updated_at = now

    def resolve_clarification(self, text: str, now: datetime) -> None:
        if self.status != TaskStatus.NEEDS_CLARIFICATION:
            raise InvalidTransitionError(
                f"Cannot resolve clarification from {self.status}"
            )
        self.normalized_text = text
        self.snooze_count = 0
        self.snoozed_until = None
        self.status = TaskStatus.PENDING
        self.updated_at = now

    def is_snooze_limit_reached(self) -> bool:
        return self.snooze_count >= MAX_SNOOZE_COUNT


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

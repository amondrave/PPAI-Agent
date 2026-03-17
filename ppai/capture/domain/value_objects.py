from enum import StrEnum


class TaskStatus(StrEnum):
    CAPTURED = "captured"
    PENDING = "pending"
    PRIORITIZED = "prioritized"
    NUDGED = "nudged"
    DONE = "done"
    SNOOZED = "snoozed"
    CLARIFYING = "clarifying"


ACTIVE_STATUSES = frozenset({
    TaskStatus.CAPTURED,
    TaskStatus.PENDING,
    TaskStatus.PRIORITIZED,
    TaskStatus.NUDGED,
    TaskStatus.SNOOZED,
    TaskStatus.CLARIFYING,
})

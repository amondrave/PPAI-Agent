from enum import StrEnum


class TaskStatus(StrEnum):
    CAPTURED = "captured"
    PENDING = "pending"
    PRIORITIZED = "prioritized"
    NUDGED = "nudged"
    DONE = "done"
    SNOOZED = "snoozed"
    CLARIFYING = "clarifying"
    NEEDS_CLARIFICATION = "needs_clarification"


ACTIVE_STATUSES = frozenset({
    TaskStatus.CAPTURED,
    TaskStatus.PENDING,
    TaskStatus.PRIORITIZED,
    TaskStatus.NUDGED,
    TaskStatus.SNOOZED,
    TaskStatus.CLARIFYING,
})

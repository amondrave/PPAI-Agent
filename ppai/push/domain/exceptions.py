class PushError(Exception):
    """Base exception for push/scheduling errors."""


class NoTop3AvailableError(PushError):
    """Raised when there is no current Top 3 to select a nudge target from."""


class SilenceWindowActiveError(PushError):
    """Raised when the user's silence window is currently active."""


class DailyCapReachedError(PushError):
    """Raised when the user has already received the maximum nudges for today."""


class NudgeDispatchFailedError(PushError):
    """Raised when all retry attempts to send a nudge have been exhausted."""

    def __init__(self, task_id: str, attempt_count: int, cause: str = ""):
        self.task_id = task_id
        self.attempt_count = attempt_count
        self.cause = cause
        super().__init__(
            f"Nudge dispatch failed for task {task_id} after {attempt_count} attempts. {cause}"
        )

from typing import Protocol

from ppai.capture.domain.entities import TaskState, CaptureEvent, DedupRecord


class TaskStateRepository(Protocol):
    def save(self, task: TaskState) -> None: ...

    def get_by_id(self, user_id: str, task_id: str) -> TaskState | None: ...

    def count_active(self, user_id: str) -> int: ...


class EventRepository(Protocol):
    def append(self, event: CaptureEvent) -> None: ...


class DedupRepository(Protocol):
    def exists(self, user_id: str, exact_text: str) -> bool: ...

    def record(self, user_id: str, exact_text: str, task_id: str) -> None: ...

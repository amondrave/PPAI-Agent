from typing import Protocol

from ppai.capture.domain.entities import TaskState
from ppai.decision.domain.entities import ExecutionCycle


class TaskStateQueryRepository(Protocol):
    """Read-only query interface over tasks — used by DecisionService."""

    def list_pending(self, user_id: str) -> list[TaskState]: ...

    def get_by_id(self, user_id: str, task_id: str) -> TaskState | None: ...

    def save(self, task: TaskState) -> None: ...


class CycleRepository(Protocol):
    def get_active(self, user_id: str, date: str) -> ExecutionCycle | None: ...

    def save(self, cycle: ExecutionCycle) -> None: ...

    def update_top3(self, cycle_id: str, top3_task_ids: list[str]) -> None: ...

    def increment_reorders(self, cycle_id: str) -> None: ...

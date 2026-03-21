from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ppai.shared.domain.base_entity import generate_id
from ppai.decision.domain.value_objects import CycleStatus


@dataclass
class ExecutionCycle:
    user_id: str
    date: str  # YYYY-MM-DD — one cycle per user per day
    status: CycleStatus = CycleStatus.ACTIVE
    top3_task_ids: list[str] = field(default_factory=list)
    manual_reorders: int = 0
    cycle_id: str = field(default_factory=generate_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None


@dataclass(frozen=True)
class PriorityScore:
    """Value object — computed in memory, never persisted directly."""
    task_id: str
    urgency_score: int
    age_score: int
    snooze_score: int
    total_score: int
    explanation: str


@dataclass(frozen=True)
class Top3Result:
    """Value object — result of a single Top 3 evaluation."""
    cycle_id: str
    user_id: str
    ranked_scores: tuple[PriorityScore, ...]  # 0–3 items, ordered by rank
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_empty(self) -> bool:
        return len(self.ranked_scores) == 0

    def task_ids(self) -> list[str]:
        return [s.task_id for s in self.ranked_scores]

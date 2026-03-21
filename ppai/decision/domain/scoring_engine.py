from __future__ import annotations

from datetime import datetime, timezone

from ppai.capture.domain.entities import TaskState
from ppai.decision.domain.entities import PriorityScore
from ppai.decision.domain.scoring_rules import (
    AGE_SCORE_MAX_DAYS,
    SNOOZE_SCORE_MAX,
    SNOOZE_SCORE_MULTIPLIER,
    URGENCY_SCORE_24H,
    URGENCY_SCORE_72H,
    URGENCY_SCORE_FAR,
    URGENCY_SCORE_NONE,
    URGENCY_THRESHOLD_24H,
    URGENCY_THRESHOLD_72H,
)


class ScoringEngine:
    """Pure scoring engine — no I/O, no state, no side effects.

    All temporal inputs are passed explicitly so tests can fix `now`
    without monkey-patching datetime.
    """

    def score(self, task: TaskState, now: datetime) -> PriorityScore:
        urgency = self._urgency_score(task.deadline, now)
        age = self._age_score(task.updated_at, now)
        snooze = self._snooze_score(task.snooze_count)
        explanation = self._build_explanation(urgency, age, snooze, task)
        return PriorityScore(
            task_id=task.task_id,
            urgency_score=urgency,
            age_score=age,
            snooze_score=snooze,
            total_score=urgency + age + snooze,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _urgency_score(self, deadline: datetime | None, now: datetime) -> int:
        if deadline is None:
            return URGENCY_SCORE_NONE

        # Normalise both to UTC for comparison
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        hours_remaining = (deadline - now).total_seconds() / 3600

        if hours_remaining <= URGENCY_THRESHOLD_24H:
            return URGENCY_SCORE_24H
        if hours_remaining <= URGENCY_THRESHOLD_72H:
            return URGENCY_SCORE_72H
        return URGENCY_SCORE_FAR

    def _age_score(self, updated_at: datetime, now: datetime) -> int:
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        days = max(0, (now - updated_at).days)
        return min(days, AGE_SCORE_MAX_DAYS)

    def _snooze_score(self, snooze_count: int) -> int:
        return min(snooze_count * SNOOZE_SCORE_MULTIPLIER, SNOOZE_SCORE_MAX)

    def _build_explanation(
        self,
        urgency: int,
        age: int,
        snooze: int,
        task: TaskState,
    ) -> str:
        parts: list[str] = []

        # Urgency part
        if urgency == URGENCY_SCORE_24H:
            parts.append("deadline hoy")
        elif urgency == URGENCY_SCORE_72H:
            parts.append("deadline en 2-3 días")
        elif urgency == URGENCY_SCORE_FAR:
            parts.append("deadline lejano")
        else:
            parts.append("sin deadline")

        # Age part (only show if > 0)
        if age > 0:
            parts.append(f"{age} {'día' if age == 1 else 'días'} pendiente")

        # Snooze part (only show if > 0)
        if snooze > 0:
            count = task.snooze_count
            parts.append(f"pospuesta {count} {'vez' if count == 1 else 'veces'}")

        return " + ".join(parts)

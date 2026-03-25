from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.application.ports import CycleRepository, TaskStateQueryRepository
from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.decision.domain.exceptions import TaskNotInTop3Error
from ppai.decision.domain.scoring_engine import ScoringEngine
from ppai.decision.domain.scoring_rules import TOP3_CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

_TOP3_MAX = 3
_CLARIFY_QUESTIONS = [
    "¿Qué necesitas para avanzar con esta tarea? (a) Más información  (b) Decidir algo primero",
    "¿Qué te detiene? (a) Depende de alguien  (b) No sé por dónde empezar",
]


@dataclass
class _CacheEntry:
    result: Top3Result
    expires_at: datetime


class DecisionService:
    """Orchestrates the Top 3 decision flow (BR-DEC-01..10)."""

    def __init__(
        self,
        task_repo: TaskStateQueryRepository,
        cycle_repo: CycleRepository,
        scoring_engine: ScoringEngine,
    ) -> None:
        self._task_repo = task_repo
        self._cycle_repo = cycle_repo
        self._engine = scoring_engine
        self._cache: dict[str, _CacheEntry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_top3(self, user_id: str, now: datetime | None = None) -> Top3Result:
        """Return the ranked Top 3 for *user_id*.

        Cache hit returns cached result.  On miss: queries DB, scores tasks,
        transitions statuses, updates the ExecutionCycle, and caches result.

        *now* is injectable for deterministic testing; defaults to UTC wall clock.
        """
        cached = self._get_cached(user_id)
        if cached is not None:
            logger.info("top3.cache_hit", extra={"user_id": user_id})
            return cached

        now = now or datetime.now(timezone.utc)
        today = now.date()

        # BR-DEC-01 — only pending tasks are eligible
        pending_tasks = self._task_repo.list_pending(user_id)

        if pending_tasks:
            # BR-DEC-02 — score each eligible task
            scores = [self._engine.score(task, now) for task in pending_tasks]

            # BR-DEC-03 — tie-breaking: deadline ASC (null last), createdAt ASC
            task_by_id = {t.task_id: t for t in pending_tasks}
            scores.sort(key=lambda s: self._sort_key(s, task_by_id))

            # BR-DEC-04 — select top N (max 3)
            top_scores = scores[:_TOP3_MAX]
            ranked = tuple(top_scores)

            # BR-DEC-04 — transition selected tasks: pending → prioritized
            for score in top_scores:
                task = task_by_id[score.task_id]
                task.status = TaskStatus.PRIORITIZED
                task.updated_at = now
                self._task_repo.save(task)
        else:
            # Re-show already prioritized tasks (no status change)
            prioritized_tasks = self._task_repo.list_prioritized(user_id)
            scores = [self._engine.score(task, now) for task in prioritized_tasks]
            task_by_id = {t.task_id: t for t in prioritized_tasks}
            scores.sort(key=lambda s: self._sort_key(s, task_by_id))
            top_scores = scores[:_TOP3_MAX]
            ranked = tuple(top_scores)

        # BR-DEC-08 — register in ExecutionCycle (best effort)
        cycle = self._get_or_create_cycle(user_id, today)
        top3_ids = [s.task_id for s in top_scores]
        try:
            self._cycle_repo.update_top3(cycle.cycle_id, top3_ids)
        except Exception:
            logger.warning(
                "top3.cycle_update_failed",
                extra={"user_id": user_id},
                exc_info=True,
            )

        result = Top3Result(
            cycle_id=cycle.cycle_id,
            user_id=user_id,
            ranked_scores=ranked,
            generated_at=now,
        )
        self._set_cache(user_id, result)
        logger.info(
            "top3.computed",
            extra={"user_id": user_id, "count": len(ranked), "task_ids": top3_ids},
        )
        return result

    def clarify(self, task_id: str, user_id: str) -> str:
        """Initiate clarification for *task_id* (BR-DEC-10).

        Transitions task to needs_clarification and returns the question to send.
        """
        task = self._task_repo.get_by_id(user_id, task_id)
        if task is None:
            logger.warning(
                "clarify.task_not_found",
                extra={"task_id": task_id, "user_id": user_id},
            )
            return "No encontré esa tarea. ¿Puedes intentarlo de nuevo?"

        task.status = TaskStatus.NEEDS_CLARIFICATION
        task.updated_at = datetime.now(timezone.utc)
        self._task_repo.save(task)
        self.invalidate_cache(user_id)

        logger.info("clarify.initiated", extra={"task_id": task_id, "user_id": user_id})
        return _CLARIFY_QUESTIONS[0]

    def reorder(self, user_id: str, task_id: str) -> Top3Result:
        """Move *task_id* to position #1 in the current Top 3 (BR-DEC-09).

        Does not change scores — only reorders presentation.
        """
        cached = self._get_cached(user_id)
        if cached is None or task_id not in cached.task_ids():
            raise TaskNotInTop3Error(f"Task {task_id} is not in the current Top 3")

        scores = list(cached.ranked_scores)
        idx = next(i for i, s in enumerate(scores) if s.task_id == task_id)
        if idx == 0:
            return cached  # already first

        # Move to front without changing scores
        target = scores.pop(idx)
        scores.insert(0, target)

        now = datetime.now(timezone.utc)
        new_result = Top3Result(
            cycle_id=cached.cycle_id,
            user_id=user_id,
            ranked_scores=tuple(scores),
            generated_at=now,
        )
        self._set_cache(user_id, new_result)

        # Update cycle counter (best effort)
        try:
            self._cycle_repo.increment_reorders(cached.cycle_id)
        except Exception:
            logger.warning(
                "reorder.cycle_update_failed",
                extra={"user_id": user_id},
                exc_info=True,
            )

        logger.info(
            "top3.reordered",
            extra={"user_id": user_id, "task_id": task_id, "from_position": idx + 1},
        )
        return new_result

    def invalidate_cache(self, user_id: str) -> None:
        self._cache.pop(user_id, None)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_cached(self, user_id: str) -> Top3Result | None:
        entry = self._cache.get(user_id)
        if entry and datetime.now(timezone.utc) < entry.expires_at:
            return entry.result
        return None

    def _set_cache(self, user_id: str, result: Top3Result) -> None:
        self._cache[user_id] = _CacheEntry(
            result=result,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=TOP3_CACHE_TTL_SECONDS),
        )

    def _get_or_create_cycle(self, user_id: str, today: date) -> ExecutionCycle:
        today_str = today.isoformat()
        cycle = self._cycle_repo.get_active(user_id, today_str)
        if cycle is None:
            cycle = ExecutionCycle(
                user_id=user_id,
                date=today_str,
            )
            self._cycle_repo.save(cycle)
            logger.info(
                "cycle.created_fallback",
                extra={"user_id": user_id, "cycle_id": cycle.cycle_id},
            )
        return cycle

    @staticmethod
    def _sort_key(score: PriorityScore, task_by_id: dict[str, TaskState]):
        task = task_by_id[score.task_id]
        # Primary: highest score first
        # Secondary: deadline ASC (null = far future sentinel)
        # Tertiary: created_at ASC (FIFO)
        deadline_ts = (
            task.deadline.timestamp()
            if task.deadline is not None
            else float("inf")
        )
        return (-score.total_score, deadline_ts, task.created_at.timestamp())

"""Unit tests for DecisionService — BR-DEC-01..10, DP-10, DP-13.

Uses in-memory fake repositories — no mocks, no DB, no I/O.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.application.decision_service import DecisionService
from ppai.decision.domain.entities import ExecutionCycle, Top3Result
from ppai.decision.domain.exceptions import TaskNotInTop3Error
from ppai.decision.domain.scoring_engine import ScoringEngine
from ppai.decision.domain.value_objects import CycleStatus

# ---------------------------------------------------------------------------
# Fake repositories (in-memory)
# ---------------------------------------------------------------------------

class FakeTaskRepo:
    def __init__(self, tasks: list[TaskState] | None = None):
        self._tasks: dict[str, TaskState] = {t.task_id: t for t in (tasks or [])}

    def list_pending(self, user_id: str) -> list[TaskState]:
        return [
            t for t in self._tasks.values()
            if t.user_id == user_id and t.status == TaskStatus.PENDING
        ]

    def get_by_id(self, user_id: str, task_id: str) -> TaskState | None:
        t = self._tasks.get(task_id)
        return t if t and t.user_id == user_id else None

    def save(self, task: TaskState) -> None:
        self._tasks[task.task_id] = task


class FakeCycleRepo:
    def __init__(self):
        self._cycles: dict[str, ExecutionCycle] = {}
        self.saved: list[ExecutionCycle] = []
        self.top3_updates: list[tuple[str, list[str]]] = []
        self.reorder_increments: list[str] = []

    def get_active(self, user_id: str, date: str) -> ExecutionCycle | None:
        return next(
            (
                c for c in self._cycles.values()
                if c.user_id == user_id and c.date == date and c.status == CycleStatus.ACTIVE
            ),
            None,
        )

    def save(self, cycle: ExecutionCycle) -> None:
        self._cycles[cycle.cycle_id] = cycle
        self.saved.append(cycle)

    def update_top3(self, cycle_id: str, top3_task_ids: list[str]) -> None:
        self.top3_updates.append((cycle_id, top3_task_ids))
        if cycle_id in self._cycles:
            self._cycles[cycle_id].top3_task_ids = top3_task_ids

    def increment_reorders(self, cycle_id: str) -> None:
        self.reorder_increments.append(cycle_id)
        if cycle_id in self._cycles:
            self._cycles[cycle_id].manual_reorders += 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 3, 21, 12, 0, 0, tzinfo=timezone.utc)
TODAY = "2026-03-21"
USER = "user-test"


def make_pending_task(
    user_id: str = USER,
    snooze_count: int = 0,
    deadline: datetime | None = None,
    days_old: int = 0,
) -> TaskState:
    task = TaskState(
        user_id=user_id,
        original_text="tarea de prueba",
        normalized_text="Tarea de prueba",
        source_intent_id="intent-1",
        status=TaskStatus.PENDING,
        snooze_count=snooze_count,
        deadline=deadline,
    )
    task.updated_at = NOW - timedelta(days=days_old)
    task.created_at = NOW - timedelta(days=days_old)
    return task


def make_service(tasks=None, cycles=None) -> tuple[DecisionService, FakeTaskRepo, FakeCycleRepo]:
    task_repo = FakeTaskRepo(tasks or [])
    cycle_repo = FakeCycleRepo()
    if cycles:
        for c in cycles:
            cycle_repo._cycles[c.cycle_id] = c
    service = DecisionService(
        task_repo=task_repo,
        cycle_repo=cycle_repo,
        scoring_engine=ScoringEngine(),
    )
    return service, task_repo, cycle_repo


# ---------------------------------------------------------------------------
# get_top3
# ---------------------------------------------------------------------------

class TestGetTop3:
    def test_empty_inbox_returns_empty_result(self):
        svc, _, _ = make_service()
        result = svc.get_top3(USER)
        assert result.is_empty()

    def test_non_pending_tasks_are_excluded(self):
        """BR-DEC-01: only pending tasks eligible."""
        tasks = [
            make_pending_task(),
        ]
        tasks[0].status = TaskStatus.CAPTURED  # not pending
        svc, _, _ = make_service(tasks)
        result = svc.get_top3(USER)
        assert result.is_empty()

    def test_returns_max_3_tasks(self):
        """BR-DEC-04: max 3 selected."""
        tasks = [make_pending_task() for _ in range(5)]
        svc, _, _ = make_service(tasks)
        result = svc.get_top3(USER)
        assert len(result.ranked_scores) == 3

    def test_returns_all_when_fewer_than_3(self):
        """BR-DEC-04: if fewer than 3 eligible, return all."""
        tasks = [make_pending_task(), make_pending_task()]
        svc, _, _ = make_service(tasks)
        result = svc.get_top3(USER)
        assert len(result.ranked_scores) == 2

    def test_selected_tasks_transition_to_prioritized(self):
        """BR-DEC-04: pending → prioritized for selected tasks."""
        tasks = [make_pending_task() for _ in range(2)]
        svc, task_repo, _ = make_service(tasks)
        result = svc.get_top3(USER)

        for task_id in result.task_ids():
            task = task_repo.get_by_id(USER, task_id)
            assert task.status == TaskStatus.PRIORITIZED

    def test_non_selected_tasks_stay_pending(self):
        """BR-DEC-04: non-selected tasks remain pending."""
        tasks = [make_pending_task() for _ in range(5)]
        svc, task_repo, _ = make_service(tasks)
        result = svc.get_top3(USER)

        selected_ids = set(result.task_ids())
        all_ids = {t.task_id for t in tasks}
        non_selected = all_ids - selected_ids

        for task_id in non_selected:
            task = task_repo.get_by_id(USER, task_id)
            assert task.status == TaskStatus.PENDING

    def test_higher_score_ranks_first(self):
        """BR-DEC-02: highest totalScore → position #1."""
        low = make_pending_task(snooze_count=0, days_old=0)
        high = make_pending_task(snooze_count=5, days_old=7, deadline=NOW + timedelta(hours=10))
        svc, _, _ = make_service([low, high])
        result = svc.get_top3(USER)
        assert result.ranked_scores[0].task_id == high.task_id

    def test_tie_breaking_by_deadline(self):
        """BR-DEC-03: equal score → deadline ASC."""
        # Both tasks have same snooze=0, age=0, no deadline → same score (3)
        # except one has a near deadline → higher urgency, but here we force same score manually
        # Easiest: two tasks with no deadline (score=3), different createdAt to verify FIFO
        older = make_pending_task()
        older.created_at = NOW - timedelta(hours=2)
        newer = make_pending_task()
        newer.created_at = NOW - timedelta(hours=1)

        svc, _, _ = make_service([newer, older])
        result = svc.get_top3(USER)
        # older task should come first (FIFO tie-breaking)
        assert result.ranked_scores[0].task_id == older.task_id

    def test_tie_breaking_deadline_before_fifo(self):
        """BR-DEC-03: deadline closer beats older created_at."""
        # same score via same snooze+age, but one has closer deadline
        near_deadline = make_pending_task(deadline=NOW + timedelta(hours=48))
        far_deadline = make_pending_task(deadline=NOW + timedelta(hours=60))
        near_deadline.created_at = NOW - timedelta(hours=1)   # newer
        far_deadline.created_at = NOW - timedelta(hours=10)   # older (would win by FIFO)

        svc, _, _ = make_service([near_deadline, far_deadline])
        result = svc.get_top3(USER)
        # both have urgencyScore=7 (within 72h), near_deadline wins tie
        assert result.ranked_scores[0].task_id == near_deadline.task_id

    def test_registers_top3_in_cycle(self):
        """BR-DEC-08: top3TaskIds updated in ExecutionCycle."""
        tasks = [make_pending_task() for _ in range(2)]
        svc, _, cycle_repo = make_service(tasks)
        result = svc.get_top3(USER)

        assert len(cycle_repo.top3_updates) == 1
        _, updated_ids = cycle_repo.top3_updates[0]
        assert set(updated_ids) == set(result.task_ids())


class TestTop3Cache:
    def test_cache_hit_returns_same_result(self):
        """DP-10: second call hits cache."""
        tasks = [make_pending_task()]
        svc, _, _ = make_service(tasks)
        r1 = svc.get_top3(USER)
        r2 = svc.get_top3(USER)
        assert r1 is r2

    def test_invalidate_clears_cache(self):
        """DP-10: invalidate_cache forces recompute."""
        tasks = [make_pending_task()]
        svc, task_repo, _ = make_service(tasks)
        r1 = svc.get_top3(USER)
        svc.invalidate_cache(USER)
        r2 = svc.get_top3(USER)
        assert r1 is not r2

    def test_different_users_have_independent_caches(self):
        t1 = make_pending_task(user_id="alice")
        t2 = make_pending_task(user_id="bob")
        svc, _, _ = make_service([t1, t2])

        r_alice = svc.get_top3("alice")
        r_bob = svc.get_top3("bob")
        assert r_alice.task_ids() != r_bob.task_ids()


class TestCycleFallback:
    def test_cycle_created_if_not_exists(self):
        """DP-13: UOW-02 creates cycle in fallback mode."""
        tasks = [make_pending_task()]
        svc, _, cycle_repo = make_service(tasks)
        svc.get_top3(USER, now=NOW)
        assert len(cycle_repo.saved) == 1

    def test_existing_cycle_not_duplicated(self):
        """DP-13: existing active cycle is reused."""
        existing = ExecutionCycle(user_id=USER, date=TODAY)
        tasks = [make_pending_task()]
        svc, _, cycle_repo = make_service(tasks, cycles=[existing])
        svc.get_top3(USER, now=NOW)
        # No new cycle should be created
        assert len(cycle_repo.saved) == 0


# ---------------------------------------------------------------------------
# clarify
# ---------------------------------------------------------------------------

class TestClarify:
    def test_clarify_transitions_to_needs_clarification(self):
        """BR-DEC-10: prioritized → needs_clarification."""
        task = make_pending_task()
        task.status = TaskStatus.PRIORITIZED
        svc, task_repo, _ = make_service([task])
        svc.clarify(task.task_id, USER)

        updated = task_repo.get_by_id(USER, task.task_id)
        assert updated.status == TaskStatus.NEEDS_CLARIFICATION

    def test_clarify_returns_question_string(self):
        task = make_pending_task()
        svc, _, _ = make_service([task])
        question = svc.clarify(task.task_id, USER)
        assert isinstance(question, str)
        assert len(question) > 0

    def test_clarify_invalidates_cache(self):
        task = make_pending_task()
        svc, _, _ = make_service([task])
        r1 = svc.get_top3(USER)
        svc.clarify(task.task_id, USER)
        r2 = svc.get_top3(USER)
        assert r1 is not r2

    def test_clarify_unknown_task_returns_message(self):
        svc, _, _ = make_service()
        response = svc.clarify("nonexistent-id", USER)
        assert "No encontré" in response


# ---------------------------------------------------------------------------
# reorder
# ---------------------------------------------------------------------------

class TestReorder:
    def _setup_top3(self) -> tuple[DecisionService, list[TaskState]]:
        # Create 3 tasks with different scores so order is predictable
        t1 = make_pending_task(snooze_count=5)   # highest score
        t2 = make_pending_task(snooze_count=3)
        t3 = make_pending_task(snooze_count=1)   # lowest score
        svc, _, _ = make_service([t1, t2, t3])
        svc.get_top3(USER)  # populate cache
        return svc, [t1, t2, t3]

    def test_reorder_moves_task_to_position_1(self):
        """BR-DEC-09: referenced task moves to #1."""
        svc, tasks = self._setup_top3()
        # tasks[2] is #3 (lowest score)
        result = svc.reorder(USER, tasks[2].task_id)
        assert result.ranked_scores[0].task_id == tasks[2].task_id

    def test_reorder_does_not_change_scores(self):
        """BR-DEC-09: scores are preserved."""
        svc, tasks = self._setup_top3()
        before = {s.task_id: s.total_score for s in svc.get_top3(USER).ranked_scores}
        result = svc.reorder(USER, tasks[2].task_id)
        after = {s.task_id: s.total_score for s in result.ranked_scores}
        assert before == after

    def test_reorder_increments_cycle_counter(self):
        """BR-DEC-09: manualReorders +1."""
        tasks = [make_pending_task(snooze_count=i) for i in range(3)]
        svc, _, cycle_repo = make_service(tasks)
        svc.get_top3(USER)
        svc.reorder(USER, tasks[0].task_id)  # move lowest to #1 (or any)
        assert len(cycle_repo.reorder_increments) == 1

    def test_reorder_already_first_returns_same(self):
        """BR-DEC-09: no-op if task already #1."""
        svc, tasks = self._setup_top3()
        r1 = svc.get_top3(USER)
        first_id = r1.ranked_scores[0].task_id
        r2 = svc.reorder(USER, first_id)
        assert r2.ranked_scores[0].task_id == first_id

    def test_reorder_unknown_task_raises(self):
        """BR-DEC-09: raises if task not in Top 3."""
        svc, _ = self._setup_top3()
        with pytest.raises(TaskNotInTop3Error):
            svc.reorder(USER, "not-in-top3")

    def test_reorder_without_active_top3_raises(self):
        """BR-DEC-09: raises if no cached Top 3."""
        svc, _, _ = make_service()
        with pytest.raises(TaskNotInTop3Error):
            svc.reorder(USER, "any-id")

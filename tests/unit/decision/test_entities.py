"""Unit tests for UOW-02 domain entities."""
from datetime import datetime, timezone

from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.decision.domain.value_objects import CycleStatus


class TestExecutionCycle:
    def test_default_status_is_active(self):
        cycle = ExecutionCycle(user_id="u1", date="2026-03-21")
        assert cycle.status == CycleStatus.ACTIVE

    def test_default_manual_reorders_zero(self):
        cycle = ExecutionCycle(user_id="u1", date="2026-03-21")
        assert cycle.manual_reorders == 0

    def test_default_top3_task_ids_empty(self):
        cycle = ExecutionCycle(user_id="u1", date="2026-03-21")
        assert cycle.top3_task_ids == []

    def test_cycle_id_auto_generated(self):
        cycle = ExecutionCycle(user_id="u1", date="2026-03-21")
        assert len(cycle.cycle_id) == 36  # UUID format

    def test_two_cycles_have_different_ids(self):
        c1 = ExecutionCycle(user_id="u1", date="2026-03-21")
        c2 = ExecutionCycle(user_id="u1", date="2026-03-21")
        assert c1.cycle_id != c2.cycle_id

    def test_closed_at_defaults_to_none(self):
        cycle = ExecutionCycle(user_id="u1", date="2026-03-21")
        assert cycle.closed_at is None


class TestTop3Result:
    def _make_score(self, task_id: str, total: int) -> PriorityScore:
        return PriorityScore(
            task_id=task_id,
            urgency_score=total,
            age_score=0,
            snooze_score=0,
            total_score=total,
            explanation="test",
        )

    def test_is_empty_when_no_scores(self):
        result = Top3Result(cycle_id="c1", user_id="u1", ranked_scores=())
        assert result.is_empty()

    def test_is_not_empty_with_scores(self):
        score = self._make_score("t1", 10)
        result = Top3Result(cycle_id="c1", user_id="u1", ranked_scores=(score,))
        assert not result.is_empty()

    def test_task_ids_returns_ordered_list(self):
        s1 = self._make_score("t1", 15)
        s2 = self._make_score("t2", 10)
        s3 = self._make_score("t3", 5)
        result = Top3Result(cycle_id="c1", user_id="u1", ranked_scores=(s1, s2, s3))
        assert result.task_ids() == ["t1", "t2", "t3"]

    def test_frozen_immutable(self):
        result = Top3Result(cycle_id="c1", user_id="u1", ranked_scores=())
        import pytest
        with pytest.raises(Exception):
            result.cycle_id = "other"  # type: ignore[misc]

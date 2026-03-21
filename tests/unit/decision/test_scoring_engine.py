"""Unit tests for ScoringEngine — BR-DEC-02, BR-DEC-03, BR-DEC-05.

All tests are pure: no I/O, no mocks, deterministic datetime via `now` parameter.
"""
from datetime import datetime, timezone, timedelta

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.decision.domain.scoring_engine import ScoringEngine
from ppai.decision.domain.scoring_rules import (
    AGE_SCORE_MAX_DAYS,
    SNOOZE_SCORE_MAX,
    URGENCY_SCORE_24H,
    URGENCY_SCORE_72H,
    URGENCY_SCORE_FAR,
    URGENCY_SCORE_NONE,
)


NOW = datetime(2026, 3, 21, 12, 0, 0, tzinfo=timezone.utc)


def make_task(**kwargs) -> TaskState:
    defaults = dict(
        user_id="user-1",
        original_text="tarea de prueba",
        normalized_text="Tarea de prueba",
        source_intent_id="intent-1",
        snooze_count=0,
    )
    defaults.update(kwargs)
    return TaskState(**defaults)


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine()


# ---------------------------------------------------------------------------
# urgencyScore — BR-DEC-02
# ---------------------------------------------------------------------------

class TestUrgencyScore:
    def test_deadline_within_24h(self, engine):
        task = make_task(deadline=NOW + timedelta(hours=10))
        score = engine.score(task, NOW)
        assert score.urgency_score == URGENCY_SCORE_24H

    def test_deadline_exactly_24h(self, engine):
        task = make_task(deadline=NOW + timedelta(hours=24))
        score = engine.score(task, NOW)
        assert score.urgency_score == URGENCY_SCORE_24H

    def test_deadline_within_72h(self, engine):
        task = make_task(deadline=NOW + timedelta(hours=48))
        score = engine.score(task, NOW)
        assert score.urgency_score == URGENCY_SCORE_72H

    def test_deadline_exactly_72h(self, engine):
        task = make_task(deadline=NOW + timedelta(hours=72))
        score = engine.score(task, NOW)
        assert score.urgency_score == URGENCY_SCORE_72H

    def test_deadline_beyond_72h(self, engine):
        task = make_task(deadline=NOW + timedelta(hours=96))
        score = engine.score(task, NOW)
        assert score.urgency_score == URGENCY_SCORE_FAR

    def test_no_deadline(self, engine):
        task = make_task(deadline=None)
        score = engine.score(task, NOW)
        assert score.urgency_score == URGENCY_SCORE_NONE

    def test_past_deadline_treated_as_within_24h(self, engine):
        # A past deadline has hours_remaining <= 24 → max urgency
        task = make_task(deadline=NOW - timedelta(hours=1))
        score = engine.score(task, NOW)
        assert score.urgency_score == URGENCY_SCORE_24H


# ---------------------------------------------------------------------------
# ageScore — BR-DEC-02
# ---------------------------------------------------------------------------

class TestAgeScore:
    def test_zero_days_pending(self, engine):
        task = make_task()
        task.updated_at = NOW
        score = engine.score(task, NOW)
        assert score.age_score == 0

    def test_one_day_pending(self, engine):
        task = make_task()
        task.updated_at = NOW - timedelta(days=1)
        score = engine.score(task, NOW)
        assert score.age_score == 1

    def test_five_days_pending(self, engine):
        task = make_task()
        task.updated_at = NOW - timedelta(days=5)
        score = engine.score(task, NOW)
        assert score.age_score == 5

    def test_age_capped_at_max_days(self, engine):
        task = make_task()
        task.updated_at = NOW - timedelta(days=15)
        score = engine.score(task, NOW)
        assert score.age_score == AGE_SCORE_MAX_DAYS

    def test_exactly_max_days(self, engine):
        task = make_task()
        task.updated_at = NOW - timedelta(days=AGE_SCORE_MAX_DAYS)
        score = engine.score(task, NOW)
        assert score.age_score == AGE_SCORE_MAX_DAYS


# ---------------------------------------------------------------------------
# snoozeScore — BR-DEC-02
# ---------------------------------------------------------------------------

class TestSnoozeScore:
    def test_zero_snoozes(self, engine):
        task = make_task(snooze_count=0)
        score = engine.score(task, NOW)
        assert score.snooze_score == 0

    def test_one_snooze(self, engine):
        task = make_task(snooze_count=1)
        score = engine.score(task, NOW)
        assert score.snooze_score == 2

    def test_three_snoozes(self, engine):
        task = make_task(snooze_count=3)
        score = engine.score(task, NOW)
        assert score.snooze_score == 6

    def test_snooze_capped_at_max(self, engine):
        task = make_task(snooze_count=10)
        score = engine.score(task, NOW)
        assert score.snooze_score == SNOOZE_SCORE_MAX

    def test_snooze_exactly_at_cap(self, engine):
        task = make_task(snooze_count=5)
        score = engine.score(task, NOW)
        assert score.snooze_score == SNOOZE_SCORE_MAX


# ---------------------------------------------------------------------------
# totalScore — BR-DEC-02
# ---------------------------------------------------------------------------

class TestTotalScore:
    def test_total_is_sum_of_factors(self, engine):
        task = make_task(deadline=NOW + timedelta(hours=10), snooze_count=2)
        task.updated_at = NOW - timedelta(days=3)
        score = engine.score(task, NOW)
        assert score.total_score == score.urgency_score + score.age_score + score.snooze_score

    def test_minimum_possible_score(self, engine):
        # no deadline, 0 days, 0 snoozes → 3 + 0 + 0 = 3
        task = make_task(deadline=None, snooze_count=0)
        task.updated_at = NOW
        score = engine.score(task, NOW)
        assert score.total_score == 3

    def test_maximum_possible_score(self, engine):
        # deadline within 24h + 7+ days + 5+ snoozes → 10 + 7 + 10 = 27
        task = make_task(deadline=NOW + timedelta(hours=1), snooze_count=10)
        task.updated_at = NOW - timedelta(days=10)
        score = engine.score(task, NOW)
        assert score.total_score == 27


# ---------------------------------------------------------------------------
# Explanation — BR-DEC-05
# ---------------------------------------------------------------------------

class TestExplanation:
    def test_explanation_deadline_today(self, engine):
        task = make_task(deadline=NOW + timedelta(hours=5))
        score = engine.score(task, NOW)
        assert "deadline hoy" in score.explanation

    def test_explanation_no_deadline(self, engine):
        task = make_task(deadline=None)
        score = engine.score(task, NOW)
        assert "sin deadline" in score.explanation

    def test_explanation_includes_age(self, engine):
        task = make_task(deadline=None)
        task.updated_at = NOW - timedelta(days=4)
        score = engine.score(task, NOW)
        assert "4 días pendiente" in score.explanation

    def test_explanation_includes_snooze(self, engine):
        task = make_task(deadline=None, snooze_count=3)
        score = engine.score(task, NOW)
        assert "pospuesta 3 veces" in score.explanation

    def test_explanation_singular_day(self, engine):
        task = make_task(deadline=None)
        task.updated_at = NOW - timedelta(days=1)
        score = engine.score(task, NOW)
        assert "1 día pendiente" in score.explanation

    def test_explanation_singular_snooze(self, engine):
        task = make_task(deadline=None, snooze_count=1)
        score = engine.score(task, NOW)
        assert "pospuesta 1 vez" in score.explanation

    def test_explanation_omits_zero_age(self, engine):
        task = make_task(deadline=None, snooze_count=0)
        task.updated_at = NOW
        score = engine.score(task, NOW)
        assert "pendiente" not in score.explanation

    def test_explanation_omits_zero_snooze(self, engine):
        task = make_task(deadline=None, snooze_count=0)
        score = engine.score(task, NOW)
        assert "pospuesta" not in score.explanation


# ---------------------------------------------------------------------------
# Determinism — BR-DEC-02 constraint
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_input_same_output(self, engine):
        task = make_task(deadline=NOW + timedelta(hours=30), snooze_count=2)
        task.updated_at = NOW - timedelta(days=3)

        score_a = engine.score(task, NOW)
        score_b = engine.score(task, NOW)
        assert score_a == score_b

    def test_different_engines_same_result(self):
        task = make_task(deadline=NOW + timedelta(hours=30), snooze_count=1)
        task.updated_at = NOW - timedelta(days=2)

        score_a = ScoringEngine().score(task, NOW)
        score_b = ScoringEngine().score(task, NOW)
        assert score_a == score_b

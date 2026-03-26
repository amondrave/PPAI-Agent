"""Unit tests for RescueEvaluator (BR-SCHED-06..08)."""

from unittest.mock import MagicMock

import pytest

from ppai.push.application.rescue_evaluator import RescueEvaluator
from ppai.push.domain.value_objects import DailySummary, TaskSummaryItem


def _item(task_id, title, status="pending"):
    return TaskSummaryItem(task_id=task_id, title=title, status=status)


class TestRescueEvaluator:
    def test_dia_caido_triggers_rescue(self):
        summary = DailySummary(
            user_id="u1",
            date="2026-03-27",
            completed_tasks=[],
            pending_tasks=[_item("t1", "Write report")],
        )
        evaluator = RescueEvaluator()
        result = evaluator.evaluate(summary)
        assert result is not None
        assert result.key_task.task_id == "t1"
        assert "5 minutos" in result.micro_action
        assert result.tone == "empathetic"

    def test_productive_day_no_rescue(self):
        summary = DailySummary(
            user_id="u1",
            date="2026-03-27",
            completed_tasks=[_item("t1", "Done", "completed")],
            pending_tasks=[_item("t2", "Still pending")],
        )
        evaluator = RescueEvaluator()
        assert evaluator.evaluate(summary) is None

    def test_no_tasks_no_rescue(self):
        summary = DailySummary(user_id="u1", date="2026-03-27")
        evaluator = RescueEvaluator()
        assert evaluator.evaluate(summary) is None

    def test_uses_top3_first_when_available(self):
        summary = DailySummary(
            user_id="u1",
            date="2026-03-27",
            completed_tasks=[],
            pending_tasks=[_item("t2", "Second")],
        )
        top3_task = MagicMock()
        top3_task.task_id = "t1"
        top3_task.normalized_text = "Top priority"

        evaluator = RescueEvaluator()
        result = evaluator.evaluate(summary, top3=[top3_task])
        assert result.key_task.task_id == "t1"
        assert "Top priority" in result.micro_action

    def test_snoozed_only_triggers_rescue(self):
        summary = DailySummary(
            user_id="u1",
            date="2026-03-27",
            completed_tasks=[],
            pending_tasks=[],
            snoozed_tasks=[_item("t3", "Snoozed thing", "snoozed")],
        )
        evaluator = RescueEvaluator()
        result = evaluator.evaluate(summary)
        assert result is not None
        assert result.key_task.task_id == "t3"

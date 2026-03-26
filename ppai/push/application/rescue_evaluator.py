"""Evaluates 'día caído' condition and generates rescue suggestion (US-10, BR-SCHED-06..08)."""

from __future__ import annotations

from typing import Optional

from ppai.push.domain.value_objects import DailySummary, RescueSuggestion, TaskSummaryItem


class RescueEvaluator:
    """Detects low-execution days and proposes a rescue micro-action."""

    def evaluate(
        self,
        summary: DailySummary,
        top3: Optional[list] = None,
    ) -> Optional[RescueSuggestion]:
        # BR-SCHED-06: día caído = 0 completed AND at least 1 pending/snoozed
        if summary.completed_tasks:
            return None

        total_remaining = len(summary.pending_tasks) + len(summary.snoozed_tasks)
        if total_remaining == 0:
            return None

        # Select key task: first from Top 3 if available, else first pending
        if top3 and len(top3) > 0:
            first = top3[0]
            key_task = TaskSummaryItem(
                task_id=getattr(first, "task_id", "unknown"),
                title=getattr(first, "normalized_text", str(first)),
                status="pending",
            )
        elif summary.pending_tasks:
            key_task = summary.pending_tasks[0]
        else:
            key_task = summary.snoozed_tasks[0]

        micro_action = f"Dedícale solo 5 minutos a: {key_task.title}"

        return RescueSuggestion(
            key_task=key_task,
            micro_action=micro_action,
            tone="empathetic",
        )

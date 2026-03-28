"""Evaluates 'día caído' condition and generates rescue suggestion (US-10, BR-SCHED-06..08)."""

from __future__ import annotations

from typing import Optional

from ppai.profile.domain.entities import UserProfile
from ppai.profile.domain.value_objects import CommunicationStyle
from ppai.push.domain.value_objects import DailySummary, RescueSuggestion, TaskSummaryItem


class RescueEvaluator:
    """Detects low-execution days and proposes a rescue micro-action."""

    def evaluate(
        self,
        summary: DailySummary,
        top3: Optional[list] = None,
        profile: Optional[UserProfile] = None,
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

        # Adapt tone to profile communication style
        style = profile.communication_style if profile else None
        if style == CommunicationStyle.GENTLE:
            micro_action = f"Si puedes, dedícale solo 5 minutos a: {key_task.title}"
            tone = "empathetic"
        elif style == CommunicationStyle.DIRECT:
            micro_action = f"5 minutos en: {key_task.title}"
            tone = "direct"
        elif style == CommunicationStyle.CONFRONTATIONAL:
            micro_action = f"Mínimo haz 5 minutos de: {key_task.title}"
            tone = "challenging"
        else:
            micro_action = f"Dedícale solo 5 minutos a: {key_task.title}"
            tone = "empathetic"

        return RescueSuggestion(
            key_task=key_task,
            micro_action=micro_action,
            tone=tone,
        )

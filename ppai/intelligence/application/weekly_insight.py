"""ER4 HU-R4.4 — LLM-enriched weekly report with insights."""

from __future__ import annotations

import logging
from typing import Optional

from ppai.intelligence.domain.entities import WeeklyInsight
from ppai.intelligence.infrastructure.anthropic_adapter import AnthropicAdapter, MODEL_SONNET
from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter
from ppai.intelligence.infrastructure.prompt_templates import (
    WEEKLY_SYSTEM,
    WEEKLY_USER,
)

logger = logging.getLogger(__name__)


class WeeklyInsightGenerator:
    """Generates weekly productivity insights using Claude Sonnet."""

    def __init__(
        self,
        adapter: AnthropicAdapter,
        rate_limiter: LLMRateLimiter,
    ) -> None:
        self._adapter = adapter
        self._rate_limiter = rate_limiter

    def generate(
        self,
        name: str,
        occupation: str,
        completed: int,
        snoozed: int,
        untouched: int,
        blocks_completed: int,
        blocks_planned: int,
        best_day: str,
        worst_day: str,
        prev_completed: int | str = "sin datos",
        top_categories: str = "",
    ) -> Optional[WeeklyInsight]:
        """Generate weekly insight. Returns None if rate limit exceeded or API fails."""
        if not self._rate_limiter.allow():
            logger.info("weekly_insight.rate_limited")
            return None

        user_prompt = WEEKLY_USER.format(
            name=name,
            occupation=occupation or "no especificada",
            completed=completed,
            snoozed=snoozed,
            untouched=untouched,
            blocks_completed=blocks_completed,
            blocks_planned=blocks_planned,
            best_day=best_day,
            worst_day=worst_day,
            prev_completed=prev_completed,
            top_categories=top_categories or "sin datos",
        )

        result = self._adapter.ask_json(
            system_prompt=WEEKLY_SYSTEM,
            user_prompt=user_prompt,
            model=MODEL_SONNET,
            max_tokens=512,
        )

        if result is None:
            return None

        return self._parse_result(result)

    def _parse_result(self, data: dict) -> Optional[WeeklyInsight]:
        try:
            return WeeklyInsight(
                what_went_well=data.get("what_went_well", ""),
                problematic_pattern=data.get("problematic_pattern", ""),
                suggestion=data.get("suggestion", ""),
                question=data.get("question", ""),
            )
        except (TypeError, ValueError) as exc:
            logger.warning("weekly_insight.parse_failed", extra={"error": str(exc)})
            return None

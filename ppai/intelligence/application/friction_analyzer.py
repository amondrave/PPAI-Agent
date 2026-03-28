"""ER4 HU-R4.3 — LLM-based friction analysis with personalized strategies."""

from __future__ import annotations

import logging
from typing import Optional

from ppai.intelligence.domain.entities import FrictionAnalysis
from ppai.intelligence.infrastructure.anthropic_adapter import AnthropicAdapter, MODEL_SONNET
from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter
from ppai.intelligence.infrastructure.prompt_templates import (
    FRICTION_SYSTEM,
    FRICTION_USER,
)

logger = logging.getLogger(__name__)


class FrictionAnalyzerLLM:
    """Analyzes stuck tasks using Claude Sonnet for deep, personalized diagnosis."""

    def __init__(
        self,
        adapter: AnthropicAdapter,
        rate_limiter: LLMRateLimiter,
    ) -> None:
        self._adapter = adapter
        self._rate_limiter = rate_limiter

    def analyze(
        self,
        task_title: str,
        days_in_top3: int,
        snooze_count: int,
        category: str = "",
        estimated_minutes: int = 30,
        occupation: str = "",
        style: str = "gentle",
        friction_notes: list[str] | None = None,
    ) -> Optional[FrictionAnalysis]:
        """Analyze a stuck task and return diagnosis + strategies.

        Returns None if rate limit exceeded or API fails (caller uses static options).
        """
        if not self._rate_limiter.allow():
            logger.info("friction_analyzer.rate_limited")
            return None

        notes_str = "; ".join(friction_notes) if friction_notes else "ninguna"

        user_prompt = FRICTION_USER.format(
            occupation=occupation or "no especificada",
            style=style,
            task_title=task_title,
            days_in_top3=days_in_top3,
            snooze_count=snooze_count,
            category=category or "sin categoria",
            friction_notes=notes_str,
            estimated_minutes=estimated_minutes,
        )

        result = self._adapter.ask_json(
            system_prompt=FRICTION_SYSTEM,
            user_prompt=user_prompt,
            model=MODEL_SONNET,
            max_tokens=512,
        )

        if result is None:
            return None

        return self._parse_result(result)

    def _parse_result(self, data: dict) -> Optional[FrictionAnalysis]:
        try:
            strategies = data.get("strategies", [])
            if not isinstance(strategies, list):
                strategies = [str(strategies)]
            strategies = strategies[:3]

            return FrictionAnalysis(
                diagnosis=data.get("diagnosis", ""),
                strategies=strategies,
                micro_action=data.get("micro_action", ""),
            )
        except (TypeError, ValueError) as exc:
            logger.warning("friction_analyzer.parse_failed", extra={"error": str(exc)})
            return None

"""ER4 HU-R4.1 — LLM-based intelligent task capture analysis."""

from __future__ import annotations

import logging
from typing import Optional

from ppai.intelligence.domain.entities import TaskAnalysis
from ppai.intelligence.infrastructure.anthropic_adapter import AnthropicAdapter, MODEL_HAIKU
from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter
from ppai.intelligence.infrastructure.prompt_templates import (
    TASK_ANALYSIS_SYSTEM,
    TASK_ANALYSIS_USER,
)

logger = logging.getLogger(__name__)

_VALID_CATEGORIES = {"work", "personal", "learning", "health", "social", "errand"}
_VALID_URGENCIES = {"high", "medium", "low"}
_VALID_MINUTES = {15, 30, 45, 60, 90, 120}


class TaskAnalyzer:
    """Analyzes captured tasks using Claude Haiku for better classification."""

    def __init__(
        self,
        adapter: AnthropicAdapter,
        rate_limiter: LLMRateLimiter,
    ) -> None:
        self._adapter = adapter
        self._rate_limiter = rate_limiter

    def analyze(self, task_text: str, occupation: str = "") -> Optional[TaskAnalysis]:
        """Analyze a task and return structured classification.

        Returns None if rate limit exceeded or API fails (caller uses regex fallback).
        """
        if not self._rate_limiter.allow():
            logger.info("task_analyzer.rate_limited")
            return None

        user_prompt = TASK_ANALYSIS_USER.format(
            occupation=occupation or "no especificada",
            task_text=task_text,
        )

        result = self._adapter.ask_json(
            system_prompt=TASK_ANALYSIS_SYSTEM,
            user_prompt=user_prompt,
            model=MODEL_HAIKU,
            max_tokens=256,
        )

        if result is None:
            return None

        return self._parse_result(result, task_text)

    def _parse_result(self, data: dict, fallback_title: str) -> Optional[TaskAnalysis]:
        """Validate and parse LLM response into TaskAnalysis."""
        try:
            category = data.get("category", "personal")
            if category not in _VALID_CATEGORIES:
                category = "personal"

            urgency = data.get("urgency", "medium")
            if urgency not in _VALID_URGENCIES:
                urgency = "medium"

            minutes = int(data.get("estimated_minutes", 30))
            if minutes not in _VALID_MINUTES:
                minutes = min(_VALID_MINUTES, key=lambda m: abs(m - minutes))

            return TaskAnalysis(
                title=data.get("title", fallback_title),
                category=category,
                estimated_minutes=minutes,
                urgency=urgency,
                context=data.get("context", ""),
            )
        except (TypeError, ValueError) as exc:
            logger.warning("task_analyzer.parse_failed", extra={"error": str(exc)})
            return None

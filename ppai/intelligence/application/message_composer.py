"""ER4 HU-R4.2 — LLM-generated messages with personality."""

from __future__ import annotations

import logging
from typing import Optional

from ppai.intelligence.domain.entities import MessageRequest
from ppai.intelligence.infrastructure.anthropic_adapter import (
    AnthropicAdapter,
    MODEL_HAIKU,
    MODEL_SONNET,
)
from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter
from ppai.intelligence.infrastructure.prompt_templates import (
    DAILY_END_USER,
    DAILY_START_USER,
    MESSAGE_SYSTEM,
    NUDGE_USER,
    get_style_description,
)

logger = logging.getLogger(__name__)

# Prohibited phrases guardrail (BR-PUSH-10)
_PROHIBITED_PHRASES = (
    "debías", "ya vas tarde", "otra vez", "no hiciste",
    "deberías", "fallaste", "no avanzaste",
)


class MessageComposer:
    """Generates contextual messages using LLM with fallback to static templates."""

    def __init__(
        self,
        adapter: AnthropicAdapter,
        rate_limiter: LLMRateLimiter,
    ) -> None:
        self._adapter = adapter
        self._rate_limiter = rate_limiter

    def compose_daily_start(self, request: MessageRequest) -> Optional[str]:
        """Generate morning message. Returns None if LLM unavailable (use static)."""
        if not self._rate_limiter.allow():
            return None

        style = request.communication_style or "gentle"
        system = MESSAGE_SYSTEM.format(
            style=style,
            style_description=get_style_description(style),
        )
        tasks_str = ", ".join(request.top3_tasks) if request.top3_tasks else "ninguna"
        stuck_str = request.stuck_task or "ninguna"

        user_prompt = DAILY_START_USER.format(
            name=request.user_name,
            tasks=tasks_str,
            stuck=stuck_str,
            yesterday_completed=request.yesterday_completed,
        )

        text = self._adapter.ask_text(
            system_prompt=system,
            user_prompt=user_prompt,
            model=MODEL_SONNET,
            max_tokens=300,
        )

        return self._sanitize(text)

    def compose_daily_end(self, request: MessageRequest) -> Optional[str]:
        """Generate end-of-day message. Returns None if LLM unavailable."""
        if not self._rate_limiter.allow():
            return None

        style = request.communication_style or "gentle"
        system = MESSAGE_SYSTEM.format(
            style=style,
            style_description=get_style_description(style),
        )
        user_prompt = DAILY_END_USER.format(
            name=request.user_name,
            completed=request.completed_today,
            pending=request.pending_today,
            snoozed=request.snoozed_today,
            blocks_completed=request.blocks_completed,
            blocks_planned=request.blocks_planned,
        )

        text = self._adapter.ask_text(
            system_prompt=system,
            user_prompt=user_prompt,
            model=MODEL_SONNET,
            max_tokens=300,
        )

        return self._sanitize(text)

    def compose_nudge(
        self,
        user_name: str,
        style: str,
        task_title: str,
        context: str = "",
    ) -> Optional[str]:
        """Generate a nudge message. Returns None if LLM unavailable."""
        if not self._rate_limiter.allow():
            return None

        system = MESSAGE_SYSTEM.format(
            style=style,
            style_description=get_style_description(style),
        )
        user_prompt = NUDGE_USER.format(
            name=user_name,
            task_title=task_title,
            context=context or "recordatorio de tarea pendiente",
        )

        text = self._adapter.ask_text(
            system_prompt=system,
            user_prompt=user_prompt,
            model=MODEL_HAIKU,
            max_tokens=150,
        )

        return self._sanitize(text)

    def _sanitize(self, text: Optional[str]) -> Optional[str]:
        """Strip prohibited phrases. Returns None if text is empty."""
        if not text:
            return None

        # Word count guard (max 150 words)
        words = text.split()
        if len(words) > 150:
            text = " ".join(words[:150])

        # Prohibited phrases check
        lower = text.lower()
        for phrase in _PROHIBITED_PHRASES:
            if phrase in lower:
                logger.warning("message_composer.prohibited_phrase", extra={"phrase": phrase})
                return None

        return text

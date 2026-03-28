"""ER4 — Anthropic API adapter with fallback support."""

from __future__ import annotations

import json
import logging
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

MODEL_HAIKU = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-5-20241022"


class AnthropicAdapter:
    """Thin wrapper around the Anthropic Messages API."""

    def __init__(self, api_key: str, timeout: float = 5.0) -> None:
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

    def ask_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = MODEL_HAIKU,
        max_tokens: int = 512,
    ) -> Optional[dict]:
        """Send a prompt and parse the response as JSON. Returns None on failure."""
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                text = "\n".join(lines).strip()
            return json.loads(text)
        except (anthropic.APIError, anthropic.APITimeoutError) as exc:
            logger.warning("anthropic.api_error", extra={"error": str(exc)})
            return None
        except (json.JSONDecodeError, IndexError, KeyError) as exc:
            logger.warning("anthropic.parse_error", extra={"error": str(exc)})
            return None

    def ask_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = MODEL_HAIKU,
        max_tokens: int = 512,
    ) -> Optional[str]:
        """Send a prompt and return raw text. Returns None on failure."""
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text.strip()
        except (anthropic.APIError, anthropic.APITimeoutError) as exc:
            logger.warning("anthropic.api_error", extra={"error": str(exc)})
            return None
        except (IndexError, KeyError) as exc:
            logger.warning("anthropic.parse_error", extra={"error": str(exc)})
            return None

"""ER4 — Daily global cap for LLM API calls (decision B: cap diario global)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

# Default: 50 calls/day keeps costs well under $20/month
DEFAULT_DAILY_CAP = 50


class LLMRateLimiter:
    """Tracks daily LLM call count and enforces a global cap.

    When the cap is exceeded, callers should fall back to static templates.
    """

    def __init__(self, daily_cap: int = DEFAULT_DAILY_CAP) -> None:
        self._daily_cap = daily_cap
        self._count = 0
        self._current_date: date | None = None

    @property
    def remaining(self) -> int:
        self._maybe_reset()
        return max(0, self._daily_cap - self._count)

    def allow(self) -> bool:
        """Check if a call is allowed and consume one slot if so."""
        self._maybe_reset()
        if self._count >= self._daily_cap:
            logger.warning(
                "llm_rate_limiter.cap_reached",
                extra={"count": self._count, "cap": self._daily_cap},
            )
            return False
        self._count += 1
        return True

    def _maybe_reset(self) -> None:
        today = datetime.now(timezone.utc).date()
        if self._current_date != today:
            self._current_date = today
            self._count = 0

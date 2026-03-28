"""Unit tests for ER4 — LLMRateLimiter."""

from unittest.mock import patch
from datetime import date

import pytest

from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter


class TestLLMRateLimiter:
    def test_allow_within_cap(self):
        limiter = LLMRateLimiter(daily_cap=3)

        assert limiter.allow() is True
        assert limiter.allow() is True
        assert limiter.allow() is True
        assert limiter.allow() is False

    def test_remaining_decreases(self):
        limiter = LLMRateLimiter(daily_cap=5)

        assert limiter.remaining == 5
        limiter.allow()
        assert limiter.remaining == 4

    def test_resets_on_new_day(self):
        limiter = LLMRateLimiter(daily_cap=1)
        limiter.allow()
        assert limiter.allow() is False

        # Simulate new day
        limiter._current_date = date(2020, 1, 1)
        assert limiter.allow() is True

    def test_zero_cap_blocks_all(self):
        limiter = LLMRateLimiter(daily_cap=0)

        assert limiter.allow() is False
        assert limiter.remaining == 0

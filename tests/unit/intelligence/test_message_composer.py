"""Unit tests for ER4 HU-R4.2 — MessageComposer."""

from unittest.mock import MagicMock

import pytest

from ppai.intelligence.application.message_composer import MessageComposer
from ppai.intelligence.domain.entities import MessageRequest
from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter


@pytest.fixture
def adapter():
    return MagicMock()


@pytest.fixture
def rate_limiter():
    return LLMRateLimiter(daily_cap=100)


@pytest.fixture
def composer(adapter, rate_limiter):
    return MessageComposer(adapter=adapter, rate_limiter=rate_limiter)


def _make_request(**kwargs):
    defaults = {
        "user_name": "Angel",
        "communication_style": "gentle",
        "occupation": "ingeniero",
    }
    defaults.update(kwargs)
    return MessageRequest(**defaults)


class TestMessageComposer:
    def test_compose_daily_start_returns_text(self, composer, adapter):
        adapter.ask_text.return_value = "Buenos dias Angel, hoy tienes 3 tareas clave."
        request = _make_request(top3_tasks=["PR review", "Deploy", "Tests"])

        result = composer.compose_daily_start(request)

        assert result is not None
        assert "Angel" in result
        adapter.ask_text.assert_called_once()

    def test_compose_daily_start_returns_none_on_failure(self, composer, adapter):
        adapter.ask_text.return_value = None

        result = composer.compose_daily_start(_make_request())

        assert result is None

    def test_compose_daily_end_returns_text(self, composer, adapter):
        adapter.ask_text.return_value = "Buen trabajo hoy Angel, completaste 3 tareas."

        result = composer.compose_daily_end(_make_request(completed_today=3))

        assert result is not None

    def test_compose_nudge_returns_text(self, composer, adapter):
        adapter.ask_text.return_value = "Angel, retoma el PR review cuando puedas."

        result = composer.compose_nudge("Angel", "gentle", "PR review")

        assert result is not None

    def test_compose_returns_none_when_rate_limited(self, adapter):
        limiter = LLMRateLimiter(daily_cap=0)
        composer = MessageComposer(adapter=adapter, rate_limiter=limiter)

        result = composer.compose_daily_start(_make_request())

        assert result is None
        adapter.ask_text.assert_not_called()

    def test_sanitize_rejects_prohibited_phrases(self, composer, adapter):
        adapter.ask_text.return_value = "Ya vas tarde con esta tarea, Angel."

        result = composer.compose_daily_start(_make_request())

        assert result is None

    def test_sanitize_truncates_long_messages(self, composer, adapter):
        adapter.ask_text.return_value = " ".join(["palabra"] * 200)

        result = composer.compose_daily_start(_make_request())

        assert result is not None
        assert len(result.split()) <= 150

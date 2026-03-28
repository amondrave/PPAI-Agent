"""Unit tests for ER4 HU-R4.4 — WeeklyInsightGenerator."""

from unittest.mock import MagicMock

import pytest

from ppai.intelligence.application.weekly_insight import WeeklyInsightGenerator
from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter


@pytest.fixture
def adapter():
    return MagicMock()


@pytest.fixture
def rate_limiter():
    return LLMRateLimiter(daily_cap=100)


@pytest.fixture
def generator(adapter, rate_limiter):
    return WeeklyInsightGenerator(adapter=adapter, rate_limiter=rate_limiter)


class TestWeeklyInsightGenerator:
    def test_generate_returns_weekly_insight(self, generator, adapter):
        adapter.ask_json.return_value = {
            "what_went_well": "Completaste 12 tareas, 50% mas que la semana pasada.",
            "problematic_pattern": "Los jueves no completaste ningun bloque por reuniones.",
            "suggestion": "Bloquea 2h sin reuniones los jueves.",
            "question": "Que reuniones del jueves podrias cancelar?",
        }

        result = generator.generate(
            name="Angel",
            occupation="ingeniero",
            completed=12,
            snoozed=3,
            untouched=2,
            blocks_completed=8,
            blocks_planned=12,
            best_day="lunes",
            worst_day="jueves",
        )

        assert result is not None
        assert "12 tareas" in result.what_went_well
        assert "jueves" in result.problematic_pattern
        assert result.suggestion != ""
        assert "?" in result.question

    def test_generate_returns_none_on_api_failure(self, generator, adapter):
        adapter.ask_json.return_value = None

        result = generator.generate(
            name="Angel", occupation="", completed=0, snoozed=0, untouched=0,
            blocks_completed=0, blocks_planned=0, best_day="?", worst_day="?",
        )

        assert result is None

    def test_generate_returns_none_when_rate_limited(self, adapter):
        limiter = LLMRateLimiter(daily_cap=0)
        generator = WeeklyInsightGenerator(adapter=adapter, rate_limiter=limiter)

        result = generator.generate(
            name="Angel", occupation="", completed=0, snoozed=0, untouched=0,
            blocks_completed=0, blocks_planned=0, best_day="?", worst_day="?",
        )

        assert result is None
        adapter.ask_json.assert_not_called()

    def test_generate_with_previous_week_data(self, generator, adapter):
        adapter.ask_json.return_value = {
            "what_went_well": "Mejoraste vs la semana pasada.",
            "problematic_pattern": "Muchas tareas pospuestas.",
            "suggestion": "Revisa tu backlog.",
            "question": "Cuales tareas ya no son relevantes?",
        }

        result = generator.generate(
            name="Angel",
            occupation="ingeniero",
            completed=10,
            snoozed=5,
            untouched=3,
            blocks_completed=6,
            blocks_planned=10,
            best_day="martes",
            worst_day="viernes",
            prev_completed=8,
        )

        assert result is not None

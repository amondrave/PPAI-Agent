"""Unit tests for ER4 HU-R4.1 — TaskAnalyzer."""

from unittest.mock import MagicMock

import pytest

from ppai.intelligence.application.task_analyzer import TaskAnalyzer
from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter


@pytest.fixture
def adapter():
    return MagicMock()


@pytest.fixture
def rate_limiter():
    return LLMRateLimiter(daily_cap=100)


@pytest.fixture
def analyzer(adapter, rate_limiter):
    return TaskAnalyzer(adapter=adapter, rate_limiter=rate_limiter)


class TestTaskAnalyzer:
    def test_analyze_returns_task_analysis(self, analyzer, adapter):
        adapter.ask_json.return_value = {
            "title": "Revisar PRs pendientes",
            "category": "work",
            "estimated_minutes": 30,
            "urgency": "medium",
            "context": "Tarea de revision de codigo",
        }

        result = analyzer.analyze("revisar los PRs pendientes", "ingeniero de software")

        assert result is not None
        assert result.title == "Revisar PRs pendientes"
        assert result.category == "work"
        assert result.estimated_minutes == 30
        assert result.urgency == "medium"
        adapter.ask_json.assert_called_once()

    def test_analyze_returns_none_on_api_failure(self, analyzer, adapter):
        adapter.ask_json.return_value = None

        result = analyzer.analyze("hacer ejercicio")

        assert result is None

    def test_analyze_returns_none_when_rate_limited(self, adapter):
        limiter = LLMRateLimiter(daily_cap=0)
        analyzer = TaskAnalyzer(adapter=adapter, rate_limiter=limiter)

        result = analyzer.analyze("tarea cualquiera")

        assert result is None
        adapter.ask_json.assert_not_called()

    def test_analyze_normalizes_invalid_category(self, analyzer, adapter):
        adapter.ask_json.return_value = {
            "title": "Algo",
            "category": "INVALID",
            "estimated_minutes": 30,
            "urgency": "medium",
        }

        result = analyzer.analyze("algo")

        assert result.category == "personal"

    def test_analyze_normalizes_invalid_urgency(self, analyzer, adapter):
        adapter.ask_json.return_value = {
            "title": "Algo",
            "category": "work",
            "estimated_minutes": 30,
            "urgency": "CRITICAL",
        }

        result = analyzer.analyze("algo")

        assert result.urgency == "medium"

    def test_analyze_snaps_estimated_minutes(self, analyzer, adapter):
        adapter.ask_json.return_value = {
            "title": "Algo",
            "category": "work",
            "estimated_minutes": 25,
            "urgency": "low",
        }

        result = analyzer.analyze("algo")

        assert result.estimated_minutes == 30  # snapped to nearest valid

    def test_analyze_with_empty_occupation(self, analyzer, adapter):
        adapter.ask_json.return_value = {
            "title": "Comprar leche",
            "category": "errand",
            "estimated_minutes": 15,
            "urgency": "low",
        }

        result = analyzer.analyze("comprar leche", "")

        assert result is not None
        assert result.category == "errand"

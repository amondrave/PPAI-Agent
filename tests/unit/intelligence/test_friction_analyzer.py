"""Unit tests for ER4 HU-R4.3 — FrictionAnalyzerLLM."""

from unittest.mock import MagicMock

import pytest

from ppai.intelligence.application.friction_analyzer import FrictionAnalyzerLLM
from ppai.intelligence.infrastructure.llm_rate_limiter import LLMRateLimiter


@pytest.fixture
def adapter():
    return MagicMock()


@pytest.fixture
def rate_limiter():
    return LLMRateLimiter(daily_cap=100)


@pytest.fixture
def analyzer(adapter, rate_limiter):
    return FrictionAnalyzerLLM(adapter=adapter, rate_limiter=rate_limiter)


class TestFrictionAnalyzerLLM:
    def test_analyze_returns_friction_analysis(self, analyzer, adapter):
        adapter.ask_json.return_value = {
            "diagnosis": "La tarea es demasiado ambigua, no tienes claro el primer paso.",
            "strategies": [
                "Lee solo la documentacion del endpoint por 15 min",
                "Escribe el test antes que el codigo",
                "Pide pair programming a un companero",
            ],
            "micro_action": "Abre el archivo y lee las primeras 20 lineas del endpoint.",
        }

        result = analyzer.analyze(
            task_title="Refactorizar API de pagos",
            days_in_top3=5,
            snooze_count=2,
            category="work",
            occupation="ingeniero de software",
        )

        assert result is not None
        assert "ambigua" in result.diagnosis
        assert len(result.strategies) == 3
        assert result.micro_action != ""

    def test_analyze_returns_none_on_api_failure(self, analyzer, adapter):
        adapter.ask_json.return_value = None

        result = analyzer.analyze("tarea", days_in_top3=3, snooze_count=1)

        assert result is None

    def test_analyze_returns_none_when_rate_limited(self, adapter):
        limiter = LLMRateLimiter(daily_cap=0)
        analyzer = FrictionAnalyzerLLM(adapter=adapter, rate_limiter=limiter)

        result = analyzer.analyze("tarea", days_in_top3=3, snooze_count=1)

        assert result is None
        adapter.ask_json.assert_not_called()

    def test_analyze_includes_friction_notes(self, analyzer, adapter):
        adapter.ask_json.return_value = {
            "diagnosis": "Ya intentaste dividirla sin exito.",
            "strategies": ["Estrategia 1", "Estrategia 2", "Estrategia 3"],
            "micro_action": "Habla con tu lead.",
        }

        result = analyzer.analyze(
            task_title="Migrar base de datos",
            days_in_top3=7,
            snooze_count=3,
            friction_notes=["No tengo acceso al servidor", "Necesito credenciales"],
        )

        assert result is not None
        # Verify the friction_notes were passed in the prompt
        call_args = adapter.ask_json.call_args
        assert "No tengo acceso al servidor" in call_args.kwargs.get("user_prompt", call_args[1].get("user_prompt", ""))

    def test_analyze_truncates_strategies_to_3(self, analyzer, adapter):
        adapter.ask_json.return_value = {
            "diagnosis": "Bloqueo.",
            "strategies": ["A", "B", "C", "D", "E"],
            "micro_action": "Micro.",
        }

        result = analyzer.analyze("tarea", days_in_top3=3, snooze_count=0)

        assert len(result.strategies) == 3

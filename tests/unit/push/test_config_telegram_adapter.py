"""Unit tests for ConfigTelegramAdapter (/config command)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.infrastructure.config_telegram_adapter import ConfigTelegramAdapter


def _make_update_and_context(user_id: str = "123", args: list[str] | None = None):
    update = AsyncMock()
    update.effective_user = MagicMock()
    update.effective_user.id = int(user_id)
    update.message = AsyncMock()

    context = MagicMock()
    context.args = args or []

    return update, context


class TestConfigShowCurrent:
    @pytest.mark.asyncio
    async def test_no_args_shows_defaults(self):
        prefs_repo = MagicMock()
        prefs_repo.get.return_value = None
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=[])
        await adapter.config_handler(update, context)

        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "America/Bogota" in text
        assert "3" in text
        assert "No configurada" in text

    @pytest.mark.asyncio
    async def test_no_args_shows_existing_prefs(self):
        prefs = UserNudgePreferences(
            user_id="123",
            timezone="America/Mexico_City",
            max_nudges_per_day=5,
            silence_start="22:00",
            silence_end="08:00",
        )
        prefs_repo = MagicMock()
        prefs_repo.get.return_value = prefs
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=[])
        await adapter.config_handler(update, context)

        text = update.message.reply_text.call_args[0][0]
        assert "Mexico_City" in text
        assert "5" in text
        assert "22:00 - 08:00" in text


class TestConfigSilence:
    @pytest.mark.asyncio
    async def test_valid_silence_window(self):
        prefs_repo = MagicMock()
        prefs_repo.get.return_value = None
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["silencio", "22:00-08:00"])
        await adapter.config_handler(update, context)

        prefs_repo.save.assert_called_once()
        saved = prefs_repo.save.call_args[0][0]
        assert saved.silence_start == "22:00"
        assert saved.silence_end == "08:00"

        text = update.message.reply_text.call_args[0][0]
        assert "22:00 - 08:00" in text

    @pytest.mark.asyncio
    async def test_invalid_silence_format(self):
        prefs_repo = MagicMock()
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["silencio", "bad"])
        await adapter.config_handler(update, context)

        prefs_repo.save.assert_not_called()
        text = update.message.reply_text.call_args[0][0]
        assert "Formato inválido" in text

    @pytest.mark.asyncio
    async def test_invalid_time_values(self):
        prefs_repo = MagicMock()
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["silencio", "25:00-08:00"])
        await adapter.config_handler(update, context)

        prefs_repo.save.assert_not_called()


class TestConfigNudges:
    @pytest.mark.asyncio
    async def test_valid_nudge_count(self):
        prefs_repo = MagicMock()
        prefs_repo.get.return_value = None
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["nudges", "5"])
        await adapter.config_handler(update, context)

        saved = prefs_repo.save.call_args[0][0]
        assert saved.max_nudges_per_day == 5

    @pytest.mark.asyncio
    async def test_nudge_count_too_low(self):
        prefs_repo = MagicMock()
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["nudges", "0"])
        await adapter.config_handler(update, context)

        prefs_repo.save.assert_not_called()
        text = update.message.reply_text.call_args[0][0]
        assert "entre 1 y 10" in text

    @pytest.mark.asyncio
    async def test_nudge_count_too_high(self):
        prefs_repo = MagicMock()
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["nudges", "11"])
        await adapter.config_handler(update, context)

        prefs_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_nudge_count_not_a_number(self):
        prefs_repo = MagicMock()
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["nudges", "abc"])
        await adapter.config_handler(update, context)

        prefs_repo.save.assert_not_called()


class TestConfigTimezone:
    @pytest.mark.asyncio
    async def test_valid_timezone(self):
        prefs_repo = MagicMock()
        prefs_repo.get.return_value = None
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["timezone", "America/Mexico_City"])
        await adapter.config_handler(update, context)

        saved = prefs_repo.save.call_args[0][0]
        assert saved.timezone == "America/Mexico_City"

    @pytest.mark.asyncio
    async def test_invalid_timezone(self):
        prefs_repo = MagicMock()
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["timezone", "Invalid/Zone"])
        await adapter.config_handler(update, context)

        prefs_repo.save.assert_not_called()
        text = update.message.reply_text.call_args[0][0]
        assert "no válida" in text


class TestConfigHelp:
    @pytest.mark.asyncio
    async def test_unknown_subcommand_shows_help(self):
        prefs_repo = MagicMock()
        adapter = ConfigTelegramAdapter(prefs_repo)

        update, context = _make_update_and_context(args=["unknown"])
        await adapter.config_handler(update, context)

        text = update.message.reply_text.call_args[0][0]
        assert "Configuración de recordatorios" in text

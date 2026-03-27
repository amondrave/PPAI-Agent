"""Unit tests for ConfigTelegramAdapter UOW-05 — new subcommands."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

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


def _make_adapter(prefs=None):
    prefs_repo = MagicMock()
    prefs_repo.get.return_value = prefs
    prefs_repo.save = MagicMock()
    return ConfigTelegramAdapter(prefs_repo), prefs_repo


class TestConfigInicio:
    @pytest.mark.asyncio
    async def test_set_inicio_valid(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["inicio", "09:00"])
        await adapter.config_handler(update, ctx)

        saved = prefs_repo.save.call_args[0][0]
        assert saved.daily_start_time == "09:00"
        text = update.message.reply_text.call_args[0][0]
        assert "09:00" in text

    @pytest.mark.asyncio
    async def test_set_inicio_invalid_format(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["inicio", "25:00"])
        await adapter.config_handler(update, ctx)

        prefs_repo.save.assert_not_called()
        text = update.message.reply_text.call_args[0][0]
        assert "inválido" in text.lower()


class TestConfigCierre:
    @pytest.mark.asyncio
    async def test_set_cierre_valid(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["cierre", "18:00"])
        await adapter.config_handler(update, ctx)

        saved = prefs_repo.save.call_args[0][0]
        assert saved.daily_end_time == "18:00"

    @pytest.mark.asyncio
    async def test_set_cierre_invalid(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["cierre", "bad"])
        await adapter.config_handler(update, ctx)
        prefs_repo.save.assert_not_called()


class TestConfigZenIntervalo:
    @pytest.mark.asyncio
    async def test_set_zen_intervalo_valid(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["zen_intervalo", "10"])
        await adapter.config_handler(update, ctx)

        saved = prefs_repo.save.call_args[0][0]
        assert saved.zen_interval_minutes == 10

    @pytest.mark.asyncio
    async def test_set_zen_intervalo_below_range(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["zen_intervalo", "3"])
        await adapter.config_handler(update, ctx)
        prefs_repo.save.assert_not_called()
        text = update.message.reply_text.call_args[0][0]
        assert "5" in text and "60" in text

    @pytest.mark.asyncio
    async def test_set_zen_intervalo_above_range(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["zen_intervalo", "100"])
        await adapter.config_handler(update, ctx)
        prefs_repo.save.assert_not_called()


class TestConfigZenMax:
    @pytest.mark.asyncio
    async def test_set_zen_max_valid(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["zen_max", "20"])
        await adapter.config_handler(update, ctx)

        saved = prefs_repo.save.call_args[0][0]
        assert saved.zen_max_nudges == 20

    @pytest.mark.asyncio
    async def test_set_zen_max_out_of_range(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["zen_max", "0"])
        await adapter.config_handler(update, ctx)
        prefs_repo.save.assert_not_called()


class TestConfigMotivacion:
    @pytest.mark.asyncio
    async def test_set_motivacion_valid(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["motivacion", "Hoy", "va", "a", "ser", "genial"])
        await adapter.config_handler(update, ctx)

        saved = prefs_repo.save.call_args[0][0]
        assert saved.motivational_message == "Hoy va a ser genial"

    @pytest.mark.asyncio
    async def test_sanitize_strips_html(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["motivacion", "<b>bold</b>", "text"])
        await adapter.config_handler(update, ctx)

        saved = prefs_repo.save.call_args[0][0]
        assert "<" not in saved.motivational_message
        assert "bold text" in saved.motivational_message

    @pytest.mark.asyncio
    async def test_reject_urls(self):
        adapter, prefs_repo = _make_adapter()
        update, ctx = _make_update_and_context(args=["motivacion", "visit", "https://evil.com"])
        await adapter.config_handler(update, ctx)

        prefs_repo.save.assert_not_called()
        text = update.message.reply_text.call_args[0][0]
        assert "URLs" in text

    @pytest.mark.asyncio
    async def test_reject_too_long(self):
        adapter, prefs_repo = _make_adapter()
        long_msg = "A" * 101
        update, ctx = _make_update_and_context(args=["motivacion", long_msg])
        await adapter.config_handler(update, ctx)
        prefs_repo.save.assert_not_called()


class TestConfigDisplayUow05:
    @pytest.mark.asyncio
    async def test_display_shows_new_fields(self):
        prefs = UserNudgePreferences(
            user_id="123",
            daily_start_time="09:00",
            daily_end_time="17:00",
            zen_active=True,
            zen_interval_minutes=10,
            zen_max_nudges=20,
            motivational_message="Vamos!",
        )
        adapter, _ = _make_adapter(prefs=prefs)
        update, ctx = _make_update_and_context(args=[])
        await adapter.config_handler(update, ctx)

        text = update.message.reply_text.call_args[0][0]
        assert "09:00" in text
        assert "17:00" in text
        assert "Activo" in text
        assert "10 min" in text
        assert "20" in text
        assert "Vamos!" in text

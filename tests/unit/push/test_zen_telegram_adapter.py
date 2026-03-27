"""Unit tests for ZenTelegramAdapter (/zen command)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.infrastructure.zen_telegram_adapter import ZenTelegramAdapter


def _make_update_and_context(user_id: str = "123", args: list[str] | None = None):
    update = AsyncMock()
    update.effective_user = MagicMock()
    update.effective_user.id = int(user_id)
    update.message = AsyncMock()

    context = MagicMock()
    context.args = args or []

    return update, context


def _make_adapter(prefs=None, cycle=None):
    prefs_repo = MagicMock()
    prefs_repo.get.return_value = prefs
    prefs_repo.save = MagicMock()

    cycle_repo = MagicMock()
    cycle_repo.get_active.return_value = cycle
    cycle_repo.record_nudge_event = MagicMock()

    zen_manager = ZenSessionManager()

    adapter = ZenTelegramAdapter(prefs_repo, cycle_repo, zen_manager)
    return adapter, prefs_repo, cycle_repo, zen_manager


class TestZenActivate:
    @pytest.mark.asyncio
    async def test_zen_activates_mode(self):
        adapter, prefs_repo, _, zen_mgr = _make_adapter()
        update, context = _make_update_and_context(args=[])
        await adapter.zen_handler(update, context)

        # Prefs saved with zen_active=True
        prefs_repo.save.assert_called_once()
        saved = prefs_repo.save.call_args[0][0]
        assert saved.zen_active is True

        # Session created in manager
        session = zen_mgr.get("123")
        assert session is not None

        # Response in Spanish
        text = update.message.reply_text.call_args[0][0]
        assert "Modo zen activado" in text

    @pytest.mark.asyncio
    async def test_zen_already_active(self):
        prefs = UserNudgePreferences(user_id="123", zen_active=True, zen_max_nudges=10)
        adapter, prefs_repo, _, zen_mgr = _make_adapter(prefs=prefs)
        zen_mgr.activate("123", zen_max_nudges=10, zen_interval_minutes=15)

        update, context = _make_update_and_context(args=[])
        await adapter.zen_handler(update, context)

        # Should not save again
        prefs_repo.save.assert_not_called()
        text = update.message.reply_text.call_args[0][0]
        assert "ya está activo" in text

    @pytest.mark.asyncio
    async def test_zen_records_activation_event(self):
        cycle = MagicMock()
        cycle.cycle_id = "cycle-1"
        adapter, _, cycle_repo, _ = _make_adapter(cycle=cycle)

        update, context = _make_update_and_context(args=[])
        await adapter.zen_handler(update, context)

        cycle_repo.record_nudge_event.assert_called_once()
        call_args = cycle_repo.record_nudge_event.call_args
        assert call_args.kwargs["event_type"] == "ZEN_ACTIVATED" or call_args[1].get("event_type") == "ZEN_ACTIVATED" or call_args[0][1] == "ZEN_ACTIVATED"


class TestZenDeactivate:
    @pytest.mark.asyncio
    async def test_zen_off_deactivates(self):
        prefs = UserNudgePreferences(user_id="123", zen_active=True)
        adapter, prefs_repo, _, zen_mgr = _make_adapter(prefs=prefs)
        zen_mgr.activate("123", zen_max_nudges=10, zen_interval_minutes=15)
        zen_mgr.record_nudge("123")  # 1 nudge sent

        update, context = _make_update_and_context(args=["off"])
        await adapter.zen_handler(update, context)

        # Prefs saved with zen_active=False
        saved = prefs_repo.save.call_args[0][0]
        assert saved.zen_active is False

        # Session removed
        assert zen_mgr.get("123") is None

        # Response includes count
        text = update.message.reply_text.call_args[0][0]
        assert "desactivado" in text
        assert "1" in text

    @pytest.mark.asyncio
    async def test_zen_off_when_not_active(self):
        prefs = UserNudgePreferences(user_id="123", zen_active=False)
        adapter, prefs_repo, _, _ = _make_adapter(prefs=prefs)

        update, context = _make_update_and_context(args=["off"])
        await adapter.zen_handler(update, context)

        prefs_repo.save.assert_not_called()
        text = update.message.reply_text.call_args[0][0]
        assert "no está activo" in text

    @pytest.mark.asyncio
    async def test_zen_response_in_spanish(self):
        adapter, _, _, _ = _make_adapter()
        update, context = _make_update_and_context(args=[])
        await adapter.zen_handler(update, context)

        text = update.message.reply_text.call_args[0][0]
        # All responses should be in Spanish
        assert any(w in text for w in ["Modo", "nudges", "activado", "desactivar"])

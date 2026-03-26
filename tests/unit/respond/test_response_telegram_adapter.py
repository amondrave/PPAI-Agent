"""Unit tests for ResponseTelegramAdapter (Step 11 — US-07)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ppai.capture.domain.value_objects import TaskStatus
from ppai.respond.domain.entities import TransitionResult
from ppai.respond.domain.value_objects import ResponseAction
from ppai.respond.infrastructure.response_telegram_adapter import ResponseTelegramAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_adapter(response_service=None, user_registry=None):
    svc = response_service or MagicMock()
    return ResponseTelegramAdapter(response_service=svc, user_registry=user_registry)


def _make_update(action: str, task_id: str, user_id: str = "123"):
    """Create a mock Telegram Update with a callback query."""
    update = MagicMock()
    update.callback_query = MagicMock()
    update.callback_query.from_user = MagicMock()
    update.callback_query.from_user.id = int(user_id)
    update.callback_query.data = f"{action}:{task_id}"
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    update.callback_query.message = MagicMock()
    update.callback_query.message.reply_text = AsyncMock()
    return update


def _make_text_update(text: str, user_id: str = "123"):
    """Create a mock Telegram Update with a text message."""
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = int(user_id)
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.callback_query = None
    return update


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDoneCallback:
    @pytest.mark.asyncio
    async def test_done_shows_confirmation_buttons(self):
        svc = MagicMock()
        svc.handle_done.return_value = TransitionResult(
            success=True,
            task_id="t1",
            action=ResponseAction.DONE,
            message="¿Confirmas que completaste esta tarea?",
            requires_confirmation=True,
            previous_status=TaskStatus.NUDGED,
        )
        adapter = _make_adapter(svc)
        update = _make_update("done", "t1")

        await adapter.callback_handler(update, None)

        update.callback_query.answer.assert_awaited_once()
        update.callback_query.edit_message_reply_markup.assert_awaited_once()
        # Verify confirmation keyboard was set (not None)
        call_args = update.callback_query.edit_message_reply_markup.call_args
        assert call_args.kwargs["reply_markup"] is not None
        update.callback_query.message.reply_text.assert_awaited_once()


class TestConfirmDoneCallback:
    @pytest.mark.asyncio
    async def test_confirm_done_ack_and_transition(self):
        svc = MagicMock()
        svc.confirm_done.return_value = TransitionResult(
            success=True,
            task_id="t1",
            action=ResponseAction.DONE,
            message="Tarea completada.",
            previous_status=TaskStatus.NUDGED,
            new_status=TaskStatus.DONE,
        )
        adapter = _make_adapter(svc)
        update = _make_update("confirm_done", "t1")

        await adapter.callback_handler(update, None)

        svc.confirm_done.assert_called_once_with("123", "t1")
        update.callback_query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)


class TestCancelDoneCallback:
    @pytest.mark.asyncio
    async def test_cancel_done_restores_message(self):
        adapter = _make_adapter()
        update = _make_update("cancel_done", "t1")

        await adapter.callback_handler(update, None)

        update.callback_query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)
        update.callback_query.message.reply_text.assert_awaited_once_with("OK, la tarea sigue activa.")


class TestSnoozeCallback:
    @pytest.mark.asyncio
    async def test_snooze_ack_with_count(self):
        svc = MagicMock()
        svc.handle_snooze.return_value = TransitionResult(
            success=True,
            task_id="t1",
            action=ResponseAction.SNOOZE,
            message="Tarea pospuesta (1/3). Volverá en 1 hora.",
            previous_status=TaskStatus.NUDGED,
            new_status=TaskStatus.SNOOZED,
        )
        adapter = _make_adapter(svc)
        update = _make_update("snooze", "t1")

        await adapter.callback_handler(update, None)

        svc.handle_snooze.assert_called_once_with("123", "t1")

    @pytest.mark.asyncio
    async def test_snooze_limit_auto_clarify_message(self):
        svc = MagicMock()
        svc.handle_snooze.return_value = TransitionResult(
            success=True,
            task_id="t1",
            action=ResponseAction.SNOOZE,
            message="Ya pospusiste esta tarea 3 veces. Necesitas aclararla o completarla.",
            previous_status=TaskStatus.NUDGED,
            new_status=TaskStatus.NEEDS_CLARIFICATION,
        )
        adapter = _make_adapter(svc)
        update = _make_update("snooze", "t1")

        await adapter.callback_handler(update, None)

        reply = update.callback_query.message.reply_text
        reply.assert_awaited_once()
        assert "3 veces" in reply.call_args[0][0]


class TestClarifyCallback:
    @pytest.mark.asyncio
    async def test_clarify_sends_question(self):
        svc = MagicMock()
        svc.handle_clarify.return_value = TransitionResult(
            success=True,
            task_id="t1",
            action=ResponseAction.CLARIFY,
            message="¿Qué necesitas para avanzar con esta tarea?",
            previous_status=TaskStatus.NUDGED,
            new_status=TaskStatus.NEEDS_CLARIFICATION,
        )
        adapter = _make_adapter(svc)
        update = _make_update("clarify", "t1")

        await adapter.callback_handler(update, None)

        reply = update.callback_query.message.reply_text
        assert "avanzar" in reply.call_args[0][0]


class TestClarifyTextResponse:
    @pytest.mark.asyncio
    async def test_text_resolves_clarification(self):
        svc = MagicMock()
        svc.handle_clarify_response.return_value = TransitionResult(
            success=True,
            task_id="t1",
            action=ResponseAction.CLARIFY,
            message="Aclaración recibida. La tarea vuelve a estar disponible.",
            previous_status=TaskStatus.NEEDS_CLARIFICATION,
            new_status=TaskStatus.PENDING,
        )
        adapter = _make_adapter(svc)
        update = _make_text_update("Necesito cotizar primero")

        await adapter.clarify_response_handler(update, None)

        svc.handle_clarify_response.assert_called_once_with("123", "Necesito cotizar primero")
        update.message.reply_text.assert_awaited_once()


class TestAuthorizationFailure:
    @pytest.mark.asyncio
    async def test_unauthorized_generic_message(self):
        svc = MagicMock()
        svc.handle_done.return_value = TransitionResult(
            success=False,
            task_id="t1",
            action=ResponseAction.DONE,
            message="No tienes permiso para esta acción.",
        )
        adapter = _make_adapter(svc)
        update = _make_update("done", "t1", user_id="999")

        await adapter.callback_handler(update, None)

        reply = update.callback_query.message.reply_text
        assert "No tienes permiso" in reply.call_args[0][0]


class TestIdempotentCallback:
    @pytest.mark.asyncio
    async def test_already_done_informative_message(self):
        svc = MagicMock()
        svc.handle_done.return_value = TransitionResult(
            success=True,
            task_id="t1",
            action=ResponseAction.DONE,
            message="Esta tarea ya fue completada.",
            previous_status=TaskStatus.DONE,
            new_status=TaskStatus.DONE,
        )
        adapter = _make_adapter(svc)
        update = _make_update("done", "t1")

        await adapter.callback_handler(update, None)

        reply = update.callback_query.message.reply_text
        assert "ya fue completada" in reply.call_args[0][0]

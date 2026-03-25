"""Unit tests for TelegramPushAdapter and CallbackAuthorizationGuard."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ppai.push.domain.entities import NudgeMessage
from ppai.push.infrastructure.telegram_push_adapter import (
    CallbackAuthorizationGuard,
    TelegramPushAdapter,
)


def make_message(task_id: str = "t1") -> NudgeMessage:
    return NudgeMessage(
        task_id=task_id,
        task_title="Enviar propuesta al cliente",
        priority_reason="Vence hoy y es la tarea más urgente.",
    )


# ---------------------------------------------------------------------------
# TelegramPushAdapter._build_payload
# ---------------------------------------------------------------------------

class TestBuildPayload:
    def setup_method(self):
        self.adapter = TelegramPushAdapter(bot_token="fake-token")

    def test_payload_contains_task_title(self):
        msg = make_message()
        payload = self.adapter._build_payload("chat-1", msg)
        assert "Enviar propuesta al cliente" in payload["text"]

    def test_payload_contains_priority_reason(self):
        msg = make_message()
        payload = self.adapter._build_payload("chat-1", msg)
        assert "Vence hoy y es la tarea más urgente." in payload["text"]

    def test_payload_has_three_inline_buttons(self):
        msg = make_message()
        payload = self.adapter._build_payload("chat-1", msg)
        buttons = payload["reply_markup"]["inline_keyboard"][0]
        assert len(buttons) == 3

    def test_button_labels_are_correct(self):
        msg = make_message()
        payload = self.adapter._build_payload("chat-1", msg)
        buttons = payload["reply_markup"]["inline_keyboard"][0]
        labels = [b["text"] for b in buttons]
        assert "✓ Hecho" in labels
        assert "⏸ Posponer" in labels
        assert "? Aclarar" in labels

    def test_callback_data_done(self):
        msg = make_message(task_id="task-99")
        payload = self.adapter._build_payload("chat-1", msg)
        buttons = payload["reply_markup"]["inline_keyboard"][0]
        cb_data = {b["text"]: b["callback_data"] for b in buttons}
        assert cb_data["✓ Hecho"] == "done:task-99"

    def test_callback_data_snooze(self):
        msg = make_message(task_id="task-99")
        payload = self.adapter._build_payload("chat-1", msg)
        buttons = payload["reply_markup"]["inline_keyboard"][0]
        cb_data = {b["text"]: b["callback_data"] for b in buttons}
        assert cb_data["⏸ Posponer"] == "snooze:task-99"

    def test_callback_data_clarify(self):
        msg = make_message(task_id="task-99")
        payload = self.adapter._build_payload("chat-1", msg)
        buttons = payload["reply_markup"]["inline_keyboard"][0]
        cb_data = {b["text"]: b["callback_data"] for b in buttons}
        assert cb_data["? Aclarar"] == "clarify:task-99"

    def test_chat_id_is_set_in_payload(self):
        msg = make_message()
        payload = self.adapter._build_payload("chat-42", msg)
        assert payload["chat_id"] == "chat-42"


# ---------------------------------------------------------------------------
# TelegramPushAdapter.send_nudge
# ---------------------------------------------------------------------------

class TestSendNudge:
    def setup_method(self):
        self.adapter = TelegramPushAdapter(bot_token="fake-token")

    def test_returns_true_on_http_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("ppai.push.infrastructure.telegram_push_adapter.requests.post", return_value=mock_resp):
            result = self.adapter.send_nudge("chat-1", make_message())
        assert result is True

    def test_returns_false_on_non_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        with patch("ppai.push.infrastructure.telegram_push_adapter.requests.post", return_value=mock_resp):
            result = self.adapter.send_nudge("chat-1", make_message())
        assert result is False

    def test_returns_false_on_request_exception(self):
        import requests as req_lib
        with patch(
            "ppai.push.infrastructure.telegram_push_adapter.requests.post",
            side_effect=req_lib.RequestException("timeout"),
        ):
            result = self.adapter.send_nudge("chat-1", make_message())
        assert result is False


# ---------------------------------------------------------------------------
# CallbackAuthorizationGuard
# ---------------------------------------------------------------------------

class TestCallbackAuthorizationGuard:
    def setup_method(self):
        self.guard = CallbackAuthorizationGuard()

    def test_accepts_callback_from_owner(self):
        assert self.guard.is_authorized(12345, "12345") is True

    def test_rejects_callback_from_different_user(self):
        assert self.guard.is_authorized(99999, "12345") is False

    def test_rejects_when_ids_differ_by_string_format(self):
        assert self.guard.is_authorized(12345, "012345") is False

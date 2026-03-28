from __future__ import annotations

import logging
from typing import Optional

import requests

from ppai.push.domain.entities import NudgeMessage

logger = logging.getLogger(__name__)

_BUTTON_LABELS = {
    "done": "✓ Hecho",
    "snooze": "⏸ Posponer",
    "clarify": "? Aclarar",
}


class TelegramPushAdapter:
    """
    Sends nudge messages with inline keyboard buttons via the Telegram Bot API.
    Uses the synchronous requests library so it integrates cleanly with the
    in-process threading scheduler (DP-PUSH-01) without requiring an async context.
    """

    _BASE_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str) -> None:
        self._bot_token = bot_token
        self._url = self._BASE_URL.format(token=bot_token)

    def send_nudge(self, chat_id: str, message: NudgeMessage) -> bool:
        """
        Send a nudge with inline keyboard to chat_id.
        Returns True on HTTP 200, False on any error.
        """
        payload = self._build_payload(chat_id, message)
        try:
            resp = requests.post(self._url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True
            logger.warning(
                "Telegram push failed",
                extra={
                    "chat_id": chat_id,
                    "task_id": message.task_id,
                    "status_code": resp.status_code,
                },
            )
            return False
        except requests.RequestException as exc:
            logger.warning(
                "Telegram push request error",
                extra={"chat_id": chat_id, "task_id": message.task_id, "error": str(exc)},
            )
            return False

    def send_message(self, chat_id: str, text: str) -> bool:
        """Send a plain text message (no buttons). Used for daily reminders."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            resp = requests.post(self._url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True
            logger.warning(
                "Telegram send_message failed",
                extra={"chat_id": chat_id, "status_code": resp.status_code},
            )
            return False
        except requests.RequestException as exc:
            logger.warning(
                "Telegram send_message error",
                extra={"chat_id": chat_id, "error": str(exc)},
            )
            return False

    def send_message_with_buttons(
        self,
        chat_id: str,
        text: str,
        buttons: list[list[dict[str, str]]],
    ) -> bool:
        """Send a message with inline keyboard buttons.

        Args:
            chat_id: Telegram chat ID.
            text: Message text (Markdown).
            buttons: List of rows, each row is a list of dicts with 'text' and 'callback_data'.
        """
        inline_keyboard = [
            [{"text": btn["text"], "callback_data": btn["callback_data"]} for btn in row]
            for row in buttons
        ]
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": inline_keyboard},
        }
        try:
            resp = requests.post(self._url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True
            logger.warning(
                "Telegram send_message_with_buttons failed",
                extra={"chat_id": chat_id, "status_code": resp.status_code},
            )
            return False
        except requests.RequestException as exc:
            logger.warning(
                "Telegram send_message_with_buttons error",
                extra={"chat_id": chat_id, "error": str(exc)},
            )
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(self, chat_id: str, message: NudgeMessage) -> dict:
        text = f"*{message.task_title}*\n\n{message.priority_reason}"
        inline_keyboard = [
            [
                {
                    "text": _BUTTON_LABELS.get(btn, btn),
                    "callback_data": f"{btn}:{message.task_id}",
                }
                for btn in message.buttons
            ]
        ]
        return {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": inline_keyboard},
        }


class CallbackAuthorizationGuard:
    """
    Validates that a Telegram callback query originates from the expected user.
    Implements DP-PUSH-07: dual-layer authorization for inline button callbacks.
    """

    def is_authorized(self, callback_from_user_id: int, expected_user_id: str) -> bool:
        """Return True only if the callback sender matches the expected user."""
        return str(callback_from_user_id) == expected_user_id

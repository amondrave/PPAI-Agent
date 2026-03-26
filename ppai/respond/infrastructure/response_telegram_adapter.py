"""Telegram adapter for UOW-04 Respond & State Transition."""
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ppai.respond.application.response_service import ResponseService
from ppai.respond.domain.entities import TransitionResult
from ppai.shared.infrastructure.user_registry import UserRegistry

logger = logging.getLogger(__name__)


class ResponseTelegramAdapter:
    """Handles done/snooze/clarify callbacks and clarify free-text responses."""

    def __init__(
        self,
        response_service: ResponseService,
        user_registry: UserRegistry | None = None,
    ) -> None:
        self._service = response_service
        self._user_registry = user_registry

    # ------------------------------------------------------------------
    # Callback handler — done, confirm_done, cancel_done, snooze, clarify
    # ------------------------------------------------------------------

    async def callback_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if query is None or query.from_user is None:
            return

        await query.answer()

        user_id = str(query.from_user.id)
        data = query.data or ""

        if self._user_registry:
            self._user_registry.register(user_id)

        try:
            action, task_id = data.split(":", 1)
        except ValueError:
            logger.warning("respond.callback.invalid_data", extra={"data": data})
            return

        try:
            if action == "done":
                result = self._service.handle_done(user_id, task_id)
                if result.requires_confirmation:
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("Sí", callback_data=f"confirm_done:{task_id}"),
                        InlineKeyboardButton("No", callback_data=f"cancel_done:{task_id}"),
                    ]])
                    await query.edit_message_reply_markup(reply_markup=keyboard)
                    await query.message.reply_text(result.message)
                else:
                    await query.edit_message_reply_markup(reply_markup=None)
                    await query.message.reply_text(result.message)

            elif action == "confirm_done":
                result = self._service.confirm_done(user_id, task_id)
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(self._format_result(result))

            elif action == "cancel_done":
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text("OK, la tarea sigue activa.")

            elif action == "snooze":
                result = self._service.handle_snooze(user_id, task_id)
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(self._format_result(result))

            elif action == "clarify":
                result = self._service.handle_clarify(user_id, task_id)
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(result.message)

            else:
                logger.warning("respond.callback.unknown_action", extra={"action": action})

        except ValueError as exc:
            logger.warning("respond.callback.task_not_found", extra={"error": str(exc)})
            await query.message.reply_text("No encontré esa tarea.")
        except Exception:
            logger.exception("respond.callback.error", extra={"user_id": user_id})
            await query.message.reply_text("Ocurrió un error. Intenta de nuevo.")

    # ------------------------------------------------------------------
    # Free-text handler for clarify responses
    # ------------------------------------------------------------------

    async def clarify_response_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """MessageHandler for free text when user has a task in NEEDS_CLARIFICATION."""
        if not update.effective_user or not update.message or not update.message.text:
            return

        user_id = str(update.effective_user.id)
        text = update.message.text.strip()

        if not text:
            return

        try:
            result = self._service.handle_clarify_response(user_id, text)
        except Exception:
            logger.exception("respond.clarify_response.error", extra={"user_id": user_id})
            return

        if result is None:
            # No task in NEEDS_CLARIFICATION — let other handlers process the message
            return

        await update.message.reply_text(result.message)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_result(result: TransitionResult) -> str:
        if not result.success:
            return result.message
        return result.message

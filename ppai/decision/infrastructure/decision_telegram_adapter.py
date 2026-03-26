from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ppai.capture.domain.entities import TaskState
from ppai.decision.application.decision_service import DecisionService
from ppai.decision.domain.entities import Top3Result
from ppai.decision.domain.exceptions import TaskNotInTop3Error
from ppai.shared.infrastructure.user_registry import UserRegistry

logger = logging.getLogger(__name__)

_MSG_EMPTY = "Tu bandeja está vacía. Envíame lo que tienes en mente para empezar."
_MSG_PARTIAL = "¿Tienes más pendientes? Captúralos y los agrego al mix."
_MSG_DONE_ACK = "Anotado. ✓"
_MSG_SNOOZE_ACK = "Pospuesto. Te lo recuerdo más tarde."


class DecisionTelegramAdapter:
    def __init__(
        self,
        decision_service: DecisionService,
        user_registry: UserRegistry | None = None,
    ) -> None:
        self._service = decision_service
        self._user_registry = user_registry

    # ------------------------------------------------------------------
    # /top3 command handler — BR-DEC-06, BR-DEC-07
    # ------------------------------------------------------------------

    async def top3_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.effective_user or not update.message:
            return

        user_id = str(update.effective_user.id)

        if self._user_registry:
            self._user_registry.register(user_id)

        try:
            result = self._service.get_top3(user_id)
        except Exception:
            logger.exception("top3.handler_error", extra={"user_id": user_id})
            await update.message.reply_text(
                "No pude obtener tus tareas. Intenta de nuevo."
            )
            return

        await self._send_top3(update, result)

    # ------------------------------------------------------------------
    # Callback handler — inline keyboard buttons (done / snooze / clarify)
    # ------------------------------------------------------------------

    async def callback_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        if query is None or query.from_user is None:
            return

        await query.answer()  # ACK the button press immediately

        user_id = str(query.from_user.id)
        data = query.data or ""

        try:
            action, task_id = data.split(":", 1)
        except ValueError:
            logger.warning("callback.invalid_data", extra={"data": data})
            return

        try:
            if action == "done":
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(_MSG_DONE_ACK)
                self._service.invalidate_cache(user_id)

            elif action == "snooze":
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(_MSG_SNOOZE_ACK)
                self._service.invalidate_cache(user_id)

            elif action == "clarify":
                question = self._service.clarify(task_id, user_id)
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(question)

            else:
                logger.warning("callback.unknown_action", extra={"action": action})

        except TaskNotInTop3Error:
            await query.message.reply_text(
                "Esa tarea ya no está en tu Top 3. Escribe /top3 para actualizar."
            )
        except Exception:
            logger.exception("callback.handler_error", extra={"user_id": user_id})
            await query.message.reply_text(
                "Ocurrió un error. Intenta de nuevo."
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _send_top3(self, update: Update, result: Top3Result) -> None:
        # BR-DEC-07: empty inbox
        if result.is_empty():
            await update.message.reply_text(_MSG_EMPTY)
            return

        task_ids = result.task_ids()

        # Fetch task details — service already has them but we need normalizedText
        # We get them from the score + task via service's internal task_repo
        for position, score in enumerate(result.ranked_scores, start=1):
            task = self._service._task_repo.get_by_id(
                result.user_id, score.task_id
            )
            if task is None:
                continue

            text = f"{position}. {task.normalized_text}"
            keyboard = _build_keyboard(task)
            await update.message.reply_text(text, reply_markup=keyboard)

        # BR-DEC-07: partial inbox motivational message
        if len(task_ids) < 3:
            await update.message.reply_text(_MSG_PARTIAL)


def _build_keyboard(task: TaskState) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✓ Hecho",    callback_data=f"done:{task.task_id}"),
        InlineKeyboardButton("⏸ Posponer", callback_data=f"snooze:{task.task_id}"),
        InlineKeyboardButton("? Aclarar",  callback_data=f"clarify:{task.task_id}"),
    ]])

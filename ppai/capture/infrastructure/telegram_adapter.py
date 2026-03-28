from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from ppai.capture.application.capture_service import CaptureService
from ppai.capture.domain.exceptions import InvalidInputError
from ppai.shared.infrastructure.rate_limiter import InMemoryRateLimiter
from ppai.shared.infrastructure.user_registry import UserRegistry

logger = logging.getLogger(__name__)


class TelegramAdapter:
    def __init__(
        self,
        capture_service: CaptureService,
        rate_limiter: InMemoryRateLimiter,
        user_registry: UserRegistry | None = None,
        schedule_adapter: object | None = None,
    ) -> None:
        self._capture_service = capture_service
        self._rate_limiter = rate_limiter
        self._user_registry = user_registry
        # ER5: Optional schedule adapter for post-capture calendar integration
        self._schedule_adapter = schedule_adapter

    async def message_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.effective_user or not update.message:
            return

        user_id = str(update.effective_user.id)

        if self._user_registry:
            self._user_registry.register(user_id)

        if not self._rate_limiter.check(user_id):
            await update.message.reply_text(
                "Demasiados mensajes. Espera un momento antes de enviar mas."
            )
            return

        text = update.message.text

        try:
            result = self._capture_service.process_message(user_id, text)
            confirmation = self._capture_service.build_confirmation(result)
            await update.message.reply_text(confirmation)

            # ER5: Trigger calendar scheduling for tasks with explicit time info
            if self._schedule_adapter and result.created:
                for task in result.created:
                    if task.has_explicit_time:
                        try:
                            await self._schedule_adapter.handle_post_capture(
                                update=update,
                                user_id=user_id,
                                task_id=task.task_id,
                                task_title=task.normalized_text,
                                estimated_minutes=task.estimated_minutes,
                                slot_start=task.requested_slot_start,
                                slot_end=task.requested_slot_end,
                            )
                        except Exception:
                            logger.exception(
                                "ER5: Schedule post-capture failed",
                                extra={"task_id": task.task_id},
                            )
        except InvalidInputError as e:
            await update.message.reply_text(str(e))
        except Exception:
            logger.exception("Unhandled error in message_handler", extra={"user_id": user_id})
            await update.message.reply_text(
                "Ocurrio un error procesando tu mensaje. Intenta de nuevo."
            )

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        logger.exception(
            "Unhandled exception in telegram bot",
            exc_info=context.error,
        )

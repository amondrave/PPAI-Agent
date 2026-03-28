"""Telegram ConversationHandler for onboarding flow."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ppai.profile.application.onboarding_service import OnboardingService
from ppai.profile.application.profile_service import ProfileService
from ppai.profile.domain.value_objects import OnboardingStep

logger = structlog.get_logger(__name__)

# ConversationHandler states (int constants mapped to OnboardingStep)
STATE_NAME = 0
STATE_OCCUPATION = 1
STATE_WORK_START = 2
STATE_WORK_END = 3
STATE_PROTECTED_BLOCKS = 4
STATE_COMMUNICATION_STYLE = 5
STATE_CONFIRM = 6

_STEP_TO_STATE = {
    OnboardingStep.NAME: STATE_NAME,
    OnboardingStep.OCCUPATION: STATE_OCCUPATION,
    OnboardingStep.WORK_START: STATE_WORK_START,
    OnboardingStep.WORK_END: STATE_WORK_END,
    OnboardingStep.PROTECTED_BLOCKS: STATE_PROTECTED_BLOCKS,
    OnboardingStep.COMMUNICATION_STYLE: STATE_COMMUNICATION_STYLE,
    OnboardingStep.CONFIRM: STATE_CONFIRM,
}


class OnboardingTelegramAdapter:
    """Manages the onboarding ConversationHandler for Telegram."""

    def __init__(
        self,
        onboarding_service: OnboardingService,
        profile_service: ProfileService,
    ) -> None:
        self._onboarding = onboarding_service
        self._profile_service = profile_service

    def build_conversation_handler(self) -> ConversationHandler:
        """Build and return the ConversationHandler for onboarding."""
        return ConversationHandler(
            entry_points=[
                CommandHandler("setup", self._setup_command),
                CommandHandler("start", self._start_command),
            ],
            states={
                STATE_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_name),
                ],
                STATE_OCCUPATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_occupation),
                ],
                STATE_WORK_START: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_work_start),
                ],
                STATE_WORK_END: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_work_end),
                ],
                STATE_PROTECTED_BLOCKS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_protected_blocks),
                ],
                STATE_COMMUNICATION_STYLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_communication_style),
                ],
                STATE_CONFIRM: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_confirm),
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self._cancel),
                CommandHandler("setup", self._setup_command),
            ],
        )

    async def _start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle /start — begin onboarding if no profile exists."""
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = str(update.effective_user.id)

        if self._profile_service.profile_exists(user_id):
            await update.message.reply_text(
                "Ya tienes un perfil configurado. "
                "Usa /setup si quieres reconfigurarlo."
            )
            return ConversationHandler.END

        question = self._onboarding.start(user_id)
        await update.message.reply_text(question)
        return STATE_NAME

    async def _setup_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle /setup — start or restart onboarding."""
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = str(update.effective_user.id)

        if self._profile_service.profile_exists(user_id):
            await update.message.reply_text(
                "Ya tienes un perfil. Este proceso lo sobreescribira.\n"
                "Comenzamos de nuevo:"
            )

        question = self._onboarding.start(user_id)
        await update.message.reply_text(question)
        return STATE_NAME

    async def _auto_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Auto-start onboarding on first text message if no profile exists."""
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = str(update.effective_user.id)

        if self._profile_service.profile_exists(user_id):
            # User has a profile — don't intercept, let other handlers process
            return ConversationHandler.END

        question = self._onboarding.start(user_id)
        await update.message.reply_text(question)
        return STATE_NAME

    async def _handle_name(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        return await self._process_step(update, OnboardingStep.NAME)

    async def _handle_occupation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        return await self._process_step(update, OnboardingStep.OCCUPATION)

    async def _handle_work_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        return await self._process_step(update, OnboardingStep.WORK_START)

    async def _handle_work_end(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        return await self._process_step(update, OnboardingStep.WORK_END)

    async def _handle_protected_blocks(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        return await self._process_step(update, OnboardingStep.PROTECTED_BLOCKS)

    async def _handle_communication_style(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        return await self._process_step(update, OnboardingStep.COMMUNICATION_STYLE)

    async def _handle_confirm(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle confirmation step — save profile or restart."""
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = str(update.effective_user.id)
        text = update.message.text or ""

        next_step, response = self._onboarding.process_step(
            user_id, text, OnboardingStep.CONFIRM
        )

        await update.message.reply_text(response)

        if next_step is None:
            # User confirmed — save profile
            profile = self._onboarding.complete(user_id)
            if profile:
                self._profile_service.save_profile(profile)
            return ConversationHandler.END

        # User said No — restarted, back to NAME
        return _STEP_TO_STATE.get(next_step, STATE_NAME)

    async def _cancel(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        """Handle /cancel — abort onboarding."""
        if update.message:
            await update.message.reply_text(
                "Onboarding cancelado. Puedes retomarlo con /setup."
            )
        return ConversationHandler.END

    async def _process_step(self, update: Update, step: OnboardingStep) -> int:
        """Generic step processor."""
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = str(update.effective_user.id)
        text = update.message.text or ""

        next_step, response = self._onboarding.process_step(user_id, text, step)

        await update.message.reply_text(response)

        if next_step is None:
            # Onboarding complete (should not happen here, only at CONFIRM)
            profile = self._onboarding.complete(user_id)
            if profile:
                self._profile_service.save_profile(profile)
            return ConversationHandler.END

        return _STEP_TO_STATE.get(next_step, STATE_NAME)

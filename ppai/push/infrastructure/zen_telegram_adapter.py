"""Telegram handler for /zen — zen mode activation/deactivation."""

from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from ppai.push.application.ports import CycleEventRepository, PreferencesRepository
from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.domain.entities import UserNudgePreferences


class ZenTelegramAdapter:
    """Handles /zen command for activating/deactivating zen mode."""

    def __init__(
        self,
        prefs_repo: PreferencesRepository,
        cycle_event_repo: CycleEventRepository,
        zen_manager: ZenSessionManager,
    ) -> None:
        self._prefs_repo = prefs_repo
        self._cycle_event_repo = cycle_event_repo
        self._zen_manager = zen_manager

    async def zen_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.effective_user or not update.message:
            return

        user_id = str(update.effective_user.id)
        args = context.args or []

        if args and args[0].lower() == "off":
            await self._deactivate(update, user_id)
        else:
            await self._activate(update, user_id)

    async def _activate(self, update: Update, user_id: str) -> None:
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)

        if prefs.zen_active:
            session = self._zen_manager.get(user_id)
            remaining = (session.max_nudges - session.nudges_sent) if session else "?"
            await update.message.reply_text(
                f"El modo zen ya está activo. Te quedan {remaining} nudges."
            )
            return

        prefs.zen_active = True
        self._prefs_repo.save(prefs)

        session = self._zen_manager.activate(
            user_id=user_id,
            zen_max_nudges=prefs.zen_max_nudges,
            zen_interval_minutes=prefs.zen_interval_minutes,
        )

        # Record event
        cycle = self._cycle_event_repo.get_active(user_id, datetime.now(timezone.utc).date())
        if cycle:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle.cycle_id,
                event_type="ZEN_ACTIVATED",
                metadata={
                    "max_nudges": str(prefs.zen_max_nudges),
                    "interval_minutes": str(prefs.zen_interval_minutes),
                },
            )

        await update.message.reply_text(
            f"Modo zen activado.\n"
            f"Recibirás hasta {prefs.zen_max_nudges} nudges cada {prefs.zen_interval_minutes} minutos.\n"
            f"Usa /zen off para desactivar."
        )

    async def _deactivate(self, update: Update, user_id: str) -> None:
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)

        if not prefs.zen_active:
            await update.message.reply_text(
                "El modo zen no está activo."
            )
            return

        prefs.zen_active = False
        self._prefs_repo.save(prefs)

        session = self._zen_manager.deactivate(user_id)
        nudges_sent = session.nudges_sent if session else 0

        # Record event
        cycle = self._cycle_event_repo.get_active(user_id, datetime.now(timezone.utc).date())
        if cycle:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle.cycle_id,
                event_type="ZEN_DEACTIVATED",
                metadata={"nudges_sent": str(nudges_sent), "reason": "manual"},
            )

        await update.message.reply_text(
            f"Modo zen desactivado. Enviaste {nudges_sent} nudges en esta sesión."
        )

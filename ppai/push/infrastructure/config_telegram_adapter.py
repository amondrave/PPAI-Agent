"""Telegram handler for /config — nudge preferences management."""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import Update
from telegram.ext import ContextTypes

from ppai.push.application.ports import PreferencesRepository
from ppai.push.domain.entities import UserNudgePreferences

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

_HELP_TEXT = (
    "⚙️ *Configuración de recordatorios*\n\n"
    "Uso:\n"
    "`/config` — ver tu configuración actual\n"
    "`/config silencio HH:MM-HH:MM` — ventana de silencio\n"
    "`/config nudges N` — máximo de recordatorios por día (1-10)\n"
    "`/config timezone ZONA` — zona horaria (ej. America/Bogota)\n\n"
    "Ejemplo: `/config silencio 22:00-08:00`"
)


class ConfigTelegramAdapter:
    """Handles /config command for nudge preferences."""

    def __init__(self, prefs_repo: PreferencesRepository) -> None:
        self._prefs_repo = prefs_repo

    async def config_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.effective_user or not update.message:
            return

        user_id = str(update.effective_user.id)
        args = context.args or []

        if not args:
            await self._show_current(update, user_id)
            return

        subcommand = args[0].lower()

        if subcommand == "silencio" and len(args) == 2:
            await self._set_silence(update, user_id, args[1])
        elif subcommand == "nudges" and len(args) == 2:
            await self._set_max_nudges(update, user_id, args[1])
        elif subcommand == "timezone" and len(args) == 2:
            await self._set_timezone(update, user_id, args[1])
        else:
            await update.message.reply_text(_HELP_TEXT, parse_mode="Markdown")

    async def _show_current(self, update: Update, user_id: str) -> None:
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)

        silence = "No configurada"
        if prefs.has_silence_window():
            silence = f"{prefs.silence_start} - {prefs.silence_end}"

        text = (
            "⚙️ *Tu configuración actual*\n\n"
            f"🕐 Zona horaria: `{prefs.timezone}`\n"
            f"🔔 Máx recordatorios/día: `{prefs.max_nudges_per_day}`\n"
            f"🔇 Ventana de silencio: `{silence}`\n\n"
            "Usa `/config` con subcomandos para cambiar."
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def _set_silence(self, update: Update, user_id: str, value: str) -> None:
        parts = value.split("-")
        if len(parts) != 2 or not _TIME_RE.match(parts[0]) or not _TIME_RE.match(parts[1]):
            await update.message.reply_text(
                "Formato inválido. Usa: `/config silencio HH:MM-HH:MM`\n"
                "Ejemplo: `/config silencio 22:00-08:00`",
                parse_mode="Markdown",
            )
            return

        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        prefs.silence_start = parts[0]
        prefs.silence_end = parts[1]
        self._prefs_repo.save(prefs)

        await update.message.reply_text(
            f"Ventana de silencio configurada: {parts[0]} - {parts[1]}"
        )

    async def _set_max_nudges(self, update: Update, user_id: str, value: str) -> None:
        try:
            n = int(value)
        except ValueError:
            n = -1

        if n < 1 or n > 10:
            await update.message.reply_text(
                "El número de recordatorios debe estar entre 1 y 10."
            )
            return

        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        prefs.max_nudges_per_day = n
        self._prefs_repo.save(prefs)

        await update.message.reply_text(
            f"Máximo de recordatorios por día: {n}"
        )

    async def _set_timezone(self, update: Update, user_id: str, value: str) -> None:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, KeyError):
            await update.message.reply_text(
                "Zona horaria no válida. Ejemplos:\n"
                "`America/Bogota`, `America/Mexico_City`, `US/Eastern`",
                parse_mode="Markdown",
            )
            return

        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        prefs.timezone = value
        self._prefs_repo.save(prefs)

        await update.message.reply_text(
            f"Zona horaria configurada: {value}"
        )

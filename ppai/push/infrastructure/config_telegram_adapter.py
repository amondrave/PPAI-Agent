"""Telegram handler for /config — nudge preferences management."""

from __future__ import annotations

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import Update
from telegram.ext import ContextTypes

from ppai.push.application.ports import PreferencesRepository
from ppai.push.domain.entities import UserNudgePreferences

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_HTML_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_MAX_MOTIVATIONAL_LEN = 100

_HELP_TEXT = (
    "⚙️ *Configuración de recordatorios*\n\n"
    "Uso:\n"
    "`/config` — ver tu configuración actual\n"
    "`/config silencio HH:MM-HH:MM` — ventana de silencio\n"
    "`/config nudges N` — máximo de recordatorios por día (1-10)\n"
    "`/config timezone ZONA` — zona horaria (ej. America/Bogota)\n"
    "`/config inicio HH:MM` — hora del recordatorio matutino\n"
    "`/config cierre HH:MM` — hora del resumen de cierre\n"
    "`/config zen_intervalo N` — intervalo zen en minutos (5-60)\n"
    "`/config zen_max N` — máx nudges en modo zen (1-50)\n"
    "`/config motivacion TEXTO` — mensaje motivacional (máx 100 chars)\n\n"
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
        elif subcommand == "inicio" and len(args) == 2:
            await self._set_daily_start(update, user_id, args[1])
        elif subcommand == "cierre" and len(args) == 2:
            await self._set_daily_end(update, user_id, args[1])
        elif subcommand == "zen_intervalo" and len(args) == 2:
            await self._set_zen_interval(update, user_id, args[1])
        elif subcommand == "zen_max" and len(args) == 2:
            await self._set_zen_max(update, user_id, args[1])
        elif subcommand == "motivacion" and len(args) >= 2:
            text_value = " ".join(args[1:])
            await self._set_motivational(update, user_id, text_value)
        else:
            await update.message.reply_text(_HELP_TEXT, parse_mode="Markdown")

    async def _show_current(self, update: Update, user_id: str) -> None:
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)

        silence = "No configurada"
        if prefs.has_silence_window():
            silence = f"{prefs.silence_start} - {prefs.silence_end}"

        zen_status = "Activo" if prefs.zen_active else "Inactivo"

        text = (
            "⚙️ *Tu configuración actual*\n\n"
            f"🕐 Zona horaria: `{prefs.timezone}`\n"
            f"🔔 Máx recordatorios/día: `{prefs.max_nudges_per_day}`\n"
            f"🔇 Ventana de silencio: `{silence}`\n"
            f"🌅 Hora de inicio: `{prefs.daily_start_time}`\n"
            f"🌆 Hora de cierre: `{prefs.daily_end_time}`\n"
            f"🧘 Modo zen: `{zen_status}`\n"
            f"⏱ Intervalo zen: `{prefs.zen_interval_minutes} min`\n"
            f"📊 Máx nudges zen: `{prefs.zen_max_nudges}`\n"
            f"💪 Motivación: `{prefs.motivational_message}`\n\n"
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

    # --- UOW-05: new subcommands ---

    async def _set_daily_start(self, update: Update, user_id: str, value: str) -> None:
        if not _TIME_RE.match(value):
            await update.message.reply_text("Formato inválido. Usa: `/config inicio HH:MM`", parse_mode="Markdown")
            return
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        prefs.daily_start_time = value
        self._prefs_repo.save(prefs)
        await update.message.reply_text(f"Hora de inicio configurada: {value}")

    async def _set_daily_end(self, update: Update, user_id: str, value: str) -> None:
        if not _TIME_RE.match(value):
            await update.message.reply_text("Formato inválido. Usa: `/config cierre HH:MM`", parse_mode="Markdown")
            return
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        prefs.daily_end_time = value
        self._prefs_repo.save(prefs)
        await update.message.reply_text(f"Hora de cierre configurada: {value}")

    async def _set_zen_interval(self, update: Update, user_id: str, value: str) -> None:
        try:
            n = int(value)
        except ValueError:
            n = -1
        if n < 5 or n > 60:
            await update.message.reply_text("El intervalo zen debe estar entre 5 y 60 minutos.")
            return
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        prefs.zen_interval_minutes = n
        self._prefs_repo.save(prefs)
        await update.message.reply_text(f"Intervalo zen configurado: {n} minutos")

    async def _set_zen_max(self, update: Update, user_id: str, value: str) -> None:
        try:
            n = int(value)
        except ValueError:
            n = -1
        if n < 1 or n > 50:
            await update.message.reply_text("El máximo de nudges zen debe estar entre 1 y 50.")
            return
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        prefs.zen_max_nudges = n
        self._prefs_repo.save(prefs)
        await update.message.reply_text(f"Máx nudges zen configurado: {n}")

    async def _set_motivational(self, update: Update, user_id: str, value: str) -> None:
        # DP-SCHED-07: sanitize input
        if _URL_RE.search(value):
            await update.message.reply_text("El mensaje motivacional no puede contener URLs.")
            return
        sanitized = _HTML_RE.sub("", value).strip()
        if len(sanitized) > _MAX_MOTIVATIONAL_LEN:
            await update.message.reply_text(f"El mensaje no puede superar {_MAX_MOTIVATIONAL_LEN} caracteres.")
            return
        if not sanitized:
            await update.message.reply_text("El mensaje no puede estar vacío.")
            return
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        prefs.motivational_message = sanitized
        self._prefs_repo.save(prefs)
        await update.message.reply_text(f"Mensaje motivacional configurado: {sanitized}")

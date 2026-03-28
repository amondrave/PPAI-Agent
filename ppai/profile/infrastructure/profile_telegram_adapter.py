"""Telegram command handlers for profile management: /perfil, /config profile fields, /libre."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from ppai.profile.application.profile_service import ProfileService
from ppai.profile.domain.exceptions import InvalidProfileDataError
from ppai.profile.domain.value_objects import CommunicationStyle, WeekendMode

logger = structlog.get_logger(__name__)

_STYLE_LABELS = {
    CommunicationStyle.GENTLE: "Amable",
    CommunicationStyle.DIRECT: "Directo",
    CommunicationStyle.CONFRONTATIONAL: "Desafiante",
}

_WEEKEND_LABELS = {
    WeekendMode.DESCANSO: "Descanso",
    WeekendMode.PERSONAL: "Personal",
    WeekendMode.MIXTO: "Mixto",
}

_PROFILE_CONFIG_HELP = (
    "Configuracion de perfil:\n\n"
    "`/config nombre Angel`\n"
    "`/config estilo gentle|direct|confrontational`\n"
    "`/config horario 08:00-17:00`\n"
    "`/config pais CO`\n"
    "`/config finde descanso|personal|mixto`\n"
)


class ProfileTelegramAdapter:
    """Handles /perfil, /libre, and profile-related /config subcommands."""

    def __init__(self, profile_service: ProfileService) -> None:
        self._service = profile_service

    async def perfil_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /perfil — show formatted profile summary."""
        if not update.effective_user or not update.message:
            return

        user_id = str(update.effective_user.id)
        profile = self._service.get_profile(user_id)

        if profile is None:
            await update.message.reply_text(
                "No tienes un perfil configurado. Usa /setup para crearlo."
            )
            return

        work_start = profile.work_start.strftime("%H:%M") if profile.work_start else "N/A"
        work_end = profile.work_end.strftime("%H:%M") if profile.work_end else "N/A"

        blocks_str = "Ninguno"
        if profile.protected_blocks:
            blocks_lines = []
            for b in profile.protected_blocks:
                blocks_lines.append(f"  {b['start']}-{b['end']} {b['label']}")
            blocks_str = "\n".join(blocks_lines)

        style_label = _STYLE_LABELS.get(
            profile.communication_style, str(profile.communication_style)
        )
        weekend_label = _WEEKEND_LABELS.get(
            profile.weekend_mode, str(profile.weekend_mode)
        )

        country = profile.holidays_country or "No configurado"
        days_off_count = len(profile.days_off)

        text = (
            f"Tu perfil:\n\n"
            f"Nombre: {profile.name}\n"
            f"Ocupacion: {profile.occupation}\n"
            f"Horario: {work_start} - {work_end}\n"
            f"Zona horaria: {profile.timezone}\n"
            f"Bloques protegidos:\n{blocks_str}\n"
            f"Estilo: {style_label}\n"
            f"Pais festivos: {country}\n"
            f"Modo fin de semana: {weekend_label}\n"
            f"Dias libres: {days_off_count}\n\n"
            "Usa /config para modificar campos individuales."
        )
        await update.message.reply_text(text)

    async def config_profile_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> bool:
        """
        Handle profile-related /config subcommands.
        Returns True if the subcommand was handled, False otherwise.
        This allows the existing ConfigTelegramAdapter to handle non-profile subcommands.
        """
        if not update.effective_user or not update.message:
            return False

        user_id = str(update.effective_user.id)
        args = context.args or []

        if not args:
            return False

        subcommand = args[0].lower()
        profile_subcommands = {"nombre", "estilo", "horario", "pais", "finde"}

        if subcommand not in profile_subcommands:
            return False

        if len(args) < 2:
            await update.message.reply_text(
                f"Falta el valor. Ejemplo: `/config {subcommand} ...`",
                parse_mode="Markdown",
            )
            return True

        value = " ".join(args[1:])

        try:
            profile = self._service.update_field(user_id, subcommand, value)
            field_labels = {
                "nombre": f"Nombre actualizado: {profile.name}",
                "estilo": f"Estilo actualizado: {_STYLE_LABELS.get(profile.communication_style, str(profile.communication_style))}",
                "horario": f"Horario actualizado: {profile.work_start.strftime('%H:%M') if profile.work_start else 'N/A'} - {profile.work_end.strftime('%H:%M') if profile.work_end else 'N/A'}",
                "pais": f"Pais de festivos actualizado: {profile.holidays_country or 'Ninguno'}",
                "finde": f"Modo fin de semana actualizado: {_WEEKEND_LABELS.get(profile.weekend_mode, str(profile.weekend_mode))}",
            }
            msg = field_labels.get(subcommand, "Campo actualizado.")
            await update.message.reply_text(msg)
        except InvalidProfileDataError as exc:
            await update.message.reply_text(str(exc))

        return True

    async def libre_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /libre — add or list personal days off."""
        if not update.effective_user or not update.message:
            return

        user_id = str(update.effective_user.id)
        args = context.args or []

        if not args:
            await update.message.reply_text(
                "Uso:\n"
                "`/libre 2026-04-15` — agregar dia libre\n"
                "`/libre list` — ver tus dias libres",
                parse_mode="Markdown",
            )
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            text = self._service.list_days_off(user_id)
            await update.message.reply_text(text)
            return

        # Treat first arg as a date to add
        try:
            self._service.add_day_off(user_id, args[0])
            await update.message.reply_text(f"Dia libre agregado: {args[0]}")
        except InvalidProfileDataError as exc:
            await update.message.reply_text(str(exc))

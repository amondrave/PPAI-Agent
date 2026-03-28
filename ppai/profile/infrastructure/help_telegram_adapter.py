from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Static command registry — update when adding new commands
_COMMANDS: dict[str, dict] = {
    "plan": {
        "desc": "Genera tu plan del dia con bloques de tiempo",
        "usage": "`/plan` o `/plan manana`",
        "sub": None,
    },
    "top3": {
        "desc": "Muestra tus 3 tareas mas importantes",
        "usage": "`/top3`",
        "sub": None,
    },
    "calendar": {
        "desc": "Conecta tu Google Calendar",
        "usage": "`/calendar`",
        "sub": None,
    },
    "perfil": {
        "desc": "Consulta tu perfil configurado",
        "usage": "`/perfil`",
        "sub": None,
    },
    "setup": {
        "desc": "Inicia o repite el onboarding completo",
        "usage": "`/setup`",
        "sub": None,
    },
    "config": {
        "desc": "Ajusta configuracion de recordatorios y perfil",
        "usage": "`/config <opcion> <valor>`",
        "sub": {
            "silencio HH:MM-HH:MM": "Ventana sin notificaciones",
            "nudges N": "Cantidad de nudges por dia (1-5)",
            "estilo gentil|directo|confrontacional": "Estilo de comunicacion",
            "nombre <tu nombre>": "Cambia tu nombre",
            "horario HH:MM-HH:MM": "Horario laboral",
        },
    },
    "zen": {
        "desc": "Activa modo zen (sin nudges por un tiempo)",
        "usage": "`/zen` o `/zen 60`",
        "sub": None,
    },
    "libre": {
        "desc": "Gestiona dias libres personalizados",
        "usage": "`/libre YYYY-MM-DD` o `/libre list`",
        "sub": None,
    },
    "help": {
        "desc": "Muestra esta ayuda",
        "usage": "`/help` o `/help <comando>`",
        "sub": None,
    },
}

_CAPTURE_SECTION = (
    "*Como capturar tareas*\n"
    "Envia cualquier texto y PPAI lo registra como tarea.\n\n"
    "Ejemplos:\n"
    "  `Revisar PR del equipo #work`\n"
    "  `Practicar guitarra 30min #hobby`\n"
    "  `Llamar al dentista #15:00-15:30`\n"
    "  `Leer capitulo 3 para manana #learning`\n\n"
    "Puedes incluir:\n"
    "  `#categoria` — clasifica la tarea (work, personal, learning, health, social, errand)\n"
    "  `30min`, `1h`, `2 horas` — duracion estimada\n"
    "  `#HH:MM-HH:MM` — horario exacto para agendar\n"
    "  `para hoy`, `para manana`, `urgente` — deadline\n"
)


class HelpTelegramAdapter:
    """Handler for /help command."""

    async def help_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.effective_user or not update.message:
            return

        args = context.args or []

        if args:
            # /help <command> — detailed help for one command
            cmd = args[0].lower().lstrip("/")
            text = self._command_detail(cmd)
        else:
            # /help — full overview
            text = self._full_help()

        await update.message.reply_text(text, parse_mode="Markdown")

    def _full_help(self) -> str:
        parts: list[str] = [
            "*PPAI — Tu asistente de productividad*\n",
            _CAPTURE_SECTION,
            "*Comandos disponibles*\n",
        ]

        for cmd, info in _COMMANDS.items():
            parts.append(f"  /{cmd} — {info['desc']}")

        parts.append("\nUsa `/help <comando>` para ver detalles de un comando.")
        return "\n".join(parts)

    def _command_detail(self, cmd: str) -> str:
        info = _COMMANDS.get(cmd)
        if not info:
            available = ", ".join(f"/{c}" for c in _COMMANDS)
            return f"Comando `/{cmd}` no encontrado.\n\nComandos disponibles: {available}"

        parts = [
            f"*/{cmd}* — {info['desc']}\n",
            f"Uso: {info['usage']}",
        ]

        if info["sub"]:
            parts.append("\n*Opciones:*")
            for sub_cmd, sub_desc in info["sub"].items():
                parts.append(f"  `/config {sub_cmd}` — {sub_desc}")

        return "\n".join(parts)

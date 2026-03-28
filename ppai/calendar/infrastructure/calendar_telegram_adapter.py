from __future__ import annotations

import asyncio
import logging
import time as _time
from datetime import datetime, timedelta, timezone
from functools import partial

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ppai.calendar.application.block_planner import BlockPlanner
from ppai.calendar.application.calendar_service import CalendarService
from ppai.calendar.application.calendar_sync import CalendarSync
from ppai.calendar.application.category_classifier import CategoryClassifier
from ppai.calendar.application.google_oauth_service import GoogleOAuthService
from ppai.calendar.application.ports import TimeBlockRepository
from ppai.calendar.domain.value_objects import BlockStatus
from ppai.capture.application.ports import TaskStateRepository

logger = logging.getLogger(__name__)

# ConversationHandler states
ASK_CODE = 0

# Block status display
_STATUS_EMOJI = {
    BlockStatus.PLANNED: "\U0001f4cb",     # clipboard
    BlockStatus.IN_PROGRESS: "\u25b6\ufe0f",  # play
    BlockStatus.COMPLETED: "\u2705",       # check mark
    BlockStatus.SKIPPED: "\u23ed\ufe0f",   # skip
}

_CATEGORY_EMOJI = {
    "work": "\U0001f4bc",
    "personal": "\U0001f3e0",
    "learning": "\U0001f4da",
    "health": "\U0001f3c3",
    "social": "\U0001f91d",
    "errand": "\U0001f6d2",
}


class CalendarTelegramAdapter:
    """Telegram handlers for /calendar (OAuth) and /plan (day planning) commands."""

    def __init__(
        self,
        calendar_service: CalendarService,
        oauth_service: GoogleOAuthService,
        block_planner: BlockPlanner,
        block_repo: TimeBlockRepository,
        task_repo: TaskStateRepository,
        category_classifier: CategoryClassifier,
        calendar_sync: CalendarSync,
    ) -> None:
        self._calendar_service = calendar_service
        self._oauth_service = oauth_service
        self._block_planner = block_planner
        self._block_repo = block_repo
        self._task_repo = task_repo
        self._classifier = category_classifier
        self._calendar_sync = calendar_sync

    # ------------------------------------------------------------------
    # /calendar command — OAuth ConversationHandler
    # ------------------------------------------------------------------

    def build_calendar_conversation_handler(self) -> ConversationHandler:
        """Build the ConversationHandler for the /calendar OAuth flow."""
        return ConversationHandler(
            entry_points=[CommandHandler("calendar", self._calendar_start)],
            states={
                ASK_CODE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._calendar_code),
                ],
            },
            fallbacks=[CommandHandler("cancel", self._calendar_cancel)],
            per_user=True,
            per_chat=True,
        )

    async def _calendar_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the Desktop OAuth flow: show auth URL and wait for code."""
        if not update.effective_user or not update.message:
            return ConversationHandler.END

        user_id = str(update.effective_user.id)

        # Check if already connected
        if self._calendar_service.is_connected(user_id):
            await update.message.reply_text(
                "\u2705 Tu Google Calendar ya esta conectado.\n"
                "Para reconectar, usa /calendar de nuevo."
            )

        try:
            auth_url = self._oauth_service.generate_auth_url()

            # Save timestamp for manual expiry check (no JobQueue available)
            if context.user_data is not None:
                context.user_data["calendar_started_at"] = _time.time()

            await update.message.reply_text(
                "\U0001f4c5 <b>Conectar Google Calendar</b>\n\n"
                f'1. Abre este link en tu navegador:\n<a href="{auth_url}">Autorizar Google Calendar</a>\n\n'
                "2. Autoriza el acceso a tu calendario\n\n"
                "3. Google te redirigira a una pagina que no carga — "
                "eso es normal\n\n"
                "4. Copia el valor de <code>code=</code> de la barra de direccion "
                "y pegalo aqui\n\n"
                "Tienes <b>5 minutos</b> para completar el proceso.\n"
                "Escribe /cancel para cancelar.",
                parse_mode="HTML",
            )
            return ASK_CODE
        except Exception as exc:
            logger.error("Error starting OAuth flow", extra={"error": str(exc)})
            await update.message.reply_text(
                "\u274c Error al iniciar la autorizacion. Intenta de nuevo."
            )
            return ConversationHandler.END

    async def _calendar_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """User pasted the authorization code — exchange for tokens."""
        if not update.effective_user or not update.message or not update.message.text:
            return ConversationHandler.END

        user_id = str(update.effective_user.id)

        try:
            # Check manual expiry (5 minutes)
            started_at = (context.user_data or {}).get("calendar_started_at", 0)
            if _time.time() - started_at > 300:
                await update.message.reply_text(
                    "\u23f0 El tiempo para pegar el codigo expiro (5 min).\n"
                    "Envia /calendar para iniciar de nuevo."
                )
                return ConversationHandler.END

            raw_input = update.message.text.strip()

            # Extract auth code from various formats users might paste:
            # - Full URL: http://localhost/?code=XXXX&scope=...
            # - With prefix: code=XXXX
            # - Just the code: 4/0Aci98E-XXXX
            auth_code = raw_input
            if "code=" in auth_code:
                from urllib.parse import parse_qs, urlparse
                try:
                    parsed = urlparse(auth_code)
                    if parsed.query:
                        params = parse_qs(parsed.query)
                        auth_code = params.get("code", [auth_code])[0]
                    else:
                        auth_code = auth_code.split("code=", 1)[1].split("&")[0]
                except Exception:
                    auth_code = raw_input

            auth_code = auth_code.strip()

            if not auth_code:
                await update.message.reply_text(
                    "\u274c No recibi un codigo valido. Intenta de nuevo con /calendar."
                )
                return ConversationHandler.END

            await update.message.reply_text(
                "\u23f3 Codigo recibido. Verificando autorizacion con Google..."
            )

            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None, partial(self._calendar_service.connect, user_id, auth_code),
            )
            if not success:
                await update.message.reply_text(
                    "\u274c No se pudo verificar la autorizacion.\n\n"
                    "Posibles causas:\n"
                    "- El codigo ya fue usado (solo sirve una vez)\n"
                    "- Copiaste el codigo incompleto\n\n"
                    "Envia /calendar para intentar de nuevo."
                )
                return ConversationHandler.END

            # Show confirmation with next 3 events
            events = self._calendar_service.get_events_today(user_id)
            confirmation = "\u2705 <b>Google Calendar conectado exitosamente!</b>\n\n"

            if events:
                confirmation += "\U0001f4c6 Proximos eventos de hoy:\n"
                for event in events[:3]:
                    time_str = event.start.strftime("%H:%M")
                    confirmation += f"  \u2022 {time_str} — {event.title}\n"
            else:
                confirmation += "No tienes eventos para hoy."

            confirmation += "\n\nUsa /plan para generar tu plan del dia."
            await update.message.reply_text(confirmation, parse_mode="HTML")
            return ConversationHandler.END

        except Exception as exc:
            logger.error(
                "Error processing calendar auth code",
                extra={"user_id": user_id, "error": str(exc)},
            )
            await update.message.reply_text(
                "\u274c Ocurrio un error al procesar el codigo.\n"
                "Envia /calendar para intentar de nuevo."
            )
            return ConversationHandler.END

    async def _calendar_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the OAuth flow."""
        if update.message:
            await update.message.reply_text("Conexion de calendario cancelada.")
        return ConversationHandler.END

    # ------------------------------------------------------------------
    # /plan command — Generate and display day plan
    # ------------------------------------------------------------------

    async def plan_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /plan and /plan tomorrow commands."""
        if not update.effective_user or not update.message:
            return

        user_id = str(update.effective_user.id)

        # Determine target date using user's local timezone
        args = context.args if context.args else []
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            # Try to get user's timezone from preferences
            from ppai.push.domain.entities import UserNudgePreferences
            tz = ZoneInfo("America/Bogota")  # default
        except (ZoneInfoNotFoundError, Exception):
            tz = ZoneInfo("America/Bogota")
        now = datetime.now(tz)
        if args and args[0].lower() in ("tomorrow", "manana", "mañana"):
            target_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            date_label = "manana"
        else:
            target_date = now.strftime("%Y-%m-%d")
            date_label = "hoy"

        # Check for existing plan
        existing_blocks = self._block_repo.get_plan(user_id, target_date)
        if existing_blocks:
            plan_text = self._format_plan_message(existing_blocks, [], target_date, date_label)
            keyboard = self._build_plan_keyboard(existing_blocks)
            await update.message.reply_text(plan_text, parse_mode="Markdown", reply_markup=keyboard)
            return

        # Fetch calendar events if connected
        calendar_events = []
        if self._calendar_service.is_connected(user_id):
            calendar_events = self._calendar_service.get_events_for_date(user_id, target_date)

        # Get pending/prioritized tasks
        from ppai.capture.domain.value_objects import TaskStatus

        pending_tasks = self._task_repo.list_by_status(user_id, TaskStatus.PENDING)
        prioritized_tasks = self._task_repo.list_by_status(user_id, TaskStatus.PRIORITIZED)
        all_tasks = prioritized_tasks + pending_tasks  # prioritized first

        if not all_tasks:
            await update.message.reply_text(
                f"\U0001f4cb *Plan para {date_label}*\n\n"
                "No tienes tareas pendientes para planificar.\n"
                "Envia una tarea para comenzar.",
                parse_mode="Markdown",
            )
            return

        # Build task dicts with classification
        task_dicts = []
        for task in all_tasks:
            tags = [task.tag] if task.tag else []
            category_val = task.category or self._classifier.classify(task.normalized_text, tags).value
            # Prefer task's own estimated_minutes (set by user or classifier at capture)
            estimated = task.estimated_minutes or self._classifier.estimate_minutes(task.normalized_text)
            task_dicts.append({
                "task_id": task.task_id,
                "title": task.normalized_text,
                "category": category_val if isinstance(category_val, str) else category_val.value,
                "estimated_minutes": estimated,
                "requested_slot_start": task.requested_slot_start,
                "requested_slot_end": task.requested_slot_end,
            })

        # Generate plan
        plan = self._block_planner.generate_plan(
            user_id=user_id,
            date=target_date,
            tasks=task_dicts,
            calendar_events=calendar_events,
        )

        # Save blocks to DynamoDB
        if plan.blocks:
            self._block_repo.save_plan(plan.blocks)

        # Sync to Google Calendar (best-effort)
        synced = self._calendar_sync.sync_plan_to_calendar(user_id, plan)
        if synced > 0:
            # Re-save blocks with calendar_event_ids
            self._block_repo.save_plan(plan.blocks)

        # Format and send
        plan_text = self._format_plan_message(plan.blocks, plan.calendar_events, target_date, date_label)
        keyboard = self._build_plan_keyboard(plan.blocks)
        await update.message.reply_text(plan_text, parse_mode="Markdown", reply_markup=keyboard)

    # ------------------------------------------------------------------
    # Callback handlers for block status changes
    # ------------------------------------------------------------------

    async def block_callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle block_done and block_skip callbacks."""
        query = update.callback_query
        if not query or not query.data:
            return

        await query.answer()

        parts = query.data.split(":")
        if len(parts) != 2:
            return

        action, block_id = parts[0], parts[1]
        user_id = str(query.from_user.id) if query.from_user else ""

        if not user_id:
            return

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if action == "block_done":
            new_status = BlockStatus.COMPLETED
            emoji = "\u2705"
            label = "completado"
        elif action == "block_skip":
            new_status = BlockStatus.SKIPPED
            emoji = "\u23ed\ufe0f"
            label = "omitido"
        else:
            return

        try:
            # Try today first, then tomorrow
            block = self._block_repo.get_block(block_id, user_id, today)
            block_date = today
            if block is None:
                tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
                block = self._block_repo.get_block(block_id, user_id, tomorrow)
                block_date = tomorrow

            if block is None:
                await query.edit_message_text("No se encontro el bloque.")
                return

            self._block_repo.update_block_status(block_id, user_id, block_date, new_status)
            block.status = new_status

            # Update calendar event (best-effort)
            self._calendar_sync.update_block_in_calendar(user_id, block)

            await query.edit_message_text(
                f"{emoji} Bloque *{block.task_title}* marcado como {label}.",
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.error("Error updating block status", extra={"block_id": block_id, "error": str(exc)})
            await query.edit_message_text("Error al actualizar el bloque. Intenta de nuevo.")

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_plan_message(
        self,
        blocks: list,
        calendar_events: list,
        date: str,
        date_label: str,
    ) -> str:
        """Format a plan as a Telegram message in Spanish."""
        lines = [f"\U0001f4cb *Plan para {date_label}* ({date})\n"]

        if calendar_events:
            lines.append("\U0001f4c6 *Eventos del calendario:*")
            for event in calendar_events:
                if event.is_all_day:
                    lines.append(f"  \U0001f30d {event.title} (todo el dia)")
                else:
                    start_str = event.start.strftime("%H:%M")
                    end_str = event.end.strftime("%H:%M")
                    lines.append(f"  \u2022 {start_str}-{end_str} {event.title}")
            lines.append("")

        if blocks:
            lines.append("\U0001f4cc *Bloques de tiempo:*")
            for block in blocks:
                status_emoji = _STATUS_EMOJI.get(block.status, "\U0001f4cb")
                cat_emoji = _CATEGORY_EMOJI.get(block.category.value if hasattr(block.category, 'value') else block.category, "\U0001f3e0")
                start_str = block.start.strftime("%H:%M")
                end_str = block.end.strftime("%H:%M")
                lines.append(
                    f"  {status_emoji} {start_str}-{end_str} {cat_emoji} {block.task_title}"
                )
        else:
            lines.append("No se pudieron asignar bloques de tiempo.")

        return "\n".join(lines)

    def _build_plan_keyboard(self, blocks: list) -> InlineKeyboardMarkup | None:
        """Build inline keyboard with done/skip buttons for planned blocks."""
        from ppai.calendar.domain.value_objects import BlockStatus as BS

        planned_blocks = [b for b in blocks if b.status == BS.PLANNED]
        if not planned_blocks:
            return None

        keyboard = []
        for block in planned_blocks:
            row = [
                InlineKeyboardButton(
                    f"\u2705 {block.task_title[:20]}",
                    callback_data=f"block_done:{block.block_id}",
                ),
                InlineKeyboardButton(
                    "\u23ed\ufe0f Omitir",
                    callback_data=f"block_skip:{block.block_id}",
                ),
            ]
            keyboard.append(row)

        return InlineKeyboardMarkup(keyboard)

"""ER3 Telegram callback adapter for proactive notification responses."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ppai.calendar.domain.value_objects import BlockStatus
from ppai.push.application.friction_detector import FrictionDetector
from ppai.shared.infrastructure.user_registry import UserRegistry

logger = logging.getLogger(__name__)


class ER3CallbackAdapter:
    """Handles inline keyboard callbacks for ER3 proactive notifications.

    Covers:
    - Block reminder responses (block_start, block_delay, block_skip_reminder)
    - Block check-in responses (block_complete, block_more_time, block_no_progress)
    - Friction responses (friction_divide, friction_info, friction_delete, friction_pomodoro)
    - Gap responses (gap_reassign, gap_continue, gap_rest)
    - Midday check-in responses (midday_afternoon, midday_unplanned, midday_help, midday_now)
    """

    def __init__(
        self,
        block_repo,
        task_repo,
        friction_detector: FrictionDetector,
        decision_service=None,
        user_registry: UserRegistry | None = None,
    ) -> None:
        self._block_repo = block_repo
        self._task_repo = task_repo
        self._friction_detector = friction_detector
        self._decision_service = decision_service
        self._user_registry = user_registry

    async def callback_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Route ER3 callback queries to the appropriate handler."""
        query = update.callback_query
        if query is None or query.from_user is None:
            return

        await query.answer()

        user_id = str(query.from_user.id)
        data = query.data or ""

        if self._user_registry:
            self._user_registry.register(user_id)

        try:
            action, payload = data.split(":", 1)
        except ValueError:
            logger.warning("er3.callback.invalid_data", extra={"data": data})
            return

        try:
            # Block reminder responses
            if action == "block_start":
                await self._handle_block_start(query, user_id, payload)
            elif action == "block_delay":
                await self._handle_block_delay(query, user_id, payload)
            elif action == "block_skip_reminder":
                await self._handle_block_skip(query, user_id, payload)

            # Block check-in responses
            elif action == "block_complete":
                await self._handle_block_complete(query, user_id, payload)
            elif action == "block_more_time":
                await self._handle_block_more_time(query, user_id, payload)
            elif action == "block_no_progress":
                await self._handle_block_no_progress(query, user_id, payload)

            # Friction responses
            elif action == "friction_divide":
                await self._handle_friction_divide(query, user_id, payload)
            elif action == "friction_info":
                await self._handle_friction_info(query, user_id, payload)
            elif action == "friction_delete":
                await self._handle_friction_delete(query, user_id, payload)
            elif action == "friction_pomodoro":
                await self._handle_friction_pomodoro(query, user_id, payload)

            # Gap responses
            elif action == "gap_reassign":
                await self._handle_gap_reassign(query, user_id)
            elif action == "gap_continue":
                await self._handle_gap_continue(query, user_id)
            elif action == "gap_rest":
                await self._handle_gap_rest(query, user_id)

            # Midday responses
            elif action == "midday_afternoon":
                await self._handle_midday_afternoon(query, user_id)
            elif action == "midday_unplanned":
                await self._handle_midday_unplanned(query, user_id)
            elif action == "midday_help":
                await self._handle_midday_help(query, user_id)
            elif action == "midday_now":
                await self._handle_midday_now(query, user_id)

            else:
                logger.warning("er3.callback.unknown_action", extra={"action": action})

        except Exception:
            logger.exception("er3.callback.error", extra={"user_id": user_id, "action": data})
            await query.message.reply_text("Ocurrio un error. Intenta de nuevo.")

    # ------------------------------------------------------------------
    # Block reminder handlers
    # ------------------------------------------------------------------

    async def _handle_block_start(self, query, user_id: str, block_id: str) -> None:
        """Mark block as in_progress."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        block = self._block_repo.get_block(block_id, user_id, today)
        if block is None:
            await query.edit_message_text("No se encontro el bloque.")
            return

        self._block_repo.update_block_status(block_id, user_id, today, BlockStatus.IN_PROGRESS)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Bloque *{block.task_title}* iniciado. A darle!",
            parse_mode="Markdown",
        )

    async def _handle_block_delay(self, query, user_id: str, block_id: str) -> None:
        """Delay block start by 15 minutes (informational — block stays planned)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        block = self._block_repo.get_block(block_id, user_id, today)
        if block is None:
            await query.edit_message_text("No se encontro el bloque.")
            return

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"OK, te recuerdo *{block.task_title}* en 15 minutos.",
            parse_mode="Markdown",
        )

    async def _handle_block_skip(self, query, user_id: str, block_id: str) -> None:
        """Skip the block."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        block = self._block_repo.get_block(block_id, user_id, today)
        if block is None:
            await query.edit_message_text("No se encontro el bloque.")
            return

        self._block_repo.update_block_status(block_id, user_id, today, BlockStatus.SKIPPED)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Bloque *{block.task_title}* omitido.",
            parse_mode="Markdown",
        )

    # ------------------------------------------------------------------
    # Block check-in handlers
    # ------------------------------------------------------------------

    async def _handle_block_complete(self, query, user_id: str, block_id: str) -> None:
        """Mark block as completed at check-in."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        block = self._block_repo.get_block(block_id, user_id, today)
        if block is None:
            await query.edit_message_text("No se encontro el bloque.")
            return

        self._block_repo.update_block_status(block_id, user_id, today, BlockStatus.COMPLETED)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Excelente! Bloque *{block.task_title}* completado.",
            parse_mode="Markdown",
        )

    async def _handle_block_more_time(self, query, user_id: str, block_id: str) -> None:
        """User needs more time — acknowledge and keep block in_progress."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        block = self._block_repo.get_block(block_id, user_id, today)
        if block is None:
            await query.edit_message_text("No se encontro el bloque.")
            return

        # Keep block as in_progress
        self._block_repo.update_block_status(block_id, user_id, today, BlockStatus.IN_PROGRESS)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Entendido. Sigue con *{block.task_title}*, te aviso cuando termine el siguiente bloque.",
            parse_mode="Markdown",
        )

    async def _handle_block_no_progress(self, query, user_id: str, block_id: str) -> None:
        """User didn't make progress — ask what blocked them."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        block = self._block_repo.get_block(block_id, user_id, today)
        if block is None:
            await query.edit_message_text("No se encontro el bloque.")
            return

        # Save friction note on the task
        task = self._task_repo.get_by_id(user_id, block.task_id)
        if task:
            friction_notes = getattr(task, "friction_notes", [])
            friction_notes.append(
                f"No progress during block on {today}"
            )
            task.friction_notes = friction_notes
            task.updated_at = datetime.now(timezone.utc)
            self._task_repo.save(task)

        self._block_repo.update_block_status(block_id, user_id, today, BlockStatus.SKIPPED)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Sin problema. Anote que *{block.task_title}* tuvo friccion hoy. "
            f"Si quieres, cuentame que te bloqueo para tomarlo en cuenta.",
            parse_mode="Markdown",
        )

    # ------------------------------------------------------------------
    # Friction handlers
    # ------------------------------------------------------------------

    async def _handle_friction_divide(self, query, user_id: str, task_id: str) -> None:
        """Ask user for sub-task descriptions to divide the stuck task."""
        task = self._task_repo.get_by_id(user_id, task_id)
        if task is None:
            await query.edit_message_text("No encontre esa tarea.")
            return

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Vamos a dividir *{task.normalized_text}*.\n"
            f"Escribeme las sub-tareas separadas por coma.\n"
            f"Ejemplo: investigar X, implementar Y, probar Z",
            parse_mode="Markdown",
        )
        # Note: The free-text response for division would be handled by a
        # ConversationHandler or a separate message handler. For now, this
        # prompts the user. A full implementation would track state.

    async def _handle_friction_info(self, query, user_id: str, task_id: str) -> None:
        """Mark task as needing info."""
        from ppai.capture.domain.value_objects import TaskStatus

        task = self._task_repo.get_by_id(user_id, task_id)
        if task is None:
            await query.edit_message_text("No encontre esa tarea.")
            return

        task.status = TaskStatus.NEEDS_CLARIFICATION
        task.updated_at = datetime.now(timezone.utc)
        friction_notes = getattr(task, "friction_notes", [])
        friction_notes.append("User reported needing more info")
        task.friction_notes = friction_notes
        self._task_repo.save(task)

        if self._decision_service:
            self._decision_service.invalidate_cache(user_id)

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Entendido. *{task.normalized_text}* marcada como 'necesita info'.\n"
            f"Cuando tengas lo que necesitas, puedes retomarla.",
            parse_mode="Markdown",
        )

    async def _handle_friction_delete(self, query, user_id: str, task_id: str) -> None:
        """Mark task as done (effectively removing it)."""
        from ppai.capture.domain.value_objects import TaskStatus

        task = self._task_repo.get_by_id(user_id, task_id)
        if task is None:
            await query.edit_message_text("No encontre esa tarea.")
            return

        task.status = TaskStatus.DONE
        task.completed_at = datetime.now(timezone.utc)
        task.updated_at = datetime.now(timezone.utc)
        friction_notes = getattr(task, "friction_notes", [])
        friction_notes.append("Eliminated via friction detector")
        task.friction_notes = friction_notes
        self._task_repo.save(task)

        if self._decision_service:
            self._decision_service.invalidate_cache(user_id)

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Tarea *{task.normalized_text}* eliminada. A veces soltar es avanzar.",
            parse_mode="Markdown",
        )

    async def _handle_friction_pomodoro(self, query, user_id: str, task_id: str) -> None:
        """Create immediate 25-min pomodoro block."""
        block = self._friction_detector.handle_pomodoro(user_id, task_id)
        if block is None:
            await query.edit_message_text("No encontre esa tarea.")
            return

        end_str = block.end.strftime("%H:%M")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"Pomodoro de 25 min iniciado para *{block.task_title}*.\n"
            f"Termina a las {end_str}. Concentrate!",
            parse_mode="Markdown",
        )

    # ------------------------------------------------------------------
    # Gap handlers
    # ------------------------------------------------------------------

    async def _handle_gap_reassign(self, query, user_id: str) -> None:
        """Reassign an urgent task to the freed gap."""
        await query.edit_message_reply_markup(reply_markup=None)

        # Show top 3 tasks for user to pick
        if self._decision_service:
            try:
                top3 = self._decision_service.get_top3(user_id)
                if top3 and not top3.is_empty():
                    lines = ["Elige la tarea para reasignar:"]
                    for i, score in enumerate(top3.ranked_scores[:3], 1):
                        task = self._task_repo.get_by_id(user_id, score.task_id)
                        title = task.normalized_text if task else score.task_id
                        lines.append(f"{i}. {title}")
                    await query.message.reply_text("\n".join(lines))
                    return
            except Exception:
                pass

        await query.message.reply_text(
            "Usa /plan para reorganizar tu dia con el nuevo espacio."
        )

    async def _handle_gap_continue(self, query, user_id: str) -> None:
        """Continue current in-progress task."""
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Perfecto, sigue con lo que estabas. Buen enfoque!"
        )

    async def _handle_gap_rest(self, query, user_id: str) -> None:
        """Take a break."""
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Buen momento para un descanso. Aprovecha para desconectar un rato."
        )

    # ------------------------------------------------------------------
    # Midday handlers
    # ------------------------------------------------------------------

    async def _handle_midday_afternoon(self, query, user_id: str) -> None:
        """Bad day, will pick up in the afternoon."""
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Entendido. No te preocupes, la tarde puede ser productiva. "
            "Te aviso cuando empiece tu siguiente bloque."
        )

    async def _handle_midday_unplanned(self, query, user_id: str) -> None:
        """Unplanned things came up."""
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Pasa seguido. Cuentame que surgio y lo capturo como tarea completada "
            "para que quede registrado en tu dia."
        )

    async def _handle_midday_help(self, query, user_id: str) -> None:
        """User needs help."""
        await query.edit_message_reply_markup(reply_markup=None)

        # Show current pending tasks
        if self._decision_service:
            try:
                top3 = self._decision_service.get_top3(user_id)
                if top3 and not top3.is_empty():
                    lines = ["Tu Top 3 actual:"]
                    for i, score in enumerate(top3.ranked_scores[:3], 1):
                        task = self._task_repo.get_by_id(user_id, score.task_id)
                        title = task.normalized_text if task else score.task_id
                        lines.append(f"{i}. {title}")
                    lines.append("\nQuieres dividir alguna? Usa el numero.")
                    await query.message.reply_text("\n".join(lines))
                    return
            except Exception:
                pass

        await query.message.reply_text(
            "Puedo ayudarte a reorganizar. Usa /plan para replanificar la tarde."
        )

    async def _handle_midday_now(self, query, user_id: str) -> None:
        """User will do them now."""
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Eso! Arranca con el bloque mas importante. Tu puedes!"
        )

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ppai.calendar.application.block_planner import BlockPlanner
from ppai.calendar.application.calendar_service import CalendarService
from ppai.capture.application.ports import TaskStateRepository
from ppai.profile.application.profile_service import ProfileService

logger = logging.getLogger(__name__)


class ScheduleCallbackAdapter:
    """ER5: Handles calendar scheduling after task capture.

    Two flows:
    1. Explicit slot (#HH:MM-HH:MM) → auto-create event (HU-R5.2)
    2. Duration only (30min, 1h) → suggest next free slot with buttons (HU-R5.3)
    """

    def __init__(
        self,
        calendar_service: CalendarService,
        block_planner: BlockPlanner,
        task_repo: TaskStateRepository,
        profile_service: ProfileService,
    ) -> None:
        self._calendar_service = calendar_service
        self._block_planner = block_planner
        self._task_repo = task_repo
        self._profile_service = profile_service

    async def handle_post_capture(
        self,
        update: Update,
        user_id: str,
        task_id: str,
        task_title: str,
        estimated_minutes: int | None,
        slot_start: str | None,
        slot_end: str | None,
    ) -> None:
        """Called after capture to schedule or suggest scheduling."""
        if not update.message:
            return

        if not self._calendar_service.is_connected(user_id):
            # No calendar → only mention if they had time info
            if slot_start or estimated_minutes:
                await update.message.reply_text(
                    "Conecta tu Google Calendar con `/calendar` "
                    "para agendar tareas directamente.",
                    parse_mode="Markdown",
                )
            return

        if slot_start and slot_end:
            await self._handle_explicit_slot(
                update, user_id, task_id, task_title, slot_start, slot_end
            )
        elif estimated_minutes:
            await self._handle_duration_suggestion(
                update, user_id, task_id, task_title, estimated_minutes
            )

    async def _handle_explicit_slot(
        self,
        update: Update,
        user_id: str,
        task_id: str,
        title: str,
        slot_start: str,
        slot_end: str,
    ) -> None:
        """HU-R5.2: Create event at explicit time slot."""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        try:
            sh, sm = map(int, slot_start.split(":"))
            eh, em = map(int, slot_end.split(":"))
        except (ValueError, TypeError):
            return

        slot_start_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
        slot_end_dt = now.replace(hour=eh, minute=em, second=0, microsecond=0)

        # Check if slot already passed
        if slot_end_dt <= now:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "Hoy otro horario",
                        callback_data=f"schedule_suggest:{task_id}",
                    ),
                    InlineKeyboardButton(
                        "Manana mismo horario",
                        callback_data=f"schedule_tomorrow:{task_id}:{slot_start}-{slot_end}",
                    ),
                ]
            ])
            await update.message.reply_text(
                f"El horario {slot_start}-{slot_end} ya paso. Que prefieres?",
                reply_markup=keyboard,
            )
            return

        # Check for conflicts
        events = self._calendar_service.get_events_for_date(user_id, today_str)
        for event in events:
            if event.is_all_day:
                continue
            if event.start < slot_end_dt and event.end > slot_start_dt:
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "Buscar hueco libre",
                            callback_data=f"schedule_suggest:{task_id}",
                        ),
                        InlineKeyboardButton(
                            "No agendar",
                            callback_data=f"schedule_no:{task_id}",
                        ),
                    ]
                ])
                await update.message.reply_text(
                    f"Hay un conflicto con *{event.summary}* ({event.start.strftime('%H:%M')}-{event.end.strftime('%H:%M')}).",
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                return

        # No conflicts — create the event
        event_id = self._calendar_service.create_calendar_event(
            user_id=user_id,
            title=f"[PPAI] {title}",
            start=slot_start_dt.isoformat(),
            end=slot_end_dt.isoformat(),
        )

        if event_id:
            await update.message.reply_text(
                f"Agendado de {slot_start} a {slot_end} en tu calendario."
            )
        else:
            await update.message.reply_text(
                "No pude crear el evento en tu calendario. Intenta con `/plan`.",
                parse_mode="Markdown",
            )

    async def _handle_duration_suggestion(
        self,
        update: Update,
        user_id: str,
        task_id: str,
        title: str,
        estimated_minutes: int,
    ) -> None:
        """HU-R5.3: Suggest next free slot for task with duration."""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        # Get user profile for work hours
        work_start, work_end = 9, 18
        try:
            profile = self._profile_service.get_profile(user_id)
            if profile:
                if profile.work_start:
                    work_start = int(profile.work_start.split(":")[0])
                if profile.work_end:
                    work_end = int(profile.work_end.split(":")[0])
        except Exception:
            pass

        # Check if there's enough time left today
        end_of_work = now.replace(hour=work_end, minute=0, second=0, microsecond=0)
        if now + timedelta(minutes=estimated_minutes) > end_of_work:
            # Suggest tomorrow
            tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            suggested_start = f"{work_start:02d}:00"
            eh = work_start + (estimated_minutes // 60)
            em = estimated_minutes % 60
            suggested_end = f"{eh:02d}:{em:02d}"

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        f"Si, {suggested_start}-{suggested_end}",
                        callback_data=f"schedule_yes:{task_id}:{tomorrow_str}:{suggested_start}-{suggested_end}",
                    ),
                    InlineKeyboardButton(
                        "No agendar",
                        callback_data=f"schedule_no:{task_id}",
                    ),
                ]
            ])
            await update.message.reply_text(
                f"No queda tiempo hoy. Agendar manana de {suggested_start} a {suggested_end}?",
                reply_markup=keyboard,
            )
            return

        # Find free slots today
        events = self._calendar_service.get_events_for_date(user_id, today_str)
        occupied: list[tuple[datetime, datetime]] = []
        for event in events:
            if not event.is_all_day:
                occupied.append((event.start, event.end))

        # Find the next slot from now
        window_start = max(now, now.replace(hour=work_start, minute=0, second=0, microsecond=0))
        window_end = end_of_work

        free_slots = self._block_planner._find_free_slots(
            today_str, occupied, window_start, window_end
        )

        # Find first slot that fits the duration
        for slot in free_slots:
            if slot.duration_minutes >= estimated_minutes:
                suggested_start = slot.start.strftime("%H:%M")
                suggested_end_dt = slot.start + timedelta(minutes=estimated_minutes)
                suggested_end = suggested_end_dt.strftime("%H:%M")

                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            f"Si, {suggested_start}-{suggested_end}",
                            callback_data=f"schedule_yes:{task_id}:{today_str}:{suggested_start}-{suggested_end}",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "Cambiar hora",
                            callback_data=f"schedule_change:{task_id}",
                        ),
                        InlineKeyboardButton(
                            "No agendar",
                            callback_data=f"schedule_no:{task_id}",
                        ),
                    ],
                ])
                await update.message.reply_text(
                    f"Agendar de {suggested_start} a {suggested_end}?",
                    reply_markup=keyboard,
                )
                return

        # No slots available today → suggest tomorrow
        tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        suggested_start = f"{work_start:02d}:00"
        eh = work_start + (estimated_minutes // 60)
        em = estimated_minutes % 60
        suggested_end = f"{eh:02d}:{em:02d}"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"Si, manana {suggested_start}-{suggested_end}",
                    callback_data=f"schedule_yes:{task_id}:{tomorrow_str}:{suggested_start}-{suggested_end}",
                ),
                InlineKeyboardButton(
                    "No agendar",
                    callback_data=f"schedule_no:{task_id}",
                ),
            ]
        ])
        await update.message.reply_text(
            f"No hay huecos hoy. Agendar manana de {suggested_start} a {suggested_end}?",
            reply_markup=keyboard,
        )

    async def callback_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline button responses for scheduling."""
        query = update.callback_query
        if not query or not query.data:
            return

        await query.answer()
        user_id = str(query.from_user.id)
        data = query.data

        try:
            if data.startswith("schedule_yes:"):
                await self._handle_schedule_yes(query, user_id, data)
            elif data.startswith("schedule_no:"):
                await query.edit_message_text("Tarea capturada sin agendar.")
            elif data.startswith("schedule_suggest:"):
                await self._handle_schedule_suggest(query, user_id, data)
            elif data.startswith("schedule_tomorrow:"):
                await self._handle_schedule_tomorrow(query, user_id, data)
            elif data.startswith("schedule_change:"):
                await query.edit_message_text(
                    "Envia el horario que prefieres en formato HH:MM-HH:MM"
                )
        except Exception:
            logger.exception("Error handling schedule callback", extra={"user_id": user_id})
            await query.edit_message_text("Error al agendar. Usa `/plan` para planificar.")

    async def _handle_schedule_yes(self, query, user_id: str, data: str) -> None:
        """schedule_yes:<task_id>:<date>:<HH:MM-HH:MM>"""
        parts = data.split(":", 3)
        if len(parts) < 4:
            return
        task_id = parts[1]
        date_str = parts[2]
        time_range = parts[3]
        start_str, end_str = time_range.split("-")

        task = self._task_repo.get_by_id(user_id, task_id)
        title = task.normalized_text if task else "Tarea"

        base_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        start_dt = base_date.replace(hour=sh, minute=sm)
        end_dt = base_date.replace(hour=eh, minute=em)

        event_id = self._calendar_service.create_calendar_event(
            user_id=user_id,
            title=f"[PPAI] {title}",
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
        )

        if event_id:
            await query.edit_message_text(
                f"Agendado de {start_str} a {end_str} ({date_str})."
            )
        else:
            await query.edit_message_text("No pude crear el evento. Intenta con /plan.")

    async def _handle_schedule_suggest(self, query, user_id: str, data: str) -> None:
        """schedule_suggest:<task_id> — find next free slot and create event."""
        task_id = data.split(":")[1]
        task = self._task_repo.get_by_id(user_id, task_id)
        if not task or not task.estimated_minutes:
            await query.edit_message_text("No pude encontrar la tarea. Usa /plan.")
            return

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        events = self._calendar_service.get_events_for_date(user_id, today_str)
        occupied = [(e.start, e.end) for e in events if not e.is_all_day]

        work_end = 18
        try:
            profile = self._profile_service.get_profile(user_id)
            if profile and profile.work_end:
                work_end = int(profile.work_end.split(":")[0])
        except Exception:
            pass

        window_end = now.replace(hour=work_end, minute=0, second=0, microsecond=0)
        free_slots = self._block_planner._find_free_slots(today_str, occupied, now, window_end)

        for slot in free_slots:
            if slot.duration_minutes >= task.estimated_minutes:
                start_dt = slot.start
                end_dt = start_dt + timedelta(minutes=task.estimated_minutes)
                event_id = self._calendar_service.create_calendar_event(
                    user_id=user_id,
                    title=f"[PPAI] {task.normalized_text}",
                    start=start_dt.isoformat(),
                    end=end_dt.isoformat(),
                )
                if event_id:
                    await query.edit_message_text(
                        f"Agendado de {start_dt.strftime('%H:%M')} a {end_dt.strftime('%H:%M')}."
                    )
                else:
                    await query.edit_message_text("No pude crear el evento. Usa /plan.")
                return

        await query.edit_message_text("No hay huecos libres hoy. Usa `/plan manana`.")

    async def _handle_schedule_tomorrow(self, query, user_id: str, data: str) -> None:
        """schedule_tomorrow:<task_id>:<HH:MM-HH:MM>"""
        parts = data.split(":", 2)
        if len(parts) < 3:
            return
        task_id = parts[1]
        time_range = parts[2]
        start_str, end_str = time_range.split("-")

        task = self._task_repo.get_by_id(user_id, task_id)
        title = task.normalized_text if task else "Tarea"

        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")
        base_date = datetime.strptime(tomorrow_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        start_dt = base_date.replace(hour=sh, minute=sm)
        end_dt = base_date.replace(hour=eh, minute=em)

        event_id = self._calendar_service.create_calendar_event(
            user_id=user_id,
            title=f"[PPAI] {title}",
            start=start_dt.isoformat(),
            end=end_dt.isoformat(),
        )

        if event_id:
            await query.edit_message_text(
                f"Agendado manana de {start_str} a {end_str}."
            )
        else:
            await query.edit_message_text("No pude crear el evento. Intenta con /plan.")

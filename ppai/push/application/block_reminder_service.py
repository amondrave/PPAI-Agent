"""ER3 HU-R3.1 — Block start/end reminders for scheduled time blocks."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import structlog

from ppai.profile.application.ports import ProfileRepository
from ppai.profile.domain.value_objects import CommunicationStyle
from ppai.push.application.ports import CycleEventRepository, TelegramPushPort
from ppai.push.domain.value_objects import DispatchOutcome, NudgeDispatchStatus

logger = structlog.get_logger(__name__)

_REMINDER_MINUTES_BEFORE = 5
_PROHIBITED_PHRASES = (
    "debias", "ya vas tarde", "otra vez", "no hiciste",
    "deberias", "fallaste", "no avanzaste",
)


class BlockReminderService:
    """Evaluates and sends block start reminders and end-of-block check-ins."""

    def __init__(
        self,
        block_repo,
        telegram_port: TelegramPushPort,
        cycle_event_repo: CycleEventRepository,
        profile_repo: Optional[ProfileRepository] = None,
    ) -> None:
        self._block_repo = block_repo
        self._telegram = telegram_port
        self._cycle_event_repo = cycle_event_repo
        self._profile_repo = profile_repo

    def evaluate_block_reminders(
        self,
        user_id: str,
        now: datetime,
        cycle_id: str,
    ) -> list[DispatchOutcome]:
        """Check all today's blocks and send start reminders / end check-ins."""
        results: list[DispatchOutcome] = []
        today_str = now.strftime("%Y-%m-%d")
        blocks = self._block_repo.get_plan(user_id, today_str)

        if not blocks:
            return results

        profile = self._get_profile(user_id)
        style = profile.communication_style if profile else None

        for block in blocks:
            # Skip completed or skipped blocks
            if block.status.value in ("completed", "skipped"):
                continue

            # 5 min before block start: send reminder
            reminder_time = block.start - timedelta(minutes=_REMINDER_MINUTES_BEFORE)
            if reminder_time <= now < block.start:
                event_key = f"BLOCK_REMINDER_SENT_{block.block_id}"
                if not self._cycle_event_repo.has_event_today(cycle_id, event_key):
                    outcome = self._send_start_reminder(
                        user_id, block, cycle_id, style, now,
                    )
                    if outcome:
                        results.append(outcome)

            # At block end time: send check-in
            end_tolerance = timedelta(minutes=2)
            if block.end <= now < block.end + end_tolerance:
                event_key = f"BLOCK_CHECKIN_SENT_{block.block_id}"
                if not self._cycle_event_repo.has_event_today(cycle_id, event_key):
                    outcome = self._send_end_checkin(
                        user_id, block, cycle_id, style, now,
                    )
                    if outcome:
                        results.append(outcome)

        return results

    def has_active_blocks_today(self, user_id: str, now: datetime) -> bool:
        """Check if user has any planned/in_progress blocks today."""
        today_str = now.strftime("%Y-%m-%d")
        blocks = self._block_repo.get_plan(user_id, today_str)
        return any(
            b.status.value in ("planned", "in_progress")
            for b in blocks
        )

    def _send_start_reminder(
        self, user_id, block, cycle_id, style, now,
    ) -> Optional[DispatchOutcome]:
        """Send a block start reminder with action buttons."""
        duration_min = int((block.end - block.start).total_seconds() / 60)

        if style == CommunicationStyle.GENTLE:
            text = (
                f"En 5 minutos empieza tu bloque:\n"
                f"*{block.task_title}* ({duration_min} min)\n\n"
                f"Cuando estes listo, dale arrancar."
            )
        elif style == CommunicationStyle.DIRECT:
            text = (
                f"Bloque en 5 min: *{block.task_title}* ({duration_min} min)"
            )
        elif style == CommunicationStyle.CONFRONTATIONAL:
            text = (
                f"*{block.task_title}* empieza en 5 min ({duration_min} min). "
                f"Preparate."
            )
        else:
            text = (
                f"Recordatorio: tu bloque *{block.task_title}* "
                f"({duration_min} min) empieza en 5 minutos."
            )

        buttons = [[
            {"text": "Arrancar", "callback_data": f"block_start:{block.block_id}"},
            {"text": "+15min", "callback_data": f"block_delay:{block.block_id}"},
            {"text": "Saltar", "callback_data": f"block_skip_reminder:{block.block_id}"},
        ]]

        sent = self._telegram.send_message_with_buttons(str(user_id), text, buttons)
        if sent:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle_id,
                event_type=f"BLOCK_REMINDER_SENT_{block.block_id}",
                metadata={"block_id": block.block_id, "sent_at": now.isoformat()},
            )
            logger.info("block_reminder.sent", user_id=user_id, block_id=block.block_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.sent,
                user_id=user_id,
                cycle_id=cycle_id,
                sent_at=now,
                reason="block_reminder",
            )
        return DispatchOutcome(
            status=NudgeDispatchStatus.failed,
            user_id=user_id,
            reason="block_reminder_send_failed",
        )

    def _send_end_checkin(
        self, user_id, block, cycle_id, style, now,
    ) -> Optional[DispatchOutcome]:
        """Send a block end check-in with action buttons."""
        if style == CommunicationStyle.GENTLE:
            text = (
                f"Tu bloque *{block.task_title}* acaba de terminar.\n"
                f"Como te fue?"
            )
        elif style == CommunicationStyle.DIRECT:
            text = f"Fin del bloque *{block.task_title}*. Estado?"
        elif style == CommunicationStyle.CONFRONTATIONAL:
            text = (
                f"Tiempo del bloque *{block.task_title}*. "
                f"Dime como quedo."
            )
        else:
            text = (
                f"Tu bloque *{block.task_title}* ha terminado. "
                f"Como te fue?"
            )

        buttons = [[
            {"text": "Complete", "callback_data": f"block_complete:{block.block_id}"},
            {"text": "Mas tiempo", "callback_data": f"block_more_time:{block.block_id}"},
            {"text": "No avance", "callback_data": f"block_no_progress:{block.block_id}"},
        ]]

        sent = self._telegram.send_message_with_buttons(str(user_id), text, buttons)
        if sent:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle_id,
                event_type=f"BLOCK_CHECKIN_SENT_{block.block_id}",
                metadata={"block_id": block.block_id, "sent_at": now.isoformat()},
            )
            logger.info("block_checkin.sent", user_id=user_id, block_id=block.block_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.sent,
                user_id=user_id,
                cycle_id=cycle_id,
                sent_at=now,
                reason="block_checkin",
            )
        return DispatchOutcome(
            status=NudgeDispatchStatus.failed,
            user_id=user_id,
            reason="block_checkin_send_failed",
        )

    def _get_profile(self, user_id: str):
        if not self._profile_repo:
            return None
        try:
            return self._profile_repo.get(user_id)
        except Exception:
            return None

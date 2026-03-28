"""ER3 HU-R3.5 — Midday check-in for low activity days."""

from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from typing import Optional

import structlog

from ppai.profile.domain.value_objects import CommunicationStyle
from ppai.push.application.ports import CycleEventRepository, TelegramPushPort
from ppai.push.domain.value_objects import DispatchOutcome, NudgeDispatchStatus

logger = structlog.get_logger(__name__)

_MIDDAY_TOLERANCE_MINUTES = 7


class MiddayCheckin:
    """Sends a midday check-in when no blocks have been completed by midday."""

    def __init__(
        self,
        block_repo,
        profile_service,
        telegram_port: TelegramPushPort,
        cycle_event_repo: CycleEventRepository,
    ) -> None:
        self._block_repo = block_repo
        self._profile_service = profile_service
        self._telegram = telegram_port
        self._cycle_event_repo = cycle_event_repo

    def evaluate_midday(
        self,
        user_id: str,
        now: datetime,
        cycle_id: str,
        prefs,
    ) -> Optional[DispatchOutcome]:
        """At midpoint of workday, check if activity is low and send check-in."""
        # Guard: only once per day
        if self._cycle_event_repo.has_event_today(cycle_id, "MIDDAY_CHECKIN_SENT"):
            return None

        # Don't send on days off
        try:
            if self._profile_service.is_day_off(user_id, now.date()):
                return None
        except Exception:
            pass

        # Calculate midpoint of workday
        start_time = dtime.fromisoformat(prefs.daily_start_time)
        end_time = dtime.fromisoformat(prefs.daily_end_time)
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        midpoint_minutes = (start_minutes + end_minutes) // 2

        # Check if now is within tolerance of midpoint
        now_minutes = now.hour * 60 + now.minute
        delta = abs(now_minutes - midpoint_minutes)
        if delta > _MIDDAY_TOLERANCE_MINUTES:
            return None

        # Check if any blocks completed today
        today_str = now.strftime("%Y-%m-%d")
        blocks = self._block_repo.get_plan(user_id, today_str)
        completed_count = sum(1 for b in blocks if b.status.value == "completed")

        if completed_count > 0:
            return None  # Activity exists, no need for check-in

        # No completed blocks by midday: send check-in
        profile = None
        try:
            profile = self._profile_service.get_profile(user_id)
        except Exception:
            pass

        style = profile.communication_style if profile else None
        name = profile.name if profile else ""

        if style == CommunicationStyle.GENTLE:
            text = (
                f"{name}, ya vamos a mitad de dia y no hay bloques completados.\n"
                f"Todo bien? Como quieres seguir?"
            )
        elif style == CommunicationStyle.DIRECT:
            text = (
                f"Mitad de dia, 0 bloques completados. "
                f"Que hacemos?"
            )
        elif style == CommunicationStyle.CONFRONTATIONAL:
            text = (
                f"Mitad de dia y nada completado. "
                f"Que paso hoy?"
            )
        else:
            text = (
                f"Vamos a mitad del dia y aun no has completado ningun bloque. "
                f"Como quieres continuar?"
            )

        buttons = [
            [
                {"text": "Mal dia, por la tarde", "callback_data": "midday_afternoon:now"},
                {"text": "Surgieron cosas", "callback_data": "midday_unplanned:now"},
            ],
            [
                {"text": "Necesito ayuda", "callback_data": "midday_help:now"},
                {"text": "Las hago ahora", "callback_data": "midday_now:now"},
            ],
        ]

        sent = self._telegram.send_message_with_buttons(str(user_id), text, buttons)
        if sent:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle_id,
                event_type="MIDDAY_CHECKIN_SENT",
                metadata={"sent_at": now.isoformat(), "blocks_today": str(len(blocks))},
            )
            logger.info("midday_checkin.sent", user_id=user_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.sent,
                user_id=user_id,
                cycle_id=cycle_id,
                sent_at=now,
                reason="midday_checkin",
            )
        return DispatchOutcome(
            status=NudgeDispatchStatus.failed,
            user_id=user_id,
            reason="midday_checkin_send_failed",
        )

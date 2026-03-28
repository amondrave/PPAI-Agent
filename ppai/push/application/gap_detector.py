"""ER3 HU-R3.2 — Gap detector for calendar changes (cancelled/moved events)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import structlog

from ppai.calendar.domain.entities import CalendarEvent
from ppai.profile.domain.value_objects import CommunicationStyle
from ppai.push.application.ports import CycleEventRepository, TelegramPushPort
from ppai.push.domain.value_objects import DispatchOutcome, NudgeDispatchStatus

logger = structlog.get_logger(__name__)

_GAP_CHECK_INTERVAL_MINUTES = 15
_GAP_MIN_DURATION_MINUTES = 15


class GapDetector:
    """Detects calendar gaps (cancelled/moved events) and notifies the user."""

    def __init__(
        self,
        calendar_service,
        profile_service,
        telegram_port: TelegramPushPort,
        cycle_event_repo: CycleEventRepository,
    ) -> None:
        self._calendar_service = calendar_service
        self._profile_service = profile_service
        self._telegram = telegram_port
        self._cycle_event_repo = cycle_event_repo
        # In-memory cache: user_id -> (last_check_time, list of CalendarEvent)
        self._snapshot_cache: dict[str, tuple[datetime, list[CalendarEvent]]] = {}

    def evaluate_gaps(
        self,
        user_id: str,
        now: datetime,
        cycle_id: str,
    ) -> Optional[DispatchOutcome]:
        """Check for new free slots caused by calendar changes."""
        # Don't check on days off
        try:
            if self._profile_service.is_day_off(user_id, now.date()):
                return None
        except Exception:
            pass

        # Rate-limit checks to every 15 min
        cached = self._snapshot_cache.get(user_id)
        if cached:
            last_check, prev_events = cached
            if (now - last_check) < timedelta(minutes=_GAP_CHECK_INTERVAL_MINUTES):
                return None
        else:
            prev_events = []

        # Check if calendar is connected
        if not self._calendar_service.is_connected(user_id):
            return None

        # Fetch current events
        today_str = now.strftime("%Y-%m-%d")
        try:
            current_events = self._calendar_service.get_events_for_date(user_id, today_str)
        except Exception:
            logger.warning("gap_detector.fetch_failed", user_id=user_id)
            return None

        # Update cache
        self._snapshot_cache[user_id] = (now, current_events)

        # First snapshot: no comparison yet
        if not prev_events:
            return None

        # Detect gaps: events in prev that are not in current (removed/moved)
        prev_ids = {e.event_id for e in prev_events if not e.is_all_day}
        current_ids = {e.event_id for e in current_events if not e.is_all_day}
        removed_ids = prev_ids - current_ids

        if not removed_ids:
            return None

        # Find the freed time slots
        removed_events = [e for e in prev_events if e.event_id in removed_ids]
        # Only notify for events that were in the future
        future_removed = [e for e in removed_events if e.start > now]

        if not future_removed:
            return None

        # Guard: don't re-send for same gap
        gap_event_key = f"GAP_DETECTED_{today_str}_{len(removed_ids)}"
        if self._cycle_event_repo.has_event_today(cycle_id, gap_event_key):
            return None

        # Build notification
        profile = None
        try:
            profile = self._profile_service.get_profile(user_id)
        except Exception:
            pass

        style = profile.communication_style if profile else None
        first_gap = future_removed[0]
        gap_duration = int((first_gap.end - first_gap.start).total_seconds() / 60)

        if style == CommunicationStyle.GENTLE:
            text = (
                f"Se libero un espacio de {gap_duration} min en tu calendario "
                f"({first_gap.start.strftime('%H:%M')}-{first_gap.end.strftime('%H:%M')}).\n"
                f"Que quieres hacer?"
            )
        elif style == CommunicationStyle.DIRECT:
            text = (
                f"Hueco libre: {first_gap.start.strftime('%H:%M')}-"
                f"{first_gap.end.strftime('%H:%M')} ({gap_duration} min). Opciones:"
            )
        elif style == CommunicationStyle.CONFRONTATIONAL:
            text = (
                f"Se cancelo algo y tienes {gap_duration} min libres "
                f"({first_gap.start.strftime('%H:%M')}-{first_gap.end.strftime('%H:%M')}). "
                f"Aprovechalos."
            )
        else:
            text = (
                f"Se detecto un espacio libre de {gap_duration} min "
                f"({first_gap.start.strftime('%H:%M')}-{first_gap.end.strftime('%H:%M')}). "
                f"Que quieres hacer?"
            )

        buttons = [[
            {"text": "Reasignar tarea urgente", "callback_data": "gap_reassign:now"},
            {"text": "Continuar tarea", "callback_data": "gap_continue:now"},
            {"text": "Descanso", "callback_data": "gap_rest:now"},
        ]]

        sent = self._telegram.send_message_with_buttons(str(user_id), text, buttons)
        if sent:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle_id,
                event_type=gap_event_key,
                metadata={
                    "removed_event_ids": ",".join(removed_ids),
                    "gap_minutes": str(gap_duration),
                    "sent_at": now.isoformat(),
                },
            )
            logger.info("gap_detector.sent", user_id=user_id, gap_minutes=gap_duration)
            return DispatchOutcome(
                status=NudgeDispatchStatus.sent,
                user_id=user_id,
                cycle_id=cycle_id,
                sent_at=now,
                reason="gap_detected",
            )
        return DispatchOutcome(
            status=NudgeDispatchStatus.failed,
            user_id=user_id,
            reason="gap_notification_send_failed",
        )

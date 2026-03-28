from __future__ import annotations

import logging

from ppai.calendar.application.calendar_service import CalendarService
from ppai.calendar.domain.entities import DayPlan, TimeBlock
from ppai.calendar.domain.value_objects import BlockStatus

logger = logging.getLogger(__name__)

_PPAI_PREFIX = "[PPAI]"


class CalendarSync:
    """Syncs PPAI time blocks to Google Calendar. Best-effort: failures are logged but never break the plan."""

    def __init__(self, calendar_service: CalendarService) -> None:
        self._calendar_service = calendar_service

    def sync_plan_to_calendar(self, user_id: str, plan: DayPlan) -> int:
        """
        Create Google Calendar events for each block in the plan.
        Returns the number of events successfully created.
        """
        if not self._calendar_service.is_connected(user_id):
            return 0

        created = 0
        for block in plan.blocks:
            try:
                title = f"{_PPAI_PREFIX} {block.task_title}"
                description = f"Tarea PPAI: {block.task_title}\nCategoria: {block.category.value}"
                event_id = self._calendar_service.create_calendar_event(
                    user_id=user_id,
                    title=title,
                    start=block.start.isoformat(),
                    end=block.end.isoformat(),
                    description=description,
                )
                if event_id:
                    block.calendar_event_id = event_id
                    created += 1
            except Exception as exc:
                logger.warning(
                    "Failed to sync block to calendar",
                    extra={"user_id": user_id, "block_id": block.block_id, "error": str(exc)},
                )

        return created

    def update_block_in_calendar(self, user_id: str, block: TimeBlock) -> bool:
        """
        Update or delete the calendar event when a block status changes.
        Best-effort: returns False on failure.
        """
        if not block.calendar_event_id:
            return False

        if not self._calendar_service.is_connected(user_id):
            return False

        try:
            auth = self._calendar_service._auth_repo.get(user_id)
            if auth is None:
                return False

            from ppai.calendar.domain.entities import CalendarAuth

            auth = self._calendar_service._ensure_valid_token(auth)
            decrypted_auth = CalendarAuth(
                user_id=auth.user_id,
                access_token=self._calendar_service._decrypt_token(auth.access_token),
                refresh_token=self._calendar_service._decrypt_token(auth.refresh_token),
                token_expiry=auth.token_expiry,
                calendar_connected=auth.calendar_connected,
                created_at=auth.created_at,
                updated_at=auth.updated_at,
            )

            if block.status in (BlockStatus.COMPLETED, BlockStatus.SKIPPED):
                return self._calendar_service._calendar_provider.delete_event(
                    decrypted_auth, block.calendar_event_id
                )
            else:
                title = f"{_PPAI_PREFIX} {block.task_title}"
                return self._calendar_service._calendar_provider.update_event(
                    decrypted_auth,
                    block.calendar_event_id,
                    title=title,
                )
        except Exception as exc:
            logger.warning(
                "Failed to update block in calendar",
                extra={"user_id": user_id, "block_id": block.block_id, "error": str(exc)},
            )
            return False

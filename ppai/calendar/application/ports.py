from __future__ import annotations

from typing import Protocol

from ppai.calendar.domain.entities import (
    CalendarAuth,
    CalendarEvent,
    DayPlan,
    TimeBlock,
)
from ppai.calendar.domain.value_objects import BlockStatus


class CalendarAuthRepository(Protocol):
    def get(self, user_id: str) -> CalendarAuth | None: ...

    def save(self, auth: CalendarAuth) -> None: ...

    def delete(self, user_id: str) -> None: ...


class TimeBlockRepository(Protocol):
    def save_plan(self, blocks: list[TimeBlock]) -> None: ...

    def get_plan(self, user_id: str, date: str) -> list[TimeBlock]: ...

    def update_block_status(self, block_id: str, user_id: str, date: str, status: BlockStatus) -> None: ...

    def get_block(self, block_id: str, user_id: str, date: str) -> TimeBlock | None: ...


class CalendarProvider(Protocol):
    def get_events(self, auth: CalendarAuth, date: str) -> list[CalendarEvent]: ...

    def create_event(
        self,
        auth: CalendarAuth,
        title: str,
        start: str,
        end: str,
        description: str | None = None,
        timezone_name: str = "UTC",
    ) -> str: ...

    def update_event(
        self,
        auth: CalendarAuth,
        event_id: str,
        title: str | None = None,
        start: str | None = None,
        end: str | None = None,
        description: str | None = None,
    ) -> bool: ...

    def delete_event(self, auth: CalendarAuth, event_id: str) -> bool: ...


class CalendarTelegramPort(Protocol):
    def send_plan(self, chat_id: str, plan: DayPlan) -> bool: ...

    def send_message(self, chat_id: str, text: str) -> bool: ...

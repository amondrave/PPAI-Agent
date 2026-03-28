from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ppai.calendar.domain.entities import (
    CalendarEvent,
    DayPlan,
    FreeSlot,
    TimeBlock,
)
from ppai.calendar.domain.value_objects import (
    BLOCK_BUFFER_MINUTES,
    DEFAULT_ESTIMATED_MINUTES,
    BlockStatus,
    TaskCategory,
)
from ppai.shared.domain.base_entity import generate_id

logger = logging.getLogger(__name__)

# Categories assigned within work hours
_WORK_CATEGORIES = frozenset({TaskCategory.WORK, TaskCategory.LEARNING})


class BlockPlanner:
    """Generates a DayPlan by assigning tasks to free time slots."""

    def generate_plan(
        self,
        user_id: str,
        date: str,
        tasks: list[dict],
        calendar_events: list[CalendarEvent],
        work_start: int = 9,
        work_end: int = 18,
        protected_blocks: list[tuple[datetime, datetime]] | None = None,
    ) -> DayPlan:
        """
        Generate a day plan for the given date.

        Args:
            user_id: The user identifier.
            date: Date string in YYYY-MM-DD format.
            tasks: List of task dicts with keys: task_id, title, category, estimated_minutes.
            calendar_events: Existing calendar events for the day.
            work_start: Work hours start (24h format, default 9).
            work_end: Work hours end (24h format, default 18).
            protected_blocks: Additional time ranges that cannot be scheduled.

        Returns:
            A DayPlan with assigned TimeBlocks and calendar events.
        """
        base_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        # Build occupied slots from calendar events and protected blocks
        occupied: list[tuple[datetime, datetime]] = []
        for event in calendar_events:
            if not event.is_all_day:
                occupied.append((event.start, event.end))
        if protected_blocks:
            occupied.extend(protected_blocks)

        # Define work and non-work windows
        work_window_start = base_date.replace(hour=work_start, minute=0, second=0)
        work_window_end = base_date.replace(hour=work_end, minute=0, second=0)
        day_start = base_date.replace(hour=7, minute=0, second=0)
        day_end = base_date.replace(hour=22, minute=0, second=0)

        # Calculate free slots for work and non-work hours
        work_free = self._find_free_slots(date, occupied, work_window_start, work_window_end)
        non_work_free = (
            self._find_free_slots(date, occupied, day_start, work_window_start)
            + self._find_free_slots(date, occupied, work_window_end, day_end)
        )

        blocks: list[TimeBlock] = []

        # Separate tasks with explicit time slots from regular tasks
        explicit_tasks = []
        regular_tasks = []
        for task in tasks:
            if task.get("requested_slot_start") and task.get("requested_slot_end"):
                explicit_tasks.append(task)
            else:
                regular_tasks.append(task)

        # ER5: First, assign tasks with explicit time slots
        for task in explicit_tasks:
            task_id = task.get("task_id", "")
            title = task.get("title", "")
            category = TaskCategory(task.get("category", TaskCategory.PERSONAL.value))
            slot_start_str = task["requested_slot_start"]
            slot_end_str = task["requested_slot_end"]
            try:
                sh, sm = map(int, slot_start_str.split(":"))
                eh, em = map(int, slot_end_str.split(":"))
                block_start = base_date.replace(hour=sh, minute=sm, second=0, microsecond=0)
                block_end = base_date.replace(hour=eh, minute=em, second=0, microsecond=0)
                block = TimeBlock(
                    block_id=generate_id(),
                    user_id=user_id,
                    task_id=task_id,
                    task_title=title,
                    date=date,
                    start=block_start,
                    end=block_end,
                    status=BlockStatus.PLANNED,
                    category=category,
                )
                blocks.append(block)
                # Mark this slot as occupied so regular tasks don't overlap
                occupied.append((block_start, block_end))
            except (ValueError, TypeError):
                regular_tasks.append(task)  # Fall back to regular assignment

        # Recalculate free slots after explicit assignments
        if explicit_tasks:
            work_free = self._find_free_slots(date, occupied, work_window_start, work_window_end)
            non_work_free = (
                self._find_free_slots(date, occupied, day_start, work_window_start)
                + self._find_free_slots(date, occupied, work_window_end, day_end)
            )

        # Assign regular tasks to free slots
        for task in regular_tasks:
            task_id = task.get("task_id", "")
            title = task.get("title", "")
            category = TaskCategory(task.get("category", TaskCategory.PERSONAL.value))
            estimated = task.get("estimated_minutes", DEFAULT_ESTIMATED_MINUTES)

            if category in _WORK_CATEGORIES:
                new_blocks = self._assign_task_to_slots(
                    user_id, date, task_id, title, estimated, category, work_free,
                )
            else:
                new_blocks = self._assign_task_to_slots(
                    user_id, date, task_id, title, estimated, category, non_work_free,
                )

            # Fallback: if no non-work slots, try work slots
            if not new_blocks and category not in _WORK_CATEGORIES:
                new_blocks = self._assign_task_to_slots(
                    user_id, date, task_id, title, estimated, category, work_free,
                )

            blocks.extend(new_blocks)

        return DayPlan(
            user_id=user_id,
            date=date,
            blocks=blocks,
            calendar_events=calendar_events,
        )

    def _find_free_slots(
        self,
        date: str,
        occupied: list[tuple[datetime, datetime]],
        window_start: datetime,
        window_end: datetime,
    ) -> list[FreeSlot]:
        """Find free time slots within a time window, excluding occupied ranges."""
        if window_start >= window_end:
            return []

        # Sort occupied slots by start time
        relevant = sorted(
            [(max(s, window_start), min(e, window_end)) for s, e in occupied if s < window_end and e > window_start],
            key=lambda x: x[0],
        )

        free_slots: list[FreeSlot] = []
        current = window_start

        for occ_start, occ_end in relevant:
            if current < occ_start:
                gap_minutes = int((occ_start - current).total_seconds() / 60)
                if gap_minutes >= 15:  # minimum useful slot
                    free_slots.append(FreeSlot(start=current, end=occ_start))
            current = max(current, occ_end)

        # Remaining time after last occupied slot
        if current < window_end:
            gap_minutes = int((window_end - current).total_seconds() / 60)
            if gap_minutes >= 15:
                free_slots.append(FreeSlot(start=current, end=window_end))

        return free_slots

    def _assign_task_to_slots(
        self,
        user_id: str,
        date: str,
        task_id: str,
        title: str,
        estimated_minutes: int,
        category: TaskCategory,
        free_slots: list[FreeSlot],
    ) -> list[TimeBlock]:
        """
        Assign a task to available free slots.
        Splits the task across multiple slots if needed.
        Adds BLOCK_BUFFER_MINUTES between blocks.
        """
        blocks: list[TimeBlock] = []
        remaining = estimated_minutes

        i = 0
        while remaining > 0 and i < len(free_slots):
            slot = free_slots[i]
            available = slot.duration_minutes

            if available <= 0:
                i += 1
                continue

            # Use as much of the slot as needed
            block_duration = min(remaining, available)
            block_start = slot.start
            block_end = block_start + timedelta(minutes=block_duration)

            block = TimeBlock(
                block_id=generate_id(),
                user_id=user_id,
                task_id=task_id,
                task_title=title,
                date=date,
                start=block_start,
                end=block_end,
                status=BlockStatus.PLANNED,
                category=category,
            )
            blocks.append(block)

            remaining -= block_duration

            # Update the free slot: consume used time + buffer
            buffer = timedelta(minutes=BLOCK_BUFFER_MINUTES)
            new_start = block_end + buffer
            if new_start < slot.end:
                new_duration = int((slot.end - new_start).total_seconds() / 60)
                free_slots[i] = FreeSlot(start=new_start, end=slot.end, duration_minutes=new_duration)
            else:
                # Slot fully consumed
                free_slots[i] = FreeSlot(start=slot.end, end=slot.end, duration_minutes=0)
                i += 1

        return blocks

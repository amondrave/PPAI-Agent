"""ER3 HU-R3.3 — Friction detector for stuck tasks (DIFERENCIAL)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog

from ppai.calendar.domain.entities import TimeBlock
from ppai.calendar.domain.value_objects import BlockStatus, TaskCategory
from ppai.capture.domain.value_objects import TaskStatus
from ppai.profile.application.ports import ProfileRepository
from ppai.profile.domain.value_objects import CommunicationStyle
from ppai.push.application.ports import CycleEventRepository, TelegramPushPort
from ppai.push.domain.value_objects import DispatchOutcome, NudgeDispatchStatus
from ppai.shared.domain.base_entity import generate_id

logger = structlog.get_logger(__name__)

_FRICTION_THRESHOLD_DAYS = 3


class FrictionDetector:
    """Detects stuck tasks (days_in_top3 >= 3) and offers intervention options."""

    def __init__(
        self,
        task_repo,
        block_repo,
        profile_repo: Optional[ProfileRepository],
        cycle_event_repo: CycleEventRepository,
        telegram_port: TelegramPushPort,
    ) -> None:
        self._task_repo = task_repo
        self._block_repo = block_repo
        self._profile_repo = profile_repo
        self._cycle_event_repo = cycle_event_repo
        self._telegram = telegram_port

    def evaluate_friction(
        self,
        user_id: str,
        now: datetime,
        cycle_id: str,
    ) -> Optional[DispatchOutcome]:
        """Once daily (morning), detect stuck tasks and notify."""
        # Guard: only once per day
        if self._cycle_event_repo.has_event_today(cycle_id, "FRICTION_DETECTED"):
            return None

        # Find stuck tasks: days_in_top3 >= threshold and not done
        stuck_tasks = self._find_stuck_tasks(user_id)
        if not stuck_tasks:
            return None

        profile = self._get_profile(user_id)
        style = profile.communication_style if profile else None

        # Notify about the first stuck task
        task = stuck_tasks[0]
        days = getattr(task, "days_in_top3", 0)

        if style == CommunicationStyle.GENTLE:
            text = (
                f"Noto que *{task.normalized_text}* lleva {days} dias en tu Top 3.\n"
                f"A veces las tareas grandes necesitan un enfoque diferente.\n"
                f"Que quieres hacer con ella?"
            )
        elif style == CommunicationStyle.DIRECT:
            text = (
                f"*{task.normalized_text}* lleva {days} dias sin completarse. "
                f"Opciones:"
            )
        elif style == CommunicationStyle.CONFRONTATIONAL:
            text = (
                f"*{task.normalized_text}*: {days} dias en Top 3 sin avance. "
                f"Hay que hacer algo al respecto."
            )
        else:
            text = (
                f"La tarea *{task.normalized_text}* lleva {days} dias "
                f"en tu Top 3. Quieres intentar algo diferente?"
            )

        buttons = [
            [
                {"text": "Dividir", "callback_data": f"friction_divide:{task.task_id}"},
                {"text": "Necesito info", "callback_data": f"friction_info:{task.task_id}"},
            ],
            [
                {"text": "Eliminar", "callback_data": f"friction_delete:{task.task_id}"},
                {"text": "Pomodoro 25min", "callback_data": f"friction_pomodoro:{task.task_id}"},
            ],
        ]

        sent = self._telegram.send_message_with_buttons(str(user_id), text, buttons)
        if sent:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle_id,
                event_type="FRICTION_DETECTED",
                metadata={
                    "task_id": task.task_id,
                    "days_in_top3": str(days),
                    "sent_at": now.isoformat(),
                },
            )
            logger.info(
                "friction_detector.sent",
                user_id=user_id,
                task_id=task.task_id,
                days=days,
            )
            return DispatchOutcome(
                status=NudgeDispatchStatus.sent,
                user_id=user_id,
                cycle_id=cycle_id,
                sent_at=now,
                reason="friction_detected",
            )
        return DispatchOutcome(
            status=NudgeDispatchStatus.failed,
            user_id=user_id,
            reason="friction_send_failed",
        )

    def handle_divide(
        self,
        user_id: str,
        task_id: str,
        parts_descriptions: list[str],
    ) -> list:
        """Split a stuck task into sub-tasks. Returns created sub-tasks."""
        original = self._task_repo.get_by_id(user_id, task_id)
        if original is None:
            return []

        created = []
        for desc in parts_descriptions:
            from ppai.capture.domain.entities import TaskState

            sub_task = TaskState(
                user_id=user_id,
                original_text=desc,
                normalized_text=desc,
                source_intent_id=original.source_intent_id,
                tag=original.tag,
                category=original.category,
                estimated_minutes=max(
                    (original.estimated_minutes or 30) // len(parts_descriptions), 15
                ),
                status=TaskStatus.PENDING,
            )
            self._task_repo.save(sub_task)
            created.append(sub_task)

        # Mark original as done
        original.status = TaskStatus.DONE
        original.completed_at = datetime.now(timezone.utc)
        original.updated_at = datetime.now(timezone.utc)
        original.friction_notes.append(
            f"Divided into {len(parts_descriptions)} sub-tasks"
        )
        self._task_repo.save(original)

        logger.info(
            "friction.task_divided",
            user_id=user_id,
            task_id=task_id,
            sub_count=len(created),
        )
        return created

    def handle_pomodoro(
        self,
        user_id: str,
        task_id: str,
        now: Optional[datetime] = None,
    ) -> Optional[TimeBlock]:
        """Create an immediate 25-min pomodoro block for the stuck task."""
        if now is None:
            now = datetime.now(timezone.utc)

        task = self._task_repo.get_by_id(user_id, task_id)
        if task is None:
            return None

        block = TimeBlock(
            block_id=generate_id(),
            user_id=user_id,
            task_id=task_id,
            task_title=task.normalized_text,
            date=now.strftime("%Y-%m-%d"),
            start=now,
            end=now + timedelta(minutes=25),
            status=BlockStatus.IN_PROGRESS,
            category=TaskCategory(task.category) if task.category else TaskCategory.PERSONAL,
        )
        self._block_repo.save_plan([block])

        logger.info(
            "friction.pomodoro_created",
            user_id=user_id,
            task_id=task_id,
            block_id=block.block_id,
        )
        return block

    def _find_stuck_tasks(self, user_id: str) -> list:
        """Find tasks with days_in_top3 >= threshold and not done."""
        stuck = []
        for status in (TaskStatus.PENDING, TaskStatus.PRIORITIZED, TaskStatus.NUDGED):
            try:
                tasks = self._task_repo.list_by_status(user_id, status)
            except Exception:
                continue
            for task in tasks:
                if getattr(task, "days_in_top3", 0) >= _FRICTION_THRESHOLD_DAYS:
                    stuck.append(task)
        # Sort by days_in_top3 descending
        stuck.sort(key=lambda t: getattr(t, "days_in_top3", 0), reverse=True)
        return stuck

    def _get_profile(self, user_id: str):
        if not self._profile_repo:
            return None
        try:
            return self._profile_repo.get(user_id)
        except Exception:
            return None

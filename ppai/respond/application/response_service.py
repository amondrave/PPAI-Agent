"""ResponseService — orchestrates done/snooze/clarify state transitions (US-07, US-08)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from ppai.capture.application.ports import TaskStateRepository
from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.application.decision_service import DecisionService
from ppai.decision.application.ports import CycleRepository
from ppai.push.application.ports import CycleEventRepository
from ppai.respond.application.ports import InteractionEventRepository
from ppai.respond.domain.entities import InteractionEvent, TransitionResult
from ppai.respond.domain.exceptions import InvalidTransitionError, UnauthorizedCallbackError
from ppai.respond.domain.value_objects import ResponseAction, SNOOZE_COOLDOWN

logger = logging.getLogger(__name__)


class ResponseService:
    """Handles user responses to nudges: done, snooze, clarify (BR-RSP-01..09)."""

    def __init__(
        self,
        task_repo: TaskStateRepository,
        event_repo: InteractionEventRepository,
        cycle_event_repo: CycleEventRepository,
        cycle_repo: CycleRepository,
        decision_service: DecisionService,
    ) -> None:
        self._task_repo = task_repo
        self._event_repo = event_repo
        self._cycle_event_repo = cycle_event_repo
        self._cycle_repo = cycle_repo
        self._decision_service = decision_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle_done(self, user_id: str, task_id: str) -> TransitionResult:
        """BR-RSP-01: First step — ask for confirmation."""
        task = self._get_task_or_fail(user_id, task_id)

        if not self._authorize(user_id, task):
            return self._unauthorized_result(task_id, ResponseAction.DONE)

        # BR-RSP-06: idempotency
        if task.status == TaskStatus.DONE:
            return TransitionResult(
                success=True,
                task_id=task_id,
                action=ResponseAction.DONE,
                message="Esta tarea ya fue completada.",
                previous_status=TaskStatus.DONE,
                new_status=TaskStatus.DONE,
            )

        return TransitionResult(
            success=True,
            task_id=task_id,
            action=ResponseAction.DONE,
            message="¿Confirmas que completaste esta tarea?",
            requires_confirmation=True,
            previous_status=task.status,
        )

    def confirm_done(self, user_id: str, task_id: str) -> TransitionResult:
        """BR-RSP-01: Second step — actually transition to DONE."""
        now = datetime.now(timezone.utc)
        task = self._get_task_or_fail(user_id, task_id)

        if not self._authorize(user_id, task):
            return self._unauthorized_result(task_id, ResponseAction.DONE)

        # BR-RSP-06: idempotency
        if task.status == TaskStatus.DONE:
            return TransitionResult(
                success=True,
                task_id=task_id,
                action=ResponseAction.DONE,
                message="Esta tarea ya fue completada.",
                previous_status=TaskStatus.DONE,
                new_status=TaskStatus.DONE,
            )

        previous = task.status
        try:
            task.transition_to_done(now)
        except InvalidTransitionError as exc:
            return TransitionResult(
                success=False,
                task_id=task_id,
                action=ResponseAction.DONE,
                message=str(exc),
                previous_status=previous,
            )

        self._task_repo.save(task)
        self._decision_service.invalidate_cache(user_id)

        # BR-RSP-08: record events (best-effort)
        cycle = self._get_current_cycle(user_id)
        self._record_event(
            user_id=user_id,
            task_id=task_id,
            event_type="TASK_DONE",
            correlation_id=cycle.cycle_id if cycle else "no-cycle",
            metadata={"previous_status": previous.value},
        )
        self._record_cycle_event(cycle, "TASK_DONE", {"task_id": task_id})

        return TransitionResult(
            success=True,
            task_id=task_id,
            action=ResponseAction.DONE,
            message="Tarea completada.",
            previous_status=previous,
            new_status=TaskStatus.DONE,
        )

    def handle_snooze(self, user_id: str, task_id: str) -> TransitionResult:
        """BR-RSP-02, BR-RSP-03: Snooze with cooldown and limit."""
        now = datetime.now(timezone.utc)
        task = self._get_task_or_fail(user_id, task_id)

        if not self._authorize(user_id, task):
            return self._unauthorized_result(task_id, ResponseAction.SNOOZE)

        # BR-RSP-06: idempotency
        if task.status == TaskStatus.SNOOZED:
            return TransitionResult(
                success=True,
                task_id=task_id,
                action=ResponseAction.SNOOZE,
                message="Esta tarea ya fue pospuesta.",
                previous_status=TaskStatus.SNOOZED,
                new_status=TaskStatus.SNOOZED,
            )

        previous = task.status

        # BR-RSP-03: snooze limit → auto-clarify
        if task.is_snooze_limit_reached():
            try:
                task.transition_to_needs_clarification(now)
            except InvalidTransitionError as exc:
                return TransitionResult(
                    success=False,
                    task_id=task_id,
                    action=ResponseAction.SNOOZE,
                    message=str(exc),
                    previous_status=previous,
                )
            self._task_repo.save(task)
            self._decision_service.invalidate_cache(user_id)

            cycle = self._get_current_cycle(user_id)
            self._record_event(
                user_id=user_id,
                task_id=task_id,
                event_type="TASK_CLARIFIED",
                correlation_id=cycle.cycle_id if cycle else "no-cycle",
                metadata={"reason": "snooze_limit_reached", "snooze_count": task.snooze_count},
            )
            self._record_cycle_event(cycle, "TASK_CLARIFIED", {"task_id": task_id, "reason": "snooze_limit"})

            return TransitionResult(
                success=True,
                task_id=task_id,
                action=ResponseAction.SNOOZE,
                message=f"Ya pospusiste esta tarea {task.snooze_count} veces. Necesitas aclararla o completarla.",
                previous_status=previous,
                new_status=TaskStatus.NEEDS_CLARIFICATION,
            )

        # Normal snooze
        try:
            task.transition_to_snoozed(now, SNOOZE_COOLDOWN)
        except InvalidTransitionError as exc:
            return TransitionResult(
                success=False,
                task_id=task_id,
                action=ResponseAction.SNOOZE,
                message=str(exc),
                previous_status=previous,
            )

        self._task_repo.save(task)
        self._decision_service.invalidate_cache(user_id)

        cycle = self._get_current_cycle(user_id)
        self._record_event(
            user_id=user_id,
            task_id=task_id,
            event_type="TASK_SNOOZED",
            correlation_id=cycle.cycle_id if cycle else "no-cycle",
            metadata={"snooze_count": task.snooze_count},
        )
        self._record_cycle_event(cycle, "TASK_SNOOZED", {"task_id": task_id, "snooze_count": task.snooze_count})

        return TransitionResult(
            success=True,
            task_id=task_id,
            action=ResponseAction.SNOOZE,
            message=f"Tarea pospuesta ({task.snooze_count}/3). Volverá en 1 hora.",
            previous_status=previous,
            new_status=TaskStatus.SNOOZED,
        )

    def handle_clarify(self, user_id: str, task_id: str) -> TransitionResult:
        """BR-RSP-04: Initiate clarification flow."""
        now = datetime.now(timezone.utc)
        task = self._get_task_or_fail(user_id, task_id)

        if not self._authorize(user_id, task):
            return self._unauthorized_result(task_id, ResponseAction.CLARIFY)

        # BR-RSP-06: idempotency
        if task.status == TaskStatus.NEEDS_CLARIFICATION:
            return TransitionResult(
                success=True,
                task_id=task_id,
                action=ResponseAction.CLARIFY,
                message="Esta tarea espera aclaración.",
                previous_status=TaskStatus.NEEDS_CLARIFICATION,
                new_status=TaskStatus.NEEDS_CLARIFICATION,
            )

        previous = task.status
        try:
            task.transition_to_needs_clarification(now)
        except InvalidTransitionError as exc:
            return TransitionResult(
                success=False,
                task_id=task_id,
                action=ResponseAction.CLARIFY,
                message=str(exc),
                previous_status=previous,
            )

        self._task_repo.save(task)
        self._decision_service.invalidate_cache(user_id)

        cycle = self._get_current_cycle(user_id)
        self._record_event(
            user_id=user_id,
            task_id=task_id,
            event_type="TASK_CLARIFIED",
            correlation_id=cycle.cycle_id if cycle else "no-cycle",
        )
        self._record_cycle_event(cycle, "TASK_CLARIFIED", {"task_id": task_id})

        return TransitionResult(
            success=True,
            task_id=task_id,
            action=ResponseAction.CLARIFY,
            message="¿Qué necesitas para avanzar con esta tarea?",
            previous_status=previous,
            new_status=TaskStatus.NEEDS_CLARIFICATION,
        )

    def handle_clarify_response(self, user_id: str, text: str) -> TransitionResult | None:
        """BR-RSP-05: Process free-text clarification response.

        Returns None if no task is awaiting clarification for this user.
        """
        now = datetime.now(timezone.utc)
        task = self._find_task_needing_clarification(user_id)
        if task is None:
            return None

        previous = task.status
        enriched = f"{task.normalized_text} | Aclarado: {text}"
        task.resolve_clarification(enriched, now)
        self._task_repo.save(task)
        self._decision_service.invalidate_cache(user_id)

        cycle = self._get_current_cycle(user_id)
        self._record_event(
            user_id=user_id,
            task_id=task.task_id,
            event_type="TASK_CLARIFY_RESOLVED",
            correlation_id=cycle.cycle_id if cycle else "no-cycle",
            metadata={"response_text": text},
        )
        self._record_cycle_event(cycle, "TASK_CLARIFY_RESOLVED", {"task_id": task.task_id})

        return TransitionResult(
            success=True,
            task_id=task.task_id,
            action=ResponseAction.CLARIFY,
            message="Aclaración recibida. La tarea vuelve a estar disponible.",
            previous_status=previous,
            new_status=TaskStatus.PENDING,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_task_or_fail(self, user_id: str, task_id: str) -> TaskState:
        task = self._task_repo.get_by_id(user_id, task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found for user {user_id}")
        return task

    def _authorize(self, callback_user_id: str, task: TaskState) -> bool:
        """BR-RSP-07: Validate callback user matches task owner."""
        if callback_user_id != task.user_id:
            logger.warning(
                "callback.unauthorized",
                extra={"callback_user_id": callback_user_id, "task_user_id": task.user_id},
            )
            return False
        return True

    def _unauthorized_result(self, task_id: str, action: ResponseAction) -> TransitionResult:
        return TransitionResult(
            success=False,
            task_id=task_id,
            action=action,
            message="No tienes permiso para esta acción.",
        )

    def _find_task_needing_clarification(self, user_id: str) -> TaskState | None:
        """BR-RSP-05: Find the most recently updated task in NEEDS_CLARIFICATION."""
        # This queries via the status index — reuses existing repo pattern
        tasks = self._task_repo.list_by_status(user_id, TaskStatus.NEEDS_CLARIFICATION)
        if not tasks:
            return None
        # Most recent by updated_at
        return max(tasks, key=lambda t: t.updated_at)

    def _get_current_cycle(self, user_id: str):
        """Get the active cycle for today, or None."""
        from datetime import date
        today = date.today().isoformat()
        try:
            return self._cycle_repo.get_active(user_id, today)
        except Exception:
            logger.warning("respond.cycle_lookup_failed", extra={"user_id": user_id}, exc_info=True)
            return None

    def _record_event(self, *, user_id: str, task_id: str, event_type: str,
                      correlation_id: str, metadata: dict | None = None) -> None:
        """BR-RSP-08, BR-RSP-09: Best-effort event recording."""
        try:
            event = InteractionEvent(
                user_id=user_id,
                task_id=task_id,
                event_type=event_type,
                correlation_id=correlation_id,
                metadata=metadata or {},
            )
            self._event_repo.append(event)
        except Exception:
            logger.warning(
                "respond.event_record_failed",
                extra={"user_id": user_id, "task_id": task_id, "event_type": event_type},
                exc_info=True,
            )

    def _record_cycle_event(self, cycle, event_type: str, metadata: dict) -> None:
        """Best-effort cycle event recording in ppai-cycles."""
        if cycle is None:
            return
        try:
            self._cycle_event_repo.record_nudge_event(cycle.cycle_id, event_type, metadata)
        except Exception:
            logger.warning(
                "respond.cycle_event_failed",
                extra={"cycle_id": cycle.cycle_id, "event_type": event_type},
                exc_info=True,
            )

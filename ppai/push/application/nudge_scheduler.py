from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable

import structlog

logger = structlog.get_logger(__name__)


class NudgeScheduler:
    """
    In-process scheduler that fires NudgeService.run_tick every tick_interval_minutes.
    Runs in a background thread inside the same ECS container as the bot (DP-PUSH-01).
    Fail-soft: exceptions in a tick are logged but never propagate (DP-PUSH-06).
    """

    _MIN_INTERVAL_MINUTES = 5  # Floor for dynamic interval (DP-SCHED-01)

    def __init__(
        self,
        nudge_service,
        user_ids_provider: Callable[[], list[str]],
        tick_interval_minutes: int = 15,
        interval_provider: Callable[[], int] | None = None,
    ) -> None:
        self._service = nudge_service
        self._user_ids_provider = user_ids_provider
        self._base_interval_minutes = tick_interval_minutes
        self._interval_seconds = tick_interval_minutes * 60
        self._interval_provider = interval_provider
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the scheduler in a daemon background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="nudge-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("nudge_scheduler.started", interval_seconds=self._interval_seconds)

    def stop(self) -> None:
        """Signal the scheduler to stop and wait for the thread to exit."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("nudge_scheduler.stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self._tick()
            self._recalculate_interval()
            self._stop_event.wait(timeout=self._interval_seconds)

    def _tick(self) -> None:
        """Execute one scheduler tick. Exceptions are caught and logged (fail-soft)."""
        try:
            user_ids = self._user_ids_provider()
            if not user_ids:
                return
            now = datetime.now(timezone.utc)
            outcomes = self._service.run_tick(user_ids, now=now)
            for outcome in outcomes:
                if outcome.status == "sent":
                    logger.info(
                        "nudge_scheduler.tick_sent",
                        user_id=outcome.user_id,
                        task_id=outcome.task_id,
                    )
                elif outcome.status == "failed":
                    logger.error(
                        "nudge_scheduler.tick_failed",
                        user_id=outcome.user_id,
                        reason=outcome.reason,
                    )
        except Exception as exc:
            logger.error("nudge_scheduler.tick_error", error=str(exc))

    def _recalculate_interval(self) -> None:
        """Recalculate tick interval from provider, with floor (DP-SCHED-01)."""
        if self._interval_provider is None:
            return
        try:
            dynamic = self._interval_provider()
            if dynamic is not None:
                minutes = max(dynamic, self._MIN_INTERVAL_MINUTES)
            else:
                minutes = self._base_interval_minutes
            self._interval_seconds = minutes * 60
        except Exception:
            pass  # Keep current interval on error

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog

from ppai.capture.domain.value_objects import TaskStatus
from ppai.decision.application.decision_service import DecisionService
from ppai.decision.domain.entities import ExecutionCycle, Top3Result
from ppai.push.application.ports import CycleEventRepository, PreferencesRepository, TelegramPushPort
from ppai.push.domain.entities import NudgeMessage, UserNudgePreferences
from ppai.push.domain.exceptions import NudgeDispatchFailedError, NoTop3AvailableError
from ppai.push.domain.value_objects import DispatchOutcome, NudgeDispatchStatus

logger = structlog.get_logger(__name__)

_DEFAULT_NUDGE_HOUR = 9        # 09:00 local time
_ACTIVITY_SILENCE_MINUTES = 60
_REENGAGEMENT_HOURS = 24
_MAX_RETRY_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 30

# Tone guardrail — prohibited phrases (BR-PUSH-10)
_PROHIBITED_PHRASES = (
    "debías", "ya vas tarde", "otra vez", "no hiciste",
    "deberías", "fallaste", "no avanzaste",
)

# Motivational templates for nudge messages (BR-PUSH-09, BR-PUSH-10)
_NUDGE_TEMPLATES = (
    "Tu siguiente paso podría ser: {title}",
    "Si te sirve, puedes retomar por aquí: {title}",
    "{title} — esto va primero hoy.",
)
_REENGAGEMENT_TEMPLATE = "Cuando estés listo, puedes retomar con: {title}"


class NudgeService:
    """
    Evaluates nudge dispatch for each user on each scheduler tick.
    Implements BR-PUSH-02..15 and DP-PUSH-02..08.
    """

    def __init__(
        self,
        prefs_repo: PreferencesRepository,
        cycle_event_repo: CycleEventRepository,
        task_repo,  # capture TaskStateRepository
        telegram_port: TelegramPushPort,
        decision_service: DecisionService,
    ) -> None:
        self._prefs_repo = prefs_repo
        self._cycle_event_repo = cycle_event_repo
        self._task_repo = task_repo
        self._telegram = telegram_port
        self._decision = decision_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_tick(
        self,
        user_ids: list[str],
        now: Optional[datetime] = None,
    ) -> list[DispatchOutcome]:
        """Evaluate all users for a scheduler tick. Returns one outcome per user."""
        if now is None:
            now = datetime.now(timezone.utc)
        outcomes = []
        for user_id in user_ids:
            try:
                outcome = self._evaluate_user(user_id, now)
            except Exception as exc:
                logger.error("nudge.tick_error", user_id=user_id, error=str(exc))
                outcome = DispatchOutcome(
                    status=NudgeDispatchStatus.failed,
                    user_id=user_id,
                    reason=str(exc),
                )
            outcomes.append(outcome)
        return outcomes

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    def _evaluate_user(self, user_id: str, now: datetime) -> DispatchOutcome:
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        local_now = self._to_local(now, prefs.timezone)

        # BR-PUSH-08 — silence window
        if self._is_silence_window(local_now, prefs):
            logger.info("nudge.skipped_silence", user_id=user_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.skipped_activity,
                user_id=user_id,
                reason="silence_window_active",
            )

        # BR-PUSH-06 — recent activity guard
        last_activity = self._cycle_event_repo.get_last_activity_at(user_id)
        if last_activity and (now - last_activity) < timedelta(minutes=_ACTIVITY_SILENCE_MINUTES):
            logger.info("nudge.skipped_activity", user_id=user_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.skipped_activity,
                user_id=user_id,
                reason="recent_activity",
            )

        # BR-PUSH-15 — re-engagement check
        is_reengagement = self._check_re_engagement(user_id, now, last_activity)

        # Resolve Top 3 — BR-PUSH-04, BR-PUSH-05
        try:
            top3 = self._decision.get_top3(user_id, now=now)
        except Exception:
            top3 = None

        if top3 is None or top3.is_empty():
            logger.info("nudge.skipped_no_top3", user_id=user_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.skipped_no_top3,
                user_id=user_id,
                reason="no_top3_available",
            )

        task_id = top3.ranked_scores[0].task_id

        # Resolve / create ExecutionCycle — BR-PUSH-02
        today_str = local_now.strftime("%Y-%m-%d")
        cycle = self._cycle_event_repo.get_active(user_id, local_now.date())
        if cycle is None:
            cycle = ExecutionCycle(user_id=user_id, date=today_str)
            self._cycle_event_repo.create(cycle)

        # BR-PUSH-07 — daily cap
        nudge_count = self._cycle_event_repo.get_nudge_count(cycle.cycle_id)
        if nudge_count >= prefs.max_nudges_per_day:
            logger.info("nudge.skipped_daily_cap", user_id=user_id, count=nudge_count)
            return DispatchOutcome(
                status=NudgeDispatchStatus.skipped_activity,
                user_id=user_id,
                reason="daily_cap_reached",
            )

        # Build nudge message — BR-PUSH-09, BR-PUSH-10
        task = self._task_repo.get_by_id(user_id, task_id)
        nudge_msg = self._build_nudge_message(task, prefs, is_reengagement)

        # DP-PUSH-02 — persist NUDGE_SCHEDULED before sending
        self._cycle_event_repo.record_nudge_event(
            cycle_id=cycle.cycle_id,
            event_type="NUDGE_SCHEDULED",
            metadata={"task_id": task_id, "window_start": now.isoformat()},
        )

        # Dispatch with retry — BR-PUSH-11, DP-PUSH-05
        chat_id = str(user_id)
        sent = self._send_with_retry(nudge_msg, chat_id)

        if sent:
            # BR-PUSH-13 — transition task to nudged
            task.status = TaskStatus.NUDGED
            self._task_repo.save(task)

            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle.cycle_id,
                event_type="NUDGE_SENT",
                metadata={"task_id": task_id, "sent_at": datetime.now(timezone.utc).isoformat()},
            )
            logger.info("nudge.sent", user_id=user_id, task_id=task_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.sent,
                user_id=user_id,
                task_id=task_id,
                cycle_id=cycle.cycle_id,
                sent_at=datetime.now(timezone.utc),
            )
        else:
            # BR-PUSH-12 — persist final failure
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle.cycle_id,
                event_type="NUDGE_FAILED",
                metadata={
                    "task_id": task_id,
                    "attempt_count": _MAX_RETRY_ATTEMPTS,
                    "reason": "telegram_dispatch_failed",
                },
            )
            logger.error("nudge.failed", user_id=user_id, task_id=task_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.failed,
                user_id=user_id,
                task_id=task_id,
                cycle_id=cycle.cycle_id,
                reason="telegram_dispatch_failed",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _send_with_retry(self, message: NudgeMessage, chat_id: str) -> bool:
        """Attempt to send up to _MAX_RETRY_ATTEMPTS times with fixed backoff (DP-PUSH-05)."""
        import time
        for attempt in range(_MAX_RETRY_ATTEMPTS):
            try:
                if self._telegram.send_nudge(chat_id, message):
                    return True
            except Exception as exc:
                logger.warning("nudge.send_attempt_failed", attempt=attempt + 1, error=str(exc))
            if attempt < _MAX_RETRY_ATTEMPTS - 1:
                time.sleep(_RETRY_DELAY_SECONDS)
        return False

    def _build_nudge_message(
        self,
        task,
        prefs: UserNudgePreferences,
        is_reengagement: bool = False,
    ) -> NudgeMessage:
        """Build nudge message with soft motivational tone (BR-PUSH-09, BR-PUSH-10)."""
        title = task.normalized_text
        if is_reengagement:
            text = _REENGAGEMENT_TEMPLATE.format(title=title)
        else:
            text = _NUDGE_TEMPLATES[0].format(title=title)

        # Guardrail check
        lower = text.lower()
        for phrase in _PROHIBITED_PHRASES:
            if phrase in lower:
                text = _NUDGE_TEMPLATES[1].format(title=title)
                break

        # Deadline-based reason
        if task.deadline:
            reason = f"Va primero porque vence el {task.deadline}"
        else:
            reason = "Es la tarea con mayor prioridad ahora"

        return NudgeMessage(
            task_id=task.task_id,
            task_title=text,
            priority_reason=reason,
        )

    def _check_re_engagement(
        self,
        user_id: str,
        now: datetime,
        last_activity: Optional[datetime],
    ) -> bool:
        """Return True if user has been inactive for more than 24h (BR-PUSH-15)."""
        if last_activity is None:
            return False
        return (now - last_activity) > timedelta(hours=_REENGAGEMENT_HOURS)

    def _is_silence_window(self, local_now: datetime, prefs: UserNudgePreferences) -> bool:
        """Check if current local time falls within user's silence window (BR-PUSH-08, DP-PUSH-04)."""
        if not prefs.has_silence_window():
            return False

        current = local_now.time()
        from datetime import time as dtime

        start = dtime.fromisoformat(prefs.silence_start)
        end = dtime.fromisoformat(prefs.silence_end)

        if start <= end:
            # Normal window (e.g., 09:00 - 12:00)
            return start <= current <= end
        else:
            # Cross-midnight window (e.g., 22:00 - 07:00)
            return current >= start or current <= end

    def _to_local(self, utc_dt: datetime, tz_name: str) -> datetime:
        """Convert UTC datetime to user's local timezone."""
        try:
            tz = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, Exception):
            tz = ZoneInfo("America/Bogota")
        return utc_dt.astimezone(tz)

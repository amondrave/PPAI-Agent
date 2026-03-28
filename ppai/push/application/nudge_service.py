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
from ppai.profile.application.ports import ProfileRepository
from ppai.profile.domain.value_objects import CommunicationStyle
from ppai.push.application.ports import CycleEventRepository, PreferencesRepository, TelegramPushPort
from ppai.push.application.daily_summary_builder import DailySummaryBuilder
from ppai.push.application.rescue_evaluator import RescueEvaluator
from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.application.block_reminder_service import BlockReminderService
from ppai.push.application.gap_detector import GapDetector
from ppai.push.application.friction_detector import FrictionDetector
from ppai.push.application.weekly_reporter import WeeklyReporter
from ppai.push.application.midday_checkin import MiddayCheckin
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
        zen_manager: Optional[ZenSessionManager] = None,
        daily_summary_builder: Optional[DailySummaryBuilder] = None,
        rescue_evaluator: Optional[RescueEvaluator] = None,
        profile_repo: Optional[ProfileRepository] = None,
        # ER3: Proactive intelligent notifications
        block_reminder_service: Optional[BlockReminderService] = None,
        gap_detector: Optional[GapDetector] = None,
        friction_detector: Optional[FrictionDetector] = None,
        weekly_reporter: Optional[WeeklyReporter] = None,
        midday_checkin: Optional[MiddayCheckin] = None,
        # ER4: LLM message composer
        message_composer=None,
    ) -> None:
        self._prefs_repo = prefs_repo
        self._cycle_event_repo = cycle_event_repo
        self._task_repo = task_repo
        self._telegram = telegram_port
        self._decision = decision_service
        # UOW-05
        self._zen_manager = zen_manager
        self._summary_builder = daily_summary_builder
        self._rescue_evaluator = rescue_evaluator
        # ER1: Profile-aware tone
        self._profile_repo = profile_repo
        # ER3: Proactive intelligent notifications
        self._block_reminder_service = block_reminder_service
        self._gap_detector = gap_detector
        self._friction_detector = friction_detector
        self._weekly_reporter = weekly_reporter
        self._midday_checkin = midday_checkin
        # ER4: LLM message composer
        self._message_composer = message_composer

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_tick(
        self,
        user_ids: list[str],
        now: Optional[datetime] = None,
    ) -> list[DispatchOutcome]:
        """Evaluate all users for a scheduler tick. Returns outcomes per user."""
        if now is None:
            now = datetime.now(timezone.utc)
        outcomes: list[DispatchOutcome] = []
        for user_id in user_ids:
            try:
                user_outcomes = self._evaluate_user_uow05(user_id, now)
                outcomes.extend(user_outcomes)
            except Exception as exc:
                logger.error("nudge.tick_error", user_id=user_id, error=str(exc))
                outcomes.append(DispatchOutcome(
                    status=NudgeDispatchStatus.failed,
                    user_id=user_id,
                    reason=str(exc),
                ))
        return outcomes

    # ------------------------------------------------------------------
    # UOW-05: Extended evaluation (daily start/end + zen + rescue)
    # ------------------------------------------------------------------

    def _evaluate_user_uow05(self, user_id: str, now: datetime) -> list[DispatchOutcome]:
        """Evaluate daily start, daily end, zen nudges for a user. Returns multiple outcomes."""
        results: list[DispatchOutcome] = []
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        local_now = self._to_local(now, prefs.timezone)

        # Ensure cycle exists
        today_str = local_now.strftime("%Y-%m-%d")
        cycle = self._cycle_event_repo.get_active(user_id, local_now.date())
        if cycle is None:
            from ppai.decision.domain.entities import ExecutionCycle
            cycle = ExecutionCycle(user_id=user_id, date=today_str)
            self._cycle_event_repo.create(cycle)

        # 1. Evaluate daily start reminder
        if prefs.is_within_start_window(local_now):
            outcome = self._evaluate_daily_start(user_id, prefs, now, local_now, cycle)
            if outcome:
                results.append(outcome)

        # 2. Evaluate daily end summary + rescue
        if prefs.is_within_end_window(local_now):
            outcome = self._evaluate_daily_end(user_id, prefs, now, local_now, cycle)
            if outcome:
                results.append(outcome)

        # 3. Zen or regular nudges
        if prefs.zen_active and self._zen_manager:
            outcome = self._evaluate_zen_nudge(user_id, prefs, now, local_now, cycle)
            if outcome:
                results.append(outcome)
        # If zen not active, no regular nudges either (BR-SCHED-13)

        # ------------------------------------------------------------------
        # ER3: Proactive intelligent notifications
        # ------------------------------------------------------------------

        # 4. Block reminders (every tick when blocks active)
        if self._block_reminder_service:
            try:
                block_outcomes = self._block_reminder_service.evaluate_block_reminders(
                    user_id, local_now, cycle.cycle_id,
                )
                results.extend(block_outcomes)
            except Exception as exc:
                logger.error("er3.block_reminder_error", user_id=user_id, error=str(exc))

        # 5. Gap detection (every 15 min if calendar connected)
        if self._gap_detector:
            try:
                gap_outcome = self._gap_detector.evaluate_gaps(
                    user_id, local_now, cycle.cycle_id,
                )
                if gap_outcome:
                    results.append(gap_outcome)
            except Exception as exc:
                logger.error("er3.gap_detector_error", user_id=user_id, error=str(exc))

        # 6. Friction detection (once daily, morning)
        if self._friction_detector and prefs.is_within_start_window(local_now):
            try:
                friction_outcome = self._friction_detector.evaluate_friction(
                    user_id, local_now, cycle.cycle_id,
                )
                if friction_outcome:
                    results.append(friction_outcome)
            except Exception as exc:
                logger.error("er3.friction_detector_error", user_id=user_id, error=str(exc))

        # 7. Weekly report (Sunday evening / Monday morning)
        if self._weekly_reporter:
            try:
                if self._weekly_reporter.should_send_report(
                    user_id, local_now, prefs, cycle.cycle_id,
                ):
                    report_outcome = self._weekly_reporter.generate_and_send_report(
                        user_id, local_now, cycle.cycle_id,
                    )
                    if report_outcome:
                        results.append(report_outcome)
            except Exception as exc:
                logger.error("er3.weekly_reporter_error", user_id=user_id, error=str(exc))

        # 8. Midday check-in (once daily, midpoint of workday)
        if self._midday_checkin:
            try:
                midday_outcome = self._midday_checkin.evaluate_midday(
                    user_id, local_now, cycle.cycle_id, prefs,
                )
                if midday_outcome:
                    results.append(midday_outcome)
            except Exception as exc:
                logger.error("er3.midday_checkin_error", user_id=user_id, error=str(exc))

        return results

    def _evaluate_daily_start(
        self, user_id, prefs, now, local_now, cycle,
    ) -> Optional[DispatchOutcome]:
        """Send morning Top 3 reminder if not already sent today (DP-SCHED-02)."""
        if self._cycle_event_repo.has_event_today(cycle.cycle_id, "DAILY_START_SENT"):
            return None

        try:
            top3 = self._decision.get_top3(user_id, now=now)
        except Exception:
            top3 = None

        text = self._build_start_message(top3, prefs.motivational_message, user_id=user_id)
        chat_id = str(user_id)
        sent = self._telegram.send_message(chat_id, text)

        if sent:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle.cycle_id,
                event_type="DAILY_START_SENT",
                metadata={"sent_at": now.isoformat()},
            )
            logger.info("daily_start.sent", user_id=user_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.sent,
                user_id=user_id,
                cycle_id=cycle.cycle_id,
                sent_at=now,
                reason="daily_start",
            )
        return DispatchOutcome(
            status=NudgeDispatchStatus.failed,
            user_id=user_id,
            reason="daily_start_send_failed",
        )

    def _evaluate_daily_end(
        self, user_id, prefs, now, local_now, cycle,
    ) -> Optional[DispatchOutcome]:
        """Send end-of-day summary with optional rescue (DP-SCHED-02, BR-SCHED-06)."""
        if self._cycle_event_repo.has_event_today(cycle.cycle_id, "DAILY_END_SENT"):
            return None

        summary = None
        if self._summary_builder:
            summary = self._summary_builder.build(user_id, local_now.date())

        rescue = None
        if summary and self._rescue_evaluator:
            try:
                top3 = self._decision.get_top3(user_id, now=now)
                top3_tasks = top3.ranked_scores if top3 and not top3.is_empty() else []
            except Exception:
                top3_tasks = []

            # Fetch full task objects for rescue evaluator
            full_tasks = []
            for score in top3_tasks:
                task = self._task_repo.get_by_id(user_id, score.task_id)
                if task:
                    full_tasks.append(task)

            rescue = self._rescue_evaluator.evaluate(summary, top3=full_tasks)
            if rescue:
                summary.rescue_triggered = True
                summary.rescue_suggestion = rescue
                if not self._cycle_event_repo.has_event_today(cycle.cycle_id, "RESCUE_TRIGGERED"):
                    self._cycle_event_repo.record_nudge_event(
                        cycle_id=cycle.cycle_id,
                        event_type="RESCUE_TRIGGERED",
                        metadata={"task_id": rescue.key_task.task_id, "micro_action": rescue.micro_action},
                    )

        text = self._build_end_message(summary, user_id=user_id)
        chat_id = str(user_id)
        sent = self._telegram.send_message(chat_id, text)

        if sent:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle.cycle_id,
                event_type="DAILY_END_SENT",
                metadata={"sent_at": now.isoformat(), "rescue_triggered": bool(rescue)},
            )
            logger.info("daily_end.sent", user_id=user_id, rescue=bool(rescue))
            return DispatchOutcome(
                status=NudgeDispatchStatus.sent,
                user_id=user_id,
                cycle_id=cycle.cycle_id,
                sent_at=now,
                reason="daily_end",
            )
        return DispatchOutcome(
            status=NudgeDispatchStatus.failed,
            user_id=user_id,
            reason="daily_end_send_failed",
        )

    def _evaluate_zen_nudge(
        self, user_id, prefs, now, local_now, cycle,
    ) -> Optional[DispatchOutcome]:
        """Send zen nudge if interval elapsed and cap not reached (DP-SCHED-04, BR-SCHED-11)."""
        if not self._zen_manager:
            return None

        session = self._zen_manager.get(user_id)
        if session is None:
            return None

        if session.has_reached_cap:
            # Auto-deactivate (BR-SCHED-10)
            prefs.zen_active = False
            self._prefs_repo.save(prefs)
            deactivated = self._zen_manager.deactivate(user_id)
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle.cycle_id,
                event_type="ZEN_DEACTIVATED",
                metadata={"nudges_sent": deactivated.nudges_sent if deactivated else 0, "reason": "auto_cap"},
            )
            text = f"Modo zen completado. Alcanzaste el máximo de {session.max_nudges} nudges."
            self._telegram.send_message(str(user_id), text)
            logger.info("zen.auto_deactivated", user_id=user_id, nudges_sent=session.nudges_sent)
            return None

        # BR-SCHED-12: zen overrides silence — skip silence check
        # Proceed with regular nudge logic but skip silence window
        return self._evaluate_user(user_id, now, skip_silence=True)

    # ------------------------------------------------------------------
    # UOW-05: Message builders
    # ------------------------------------------------------------------

    def _build_start_message(self, top3, motivational_message: str, user_id: str | None = None) -> str:
        """Build morning reminder message (BR-SCHED-04, BR-SCHED-18). Tries LLM first (ER4)."""
        profile = self._get_user_profile(user_id) if user_id else None
        name = profile.name if profile else ""
        style = profile.communication_style if profile else None

        # ER4: Try LLM-generated message
        if self._message_composer and profile:
            try:
                from ppai.intelligence.domain.entities import MessageRequest
                tasks = []
                if top3 and not top3.is_empty():
                    for score in top3.ranked_scores[:3]:
                        task = self._task_repo.get_by_id(top3.user_id, score.task_id)
                        if task:
                            tasks.append(task.normalized_text)
                request = MessageRequest(
                    user_name=name,
                    communication_style=style.value if style else "gentle",
                    occupation=profile.occupation or "",
                    top3_tasks=tasks,
                )
                llm_text = self._message_composer.compose_daily_start(request)
                if llm_text:
                    return llm_text
            except Exception:
                logger.warning("er4.start_message_llm_failed", extra={"user_id": user_id})

        # Fallback: static templates
        if style == CommunicationStyle.GENTLE:
            header = f"Buenos días {name}, hoy tienes un gran día por delante!\n"
        elif style == CommunicationStyle.DIRECT:
            header = f"{name}, tu plan de hoy:\n"
        elif style == CommunicationStyle.CONFRONTATIONAL:
            header = f"{name}, no hay tiempo que perder. Tu agenda de hoy:\n"
        else:
            # Fallback: neutral tone (no profile)
            header = f"Buenos días! {motivational_message}\n"

        if top3 is None or top3.is_empty():
            if style == CommunicationStyle.GENTLE:
                return header + "\nNo tienes tareas pendientes por ahora. Puedes capturar nuevas con un mensaje de texto."
            elif style == CommunicationStyle.DIRECT:
                return header + "\nSin tareas pendientes. Captura nuevas cuando quieras."
            elif style == CommunicationStyle.CONFRONTATIONAL:
                return header + "\nLista vacía. Captura algo para que este día cuente."
            return header + "\nNo tienes tareas pendientes por ahora. Puedes capturar nuevas con un mensaje de texto."

        lines = [header, "\nTu Top 3 para hoy:"]
        for i, score in enumerate(top3.ranked_scores[:3], 1):
            task = self._task_repo.get_by_id(top3.user_id, score.task_id)
            title = task.normalized_text if task else score.task_id
            lines.append(f"{i}. {title}")
        return "\n".join(lines)

    def _build_end_message(self, summary, user_id: str | None = None) -> str:
        """Build end-of-day summary message (BR-SCHED-05, BR-SCHED-19). Tries LLM first (ER4)."""
        profile = self._get_user_profile(user_id) if user_id else None
        name = profile.name if profile else ""
        style = profile.communication_style if profile else None

        # ER4: Try LLM-generated message
        if self._message_composer and profile and summary:
            try:
                from ppai.intelligence.domain.entities import MessageRequest
                request = MessageRequest(
                    user_name=name,
                    communication_style=style.value if style else "gentle",
                    occupation=profile.occupation or "",
                    completed_today=len(summary.completed_tasks),
                    pending_today=len(summary.pending_tasks),
                    snoozed_today=len(summary.snoozed_tasks),
                )
                llm_text = self._message_composer.compose_daily_end(request)
                if llm_text:
                    # Append rescue section if triggered (still static — critical flow)
                    if summary.rescue_triggered and summary.rescue_suggestion:
                        r = summary.rescue_suggestion
                        llm_text += f"\n\nRescate sugerido: {r.key_task.title}\n  - {r.micro_action}"
                    return llm_text
            except Exception:
                logger.warning("er4.end_message_llm_failed", extra={"user_id": user_id})

        # Fallback: static templates
        if summary is None:
            return "Resumen del día:\n\nNo hay datos disponibles."

        if style == CommunicationStyle.GENTLE:
            parts = [f"Buen trabajo hoy, {name}!\n"]
        elif style == CommunicationStyle.DIRECT:
            parts = [f"Resumen del día, {name}:\n"]
        elif style == CommunicationStyle.CONFRONTATIONAL:
            parts = [f"{name}, asi quedo tu dia:\n"]
        else:
            parts = ["Resumen del día:\n"]

        if summary.completed_tasks:
            parts.append(f"Completadas ({len(summary.completed_tasks)}):")
            for t in summary.completed_tasks:
                parts.append(f"  ✓ {t.title}")
        else:
            parts.append("Completadas (0)")

        if summary.pending_tasks:
            parts.append(f"\nPendientes ({len(summary.pending_tasks)}):")
            for t in summary.pending_tasks:
                parts.append(f"  • {t.title}")

        if summary.snoozed_tasks:
            parts.append(f"\nPospuestas ({len(summary.snoozed_tasks)}):")
            for t in summary.snoozed_tasks:
                parts.append(f"  ⏸ {t.title}")

        # Rescue section (BR-SCHED-20)
        if summary.rescue_triggered and summary.rescue_suggestion:
            r = summary.rescue_suggestion
            if style == CommunicationStyle.GENTLE:
                parts.append("\nHoy fue un día difícil, y eso está bien.")
                parts.append(f"\nSi quieres retomar con algo pequeño:")
                parts.append(f"  • {r.key_task.title}")
                parts.append(f"  • {r.micro_action}")
                parts.append("\nSin presión — mañana es otro día.")
            elif style == CommunicationStyle.DIRECT:
                parts.append(f"\nRescate sugerido: {r.key_task.title}")
                parts.append(f"  • {r.micro_action}")
            elif style == CommunicationStyle.CONFRONTATIONAL:
                parts.append(f"\nNo completaste nada hoy. Mínimo haz esto:")
                parts.append(f"  • {r.key_task.title}")
                parts.append(f"  • {r.micro_action}")
            else:
                parts.append("\nHoy fue un día difícil, y eso está bien.")
                parts.append(f"\nSi quieres retomar con algo pequeño:")
                parts.append(f"  • {r.key_task.title}")
                parts.append(f"  • {r.micro_action}")
                parts.append("\nSin presión — mañana es otro día.")
        else:
            if style == CommunicationStyle.GENTLE:
                parts.append("\n¡Descansa bien! Mañana seguimos.")
            elif style == CommunicationStyle.DIRECT:
                parts.append("\nDía cerrado.")
            elif style == CommunicationStyle.CONFRONTATIONAL:
                parts.append("\nBien. Mañana hay que dar más.")
            else:
                parts.append("\nDescansa bien!")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Core evaluation (original UOW-03 — used by zen nudges)
    # ------------------------------------------------------------------

    def _evaluate_user(self, user_id: str, now: datetime, skip_silence: bool = False) -> DispatchOutcome:
        prefs = self._prefs_repo.get(user_id) or UserNudgePreferences(user_id=user_id)
        local_now = self._to_local(now, prefs.timezone)

        # BR-PUSH-08 — silence window (skipped for zen override, BR-SCHED-12)
        if not skip_silence and self._is_silence_window(local_now, prefs):
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
        nudge_msg = self._build_nudge_message(task, prefs, is_reengagement, user_id=user_id)

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
        user_id: str | None = None,
    ) -> NudgeMessage:
        """Build nudge message with tone adapted to profile (BR-PUSH-09, BR-PUSH-10). Tries LLM (ER4)."""
        title = task.normalized_text
        profile = self._get_user_profile(user_id) if user_id else None
        style = profile.communication_style if profile else None
        name = profile.name if profile else ""

        # ER4: Try LLM nudge
        if self._message_composer and profile and not is_reengagement:
            try:
                llm_text = self._message_composer.compose_nudge(
                    user_name=name,
                    style=style.value if style else "gentle",
                    task_title=title,
                )
                if llm_text:
                    reason = f"Va primero porque vence el {task.deadline}" if task.deadline else "Es la tarea con mayor prioridad ahora"
                    return NudgeMessage(task_id=task.task_id, task_title=llm_text, priority_reason=reason)
            except Exception:
                logger.warning("er4.nudge_llm_failed", extra={"user_id": user_id})

        # Fallback: static templates
        if is_reengagement:
            if style == CommunicationStyle.GENTLE:
                text = f"{name}, cuando estes listo, puedes retomar con: {title}"
            elif style == CommunicationStyle.DIRECT:
                text = f"{name}, retoma: {title}"
            elif style == CommunicationStyle.CONFRONTATIONAL:
                text = f"{name}, llevas tiempo sin avanzar. Retoma esto: {title}"
            else:
                text = _REENGAGEMENT_TEMPLATE.format(title=title)
        else:
            if style == CommunicationStyle.GENTLE:
                text = f"Tu siguiente paso podria ser: {title}"
            elif style == CommunicationStyle.DIRECT:
                text = f"{title} — siguiente."
            elif style == CommunicationStyle.CONFRONTATIONAL:
                text = f"Esto va primero: {title}. Arranca ya."
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

    def _get_user_profile(self, user_id: str | None):
        """Fetch UserProfile if profile_repo is available. Returns None on miss."""
        if not user_id or not self._profile_repo:
            return None
        try:
            return self._profile_repo.get(user_id)
        except Exception:
            return None

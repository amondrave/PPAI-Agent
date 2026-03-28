"""ER3 HU-R3.4 — Weekly report with insights (DIFERENCIAL)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

import structlog

from ppai.capture.domain.value_objects import TaskStatus
from ppai.profile.application.ports import ProfileRepository
from ppai.profile.domain.value_objects import CommunicationStyle, WeekendMode
from ppai.push.application.ports import CycleEventRepository, TelegramPushPort
from ppai.push.domain.value_objects import DispatchOutcome, NudgeDispatchStatus

logger = structlog.get_logger(__name__)

_WEEKDAY_NAMES = {
    0: "lunes",
    1: "martes",
    2: "miercoles",
    3: "jueves",
    4: "viernes",
    5: "sabado",
    6: "domingo",
}


class WeeklyReporter:
    """Generates and sends a weekly productivity report with insights."""

    def __init__(
        self,
        task_repo,
        block_repo,
        calendar_service,
        profile_repo: Optional[ProfileRepository],
        cycle_event_repo: CycleEventRepository,
        telegram_port: TelegramPushPort,
        weekly_insight_generator=None,
    ) -> None:
        self._task_repo = task_repo
        self._block_repo = block_repo
        self._calendar_service = calendar_service
        self._profile_repo = profile_repo
        self._cycle_event_repo = cycle_event_repo
        self._telegram = telegram_port
        # ER4: LLM weekly insight generator (optional)
        self._weekly_insight_generator = weekly_insight_generator

    def should_send_report(
        self,
        user_id: str,
        now: datetime,
        prefs,
        cycle_id: str,
    ) -> bool:
        """Determine if weekly report should be sent now."""
        # Only if calendar is connected
        if not self._calendar_service.is_connected(user_id):
            return False

        # Guard: already sent
        if self._cycle_event_repo.has_event_today(cycle_id, "WEEKLY_REPORT_SENT"):
            return False

        # Check profile for weekend mode
        profile = self._get_profile(user_id)
        weekend_mode = profile.weekend_mode if profile else WeekendMode.DESCANSO

        weekday = now.weekday()  # 0=Mon, 6=Sun

        # Sunday evening for regular users, Monday morning for weekend=rest
        if weekend_mode == WeekendMode.DESCANSO:
            # Monday morning
            if weekday != 0:
                return False
            return prefs.is_within_start_window(now)
        else:
            # Sunday at daily_end_time
            if weekday != 6:
                return False
            return prefs.is_within_end_window(now)

    def generate_and_send_report(
        self,
        user_id: str,
        now: datetime,
        cycle_id: str,
    ) -> Optional[DispatchOutcome]:
        """Generate and send the weekly report."""
        report_text = self.generate_weekly_report(user_id, now)
        if not report_text:
            return None

        sent = self._telegram.send_message(str(user_id), report_text)
        if sent:
            self._cycle_event_repo.record_nudge_event(
                cycle_id=cycle_id,
                event_type="WEEKLY_REPORT_SENT",
                metadata={"sent_at": now.isoformat()},
            )
            logger.info("weekly_report.sent", user_id=user_id)
            return DispatchOutcome(
                status=NudgeDispatchStatus.sent,
                user_id=user_id,
                cycle_id=cycle_id,
                sent_at=now,
                reason="weekly_report",
            )
        return DispatchOutcome(
            status=NudgeDispatchStatus.failed,
            user_id=user_id,
            reason="weekly_report_send_failed",
        )

    def generate_weekly_report(self, user_id: str, now: datetime) -> str:
        """Build a weekly report covering the last 7 days."""
        profile = self._get_profile(user_id)
        style = profile.communication_style if profile else None
        name = profile.name if profile else ""

        # Collect data for last 7 days
        completed_tasks = []
        snoozed_tasks = []
        untouched_tasks = []
        blocks_planned_total = 0
        blocks_completed_total = 0
        completions_by_day: Counter = Counter()

        for days_ago in range(7):
            target_date = (now - timedelta(days=days_ago)).date()
            date_str = target_date.strftime("%Y-%m-%d")
            weekday = target_date.weekday()

            # Count blocks
            blocks = self._block_repo.get_plan(user_id, date_str)
            planned = len(blocks)
            completed_blocks = sum(1 for b in blocks if b.status.value == "completed")
            blocks_planned_total += planned
            blocks_completed_total += completed_blocks

            # Count completed tasks for this day
            completions_by_day[weekday] += completed_blocks

        # Get overall task status
        try:
            done_tasks = self._task_repo.list_by_status(user_id, TaskStatus.DONE)
            week_start = (now - timedelta(days=7)).date()
            completed_tasks = [
                t for t in done_tasks
                if t.completed_at and t.completed_at.date() >= week_start
            ]
        except Exception:
            completed_tasks = []

        try:
            snoozed_tasks = self._task_repo.list_by_status(user_id, TaskStatus.SNOOZED)
        except Exception:
            snoozed_tasks = []

        try:
            pending = self._task_repo.list_by_status(user_id, TaskStatus.PENDING)
            prioritized = self._task_repo.list_by_status(user_id, TaskStatus.PRIORITIZED)
            untouched_tasks = pending + prioritized
        except Exception:
            untouched_tasks = []

        # Calculate most/least productive day
        most_productive_day = None
        least_productive_day = None
        if completions_by_day:
            most_productive_day = max(completions_by_day, key=completions_by_day.get)
            least_productive_day = min(completions_by_day, key=completions_by_day.get)

        # Build report
        if style == CommunicationStyle.GENTLE:
            header = f"Hola {name}, aqui tienes tu resumen semanal:\n"
        elif style == CommunicationStyle.DIRECT:
            header = f"{name}, reporte semanal:\n"
        elif style == CommunicationStyle.CONFRONTATIONAL:
            header = f"{name}, esto es lo que paso esta semana:\n"
        else:
            header = f"Resumen semanal:\n"

        parts = [header]

        # Stats section
        parts.append(f"Tareas completadas: {len(completed_tasks)}")
        parts.append(f"Tareas pospuestas: {len(snoozed_tasks)}")
        parts.append(f"Tareas pendientes: {len(untouched_tasks)}")
        parts.append("")

        # Blocks section
        if blocks_planned_total > 0:
            completion_rate = int(
                (blocks_completed_total / blocks_planned_total) * 100
            )
            parts.append(
                f"Bloques: {blocks_completed_total}/{blocks_planned_total} "
                f"completados ({completion_rate}%)"
            )
        else:
            parts.append("Bloques: sin bloques planificados esta semana")

        # Productivity insights
        if most_productive_day is not None:
            parts.append("")
            day_name = _WEEKDAY_NAMES.get(most_productive_day, "?")
            parts.append(f"Dia mas productivo: {day_name}")

        if least_productive_day is not None and least_productive_day != most_productive_day:
            day_name = _WEEKDAY_NAMES.get(least_productive_day, "?")
            parts.append(f"Dia menos productivo: {day_name}")

        # ER4: Try LLM-enriched insights
        llm_insight = None
        if self._weekly_insight_generator and profile:
            try:
                best_day_name = _WEEKDAY_NAMES.get(most_productive_day, "?") if most_productive_day is not None else "?"
                worst_day_name = _WEEKDAY_NAMES.get(least_productive_day, "?") if least_productive_day is not None else "?"
                llm_insight = self._weekly_insight_generator.generate(
                    name=name,
                    occupation=profile.occupation or "",
                    completed=len(completed_tasks),
                    snoozed=len(snoozed_tasks),
                    untouched=len(untouched_tasks),
                    blocks_completed=blocks_completed_total,
                    blocks_planned=blocks_planned_total,
                    best_day=best_day_name,
                    worst_day=worst_day_name,
                )
            except Exception:
                logger.warning("er4.weekly_insight_llm_failed", extra={"user_id": user_id})

        if llm_insight:
            parts.append(f"\nQue salio bien: {llm_insight.what_went_well}")
            parts.append(f"\nPatron detectado: {llm_insight.problematic_pattern}")
            parts.append(f"\nSugerencia: {llm_insight.suggestion}")
            parts.append(f"\n{llm_insight.question}")
        else:
            # Fallback: static pattern identification
            pattern = self._identify_pattern(
                completions_by_day, blocks_planned_total, blocks_completed_total,
            )
            if pattern:
                parts.append(f"\nPatron detectado: {pattern}")

            suggestion = self._generate_suggestion(
                len(completed_tasks), len(snoozed_tasks), len(untouched_tasks),
                blocks_planned_total, blocks_completed_total, style,
            )
            if suggestion:
                parts.append(f"\nSugerencia: {suggestion}")

            parts.append("\nQuieres cambiar algo para la proxima semana?")

        return "\n".join(parts)

    def _identify_pattern(
        self, completions_by_day: Counter, planned: int, completed: int,
    ) -> Optional[str]:
        """Identify one productivity pattern from the week's data."""
        if not completions_by_day:
            return None

        # Check if a specific day is consistently low
        for day, count in completions_by_day.items():
            if count == 0 and day < 5:  # Weekday with 0 completions
                day_name = _WEEKDAY_NAMES.get(day, "?")
                return (
                    f"Los {day_name} no completaste ningun bloque. "
                    f"Considera ajustar tu planificacion para ese dia."
                )

        # Check overall completion rate
        if planned > 0 and completed / planned < 0.3:
            return (
                "Tu tasa de finalizacion de bloques esta por debajo del 30%. "
                "Intenta planificar menos bloques pero mas realistas."
            )

        return None

    def _generate_suggestion(
        self,
        completed: int,
        snoozed: int,
        untouched: int,
        blocks_planned: int,
        blocks_completed: int,
        style,
    ) -> Optional[str]:
        """Generate 1-2 concrete suggestions for next week."""
        if snoozed > completed and snoozed > 0:
            return (
                "Esta semana pospusiste mas tareas de las que completaste. "
                "Revisa si esas tareas siguen siendo relevantes."
            )

        if blocks_planned > 0 and blocks_completed < blocks_planned * 0.5:
            return (
                "Menos de la mitad de tus bloques se completaron. "
                "Prueba con bloques mas cortos (25 min) la proxima semana."
            )

        if untouched > 5:
            return (
                "Tienes muchas tareas pendientes acumuladas. "
                "Considera eliminar las que ya no son relevantes."
            )

        if completed > 0:
            return "Buen ritmo esta semana. Mantenerlo es el reto."

        return None

    def _get_profile(self, user_id: str):
        if not self._profile_repo:
            return None
        try:
            return self._profile_repo.get(user_id)
        except Exception:
            return None

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from ppai.capture.application.ports import (
    TaskStateRepository,
    EventRepository,
    DedupRepository,
)
from ppai.capture.domain.entities import CaptureEvent, Intent, TaskState
from ppai.capture.domain.exceptions import (
    InvalidInputError,
    TaskLimitReachedError,
)
from ppai.shared.domain.base_entity import generate_id

logger = logging.getLogger(__name__)

# ER5: Time slot patterns — #HH:MM-HH:MM (range) or #HH:MM (single, defaults to 1h block)
_TIME_SLOT_RE = re.compile(r"#(\d{1,2}:\d{2})-(\d{1,2}:\d{2})")
_TIME_SINGLE_RE = re.compile(r"#(\d{1,2}:\d{2})(?!\S)")

# ER5: Duration patterns — "30min", "1h", "1.5h", "45 minutos", "2 horas"
_DURATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(\d+(?:\.\d+)?)\s*h(?:oras?)?\b", re.IGNORECASE), "hours"),
    (re.compile(r"(\d+)\s*min(?:utos?)?\b", re.IGNORECASE), "minutes"),
]

_HASHTAG_RE = re.compile(r"#(\w+)")
_TEMPORAL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpara\s+mañana\b", re.IGNORECASE), "tomorrow"),
    (re.compile(r"\bmañana\b", re.IGNORECASE), "tomorrow"),
    (re.compile(r"\bpara\s+hoy\b", re.IGNORECASE), "today"),
    (re.compile(r"\bhoy\b", re.IGNORECASE), "today"),
    (re.compile(r"\burgente\b", re.IGNORECASE), "today"),
    (re.compile(r"\bpara\s+(\d{1,2})/(\d{1,2})\b"), "date_dm"),
    (re.compile(r"\bpara\s+(\d{4}-\d{2}-\d{2})\b"), "date_iso"),
]
_HAS_ALNUM = re.compile(r"[a-zA-Z0-9]")


@dataclass
class CaptureResult:
    created: list[TaskState] = field(default_factory=list)
    duplicated: int = 0
    limit_reached: int = 0


class CaptureService:
    def __init__(
        self,
        task_repo: TaskStateRepository,
        event_repo: EventRepository,
        dedup_repo: DedupRepository,
        active_task_limit: int = 50,
        category_classifier: object | None = None,
        task_analyzer: object | None = None,
        profile_repo: object | None = None,
    ) -> None:
        self._task_repo = task_repo
        self._event_repo = event_repo
        self._dedup_repo = dedup_repo
        self._active_task_limit = active_task_limit
        self._category_classifier = category_classifier
        # ER4: LLM-based task analyzer (optional, falls back to regex)
        self._task_analyzer = task_analyzer
        self._profile_repo = profile_repo
        # Optional hook: called with user_id after at least one task is captured.
        # Used by DecisionService to invalidate the Top 3 cache (UOW-02).
        self.on_task_captured: callable[[str], None] | None = None

    def process_message(self, user_id: str, text: str | None) -> CaptureResult:
        validated = self._validate_input(text)
        lines = self._parse_lines(validated)
        intent = Intent(user_id=user_id, raw_text=validated)
        correlation_id = generate_id()
        result = CaptureResult()

        for line in lines:
            original, normalized = self._normalize(line)

            # ER5: Extract time slot and duration BEFORE tag/deadline extraction
            normalized, slot_start, slot_end = self._extract_time_slot(normalized)
            normalized, explicit_duration = self._extract_duration(normalized)

            normalized, tag, deadline = self._extract_tag_deadline(normalized)

            if self._check_dedup(user_id, original):
                result.duplicated += 1
                continue

            if not self._check_task_limit(user_id):
                result.limit_reached += 1
                continue

            task = self._create_task(
                user_id=user_id,
                original=original,
                normalized=normalized,
                tag=tag,
                deadline=deadline,
                intent_id=intent.intent_id,
            )

            # ER5: Set time slot or explicit duration on task
            if slot_start and slot_end:
                task.requested_slot_start = slot_start
                task.requested_slot_end = slot_end
                task.has_explicit_time = True
                # Calculate estimated_minutes from slot
                try:
                    sh, sm = map(int, slot_start.split(":"))
                    eh, em = map(int, slot_end.split(":"))
                    task.estimated_minutes = (eh * 60 + em) - (sh * 60 + sm)
                except (ValueError, TypeError):
                    pass
                self._task_repo.save(task)
            elif explicit_duration:
                task.estimated_minutes = explicit_duration
                task.has_explicit_time = True
                self._task_repo.save(task)
            self._classify_task(task)
            result.created.append(task)
            self._emit_event(task, correlation_id)
            self._record_dedup(user_id, original, task.task_id)

        if result.created and self.on_task_captured is not None:
            self.on_task_captured(user_id)

        return result

    def build_confirmation(self, result: CaptureResult) -> str:
        created = len(result.created)
        dup = result.duplicated
        limit = result.limit_reached

        if created == 0 and dup > 0 and limit == 0:
            return f"No se registraron tareas nuevas. {dup} duplicada(s) omitida(s)."

        if created == 0 and limit > 0:
            return (
                "Limite de tareas activas alcanzado (50). "
                "Completa o elimina tareas existentes para agregar nuevas."
            )

        parts: list[str] = ["Capturado."]
        if created == 1:
            parts.append("Tu tarea ha sido registrada.")
        else:
            parts.append(f"{created} tareas han sido registradas.")

        if dup > 0:
            parts.append(f"{dup} duplicada(s) omitida(s).")

        if limit > 0:
            parts.append(
                f"Limite alcanzado, {limit} tarea(s) no pudieron agregarse."
            )

        return " ".join(parts)

    def _classify_task(self, task: TaskState) -> None:
        """Classify task: try LLM first (ER4), fall back to regex (ER2).

        Note: if the user provided an explicit duration (has_explicit_time=True),
        we preserve their estimated_minutes and only update category.
        """
        user_provided_minutes = task.estimated_minutes if task.has_explicit_time else None

        # ER4: Try LLM-based analysis first
        if self._task_analyzer is not None:
            try:
                occupation = self._get_user_occupation(task.user_id)
                analysis = self._task_analyzer.analyze(task.normalized_text, occupation)
                if analysis is not None:
                    task.category = analysis.category
                    task.estimated_minutes = user_provided_minutes or analysis.estimated_minutes
                    self._task_repo.save(task)
                    return
            except Exception:
                logger.warning(
                    "LLM task analysis failed, using regex fallback",
                    extra={"task_id": task.task_id},
                )

        # Fallback: regex-based classifier (ER2)
        if self._category_classifier is None:
            return
        try:
            tags = [task.tag] if task.tag else []
            task.category = self._category_classifier.classify(task.normalized_text, tags).value
            task.estimated_minutes = user_provided_minutes or self._category_classifier.estimate_minutes(task.normalized_text)
            self._task_repo.save(task)
        except Exception:
            logger.warning(
                "Failed to classify task",
                extra={"task_id": task.task_id},
            )

    def _get_user_occupation(self, user_id: str) -> str:
        if not self._profile_repo:
            return ""
        try:
            profile = self._profile_repo.get(user_id)
            return profile.occupation if profile else ""
        except Exception:
            return ""

    # -- Private methods -------------------------------------------------------

    def _validate_input(self, text: str | None) -> str:
        if not text or not text.strip():
            raise InvalidInputError(
                "No pude interpretar tu mensaje. Por favor envia tu tarea como texto."
            )
        stripped = text.strip()
        if not _HAS_ALNUM.search(stripped):
            raise InvalidInputError(
                "No pude interpretar tu mensaje. Por favor envia tu tarea como texto."
            )
        return stripped

    def _parse_lines(self, text: str) -> list[str]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return lines

    def _normalize(self, line: str) -> tuple[str, str]:
        original = line
        normalized = " ".join(line.split())
        return original, normalized

    def _extract_time_slot(self, text: str) -> tuple[str, str | None, str | None]:
        """ER5: Extract time slot from text.

        Supports:
        - #HH:MM-HH:MM (range, e.g., #15:00-16:30)
        - #HH:MM (single time, defaults to 1-hour block)
        """
        # Try range first
        match = _TIME_SLOT_RE.search(text)
        if match:
            slot_start = match.group(1)
            slot_end = match.group(2)
            text = text[: match.start()] + text[match.end() :]
            text = " ".join(text.split())
            return text, slot_start, slot_end

        # Try single time (default 1h block)
        match = _TIME_SINGLE_RE.search(text)
        if match:
            slot_start = match.group(1)
            try:
                h, m = map(int, slot_start.split(":"))
                end_h = h + 1
                slot_end = f"{end_h:02d}:{m:02d}"
            except (ValueError, TypeError):
                return text, None, None
            text = text[: match.start()] + text[match.end() :]
            text = " ".join(text.split())
            return text, slot_start, slot_end

        return text, None, None

    def _extract_duration(self, text: str) -> tuple[str, int | None]:
        """ER5: Extract duration (30min, 1h, 45 minutos) from text."""
        for pattern, kind in _DURATION_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            value = float(match.group(1))
            minutes = int(value * 60) if kind == "hours" else int(value)
            if minutes <= 0:
                continue
            text = text[: match.start()] + text[match.end() :]
            text = " ".join(text.split())
            return text, minutes
        return text, None

    def _extract_tag_deadline(
        self, text: str
    ) -> tuple[str, str | None, datetime | None]:
        tag = None
        deadline = None

        # ER5: Extract time slots BEFORE hashtag extraction (they use # prefix too)
        slot_match = _TIME_SLOT_RE.search(text)
        if slot_match:
            text = text[: slot_match.start()] + text[slot_match.end() :]
            text = " ".join(text.split())
        else:
            single_match = _TIME_SINGLE_RE.search(text)
            if single_match:
                text = text[: single_match.start()] + text[single_match.end() :]
                text = " ".join(text.split())

        tag_match = _HASHTAG_RE.search(text)
        if tag_match:
            tag = tag_match.group(1)
            text = text[: tag_match.start()] + text[tag_match.end() :]
            text = " ".join(text.split())

        for pattern, kind in _TEMPORAL_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue

            now = datetime.now(timezone.utc)
            if kind == "tomorrow":
                deadline = (now + timedelta(days=1)).replace(
                    hour=9, minute=0, second=0, microsecond=0
                )
            elif kind == "today":
                deadline = now.replace(hour=23, minute=59, second=0, microsecond=0)
            elif kind == "date_dm":
                day, month = int(match.group(1)), int(match.group(2))
                year = now.year
                deadline = datetime(year, month, day, 9, 0, tzinfo=timezone.utc)
            elif kind == "date_iso":
                deadline = datetime.fromisoformat(match.group(1)).replace(
                    hour=9, minute=0, tzinfo=timezone.utc
                )

            text = text[: match.start()] + text[match.end() :]
            text = " ".join(text.split())
            break

        return text, tag, deadline

    def _check_dedup(self, user_id: str, exact_text: str) -> bool:
        return self._dedup_repo.exists(user_id, exact_text)

    def _check_task_limit(self, user_id: str) -> bool:
        count = self._task_repo.count_active(user_id)
        return count < self._active_task_limit

    def _create_task(
        self,
        user_id: str,
        original: str,
        normalized: str,
        tag: str | None,
        deadline: datetime | None,
        intent_id: str,
    ) -> TaskState:
        task = TaskState(
            user_id=user_id,
            original_text=original,
            normalized_text=normalized,
            tag=tag,
            deadline=deadline,
            source_intent_id=intent_id,
        )
        task.transition_to_pending()
        self._task_repo.save(task)
        return task

    def _emit_event(self, task: TaskState, correlation_id: str) -> None:
        try:
            event = CaptureEvent(
                task_id=task.task_id,
                user_id=task.user_id,
                original_text=task.original_text,
                correlation_id=correlation_id,
            )
            self._event_repo.append(event)
        except Exception:
            logger.warning(
                "Failed to emit capture event",
                extra={"task_id": task.task_id},
            )

    def _record_dedup(self, user_id: str, exact_text: str, task_id: str) -> None:
        try:
            self._dedup_repo.record(user_id, exact_text, task_id)
        except Exception:
            logger.warning(
                "Failed to record dedup entry",
                extra={"task_id": task_id},
            )

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
    ) -> None:
        self._task_repo = task_repo
        self._event_repo = event_repo
        self._dedup_repo = dedup_repo
        self._active_task_limit = active_task_limit
        self._category_classifier = category_classifier
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
        """Classify the task category and estimate duration using CategoryClassifier."""
        if self._category_classifier is None:
            return
        try:
            tags = [task.tag] if task.tag else []
            task.category = self._category_classifier.classify(task.normalized_text, tags).value
            task.estimated_minutes = self._category_classifier.estimate_minutes(task.normalized_text)
            self._task_repo.save(task)
        except Exception:
            logger.warning(
                "Failed to classify task",
                extra={"task_id": task.task_id},
            )

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

    def _extract_tag_deadline(
        self, text: str
    ) -> tuple[str, str | None, datetime | None]:
        tag = None
        deadline = None

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

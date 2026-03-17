from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ppai.capture.application.capture_service import CaptureResult, CaptureService
from ppai.capture.domain.entities import CaptureEvent, DedupRecord, TaskState
from ppai.capture.domain.exceptions import InvalidInputError
from ppai.capture.domain.value_objects import TaskStatus


# -- Fake repositories --------------------------------------------------------


class FakeTaskRepo:
    def __init__(self, active_count: int = 0) -> None:
        self.saved: list[TaskState] = []
        self._active_count = active_count

    def save(self, task: TaskState) -> None:
        self.saved.append(task)

    def get_by_id(self, user_id: str, task_id: str) -> TaskState | None:
        for t in self.saved:
            if t.user_id == user_id and t.task_id == task_id:
                return t
        return None

    def count_active(self, user_id: str) -> int:
        return self._active_count + len(self.saved)


class FakeEventRepo:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.events: list[CaptureEvent] = []
        self._should_fail = should_fail

    def append(self, event: CaptureEvent) -> None:
        if self._should_fail:
            raise RuntimeError("event write failed")
        self.events.append(event)


class FakeDedupRepo:
    def __init__(self) -> None:
        self.records: dict[str, str] = {}

    def exists(self, user_id: str, exact_text: str) -> bool:
        return f"{user_id}:{exact_text}" in self.records

    def record(self, user_id: str, exact_text: str, task_id: str) -> None:
        self.records[f"{user_id}:{exact_text}"] = task_id


def _make_service(
    active_count: int = 0,
    event_fail: bool = False,
    limit: int = 50,
) -> tuple[CaptureService, FakeTaskRepo, FakeEventRepo, FakeDedupRepo]:
    task_repo = FakeTaskRepo(active_count=active_count)
    event_repo = FakeEventRepo(should_fail=event_fail)
    dedup_repo = FakeDedupRepo()
    svc = CaptureService(
        task_repo=task_repo,
        event_repo=event_repo,
        dedup_repo=dedup_repo,
        active_task_limit=limit,
    )
    return svc, task_repo, event_repo, dedup_repo


# -- Input Validation (BR-CAP-01) --------------------------------------------


class TestValidation:
    def test_none_text_raises(self):
        svc, *_ = _make_service()
        with pytest.raises(InvalidInputError):
            svc.process_message("u1", None)

    def test_empty_text_raises(self):
        svc, *_ = _make_service()
        with pytest.raises(InvalidInputError):
            svc.process_message("u1", "")

    def test_whitespace_only_raises(self):
        svc, *_ = _make_service()
        with pytest.raises(InvalidInputError):
            svc.process_message("u1", "   \n  \t  ")

    def test_emojis_only_raises(self):
        svc, *_ = _make_service()
        with pytest.raises(InvalidInputError):
            svc.process_message("u1", "😀🎉👍")

    def test_valid_text_passes(self):
        svc, *_ = _make_service()
        result = svc.process_message("u1", "comprar leche")
        assert len(result.created) == 1


# -- Multi-Line Parsing (BR-CAP-02) ------------------------------------------


class TestMultiLine:
    def test_single_line(self):
        svc, *_ = _make_service()
        result = svc.process_message("u1", "tarea uno")
        assert len(result.created) == 1

    def test_multiple_lines(self):
        svc, *_ = _make_service()
        result = svc.process_message("u1", "tarea uno\ntarea dos\ntarea tres")
        assert len(result.created) == 3

    def test_empty_lines_ignored(self):
        svc, *_ = _make_service()
        result = svc.process_message("u1", "tarea uno\n\n\ntarea dos\n  \ntarea tres")
        assert len(result.created) == 3

    def test_each_line_is_independent_task(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche\nllamar doctor")
        texts = [t.normalized_text for t in task_repo.saved]
        assert "comprar leche" in texts
        assert "llamar doctor" in texts


# -- Normalization (BR-CAP-09) -----------------------------------------------


class TestNormalization:
    def test_preserves_original(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "  comprar   leche  ")
        task = task_repo.saved[0]
        assert task.original_text == "comprar   leche"
        assert task.normalized_text == "comprar leche"

    def test_strips_outer_whitespace(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "  hola  ")
        task = task_repo.saved[0]
        assert task.normalized_text == "hola"


# -- Tag Extraction (BR-CAP-03) ----------------------------------------------


class TestTagExtraction:
    def test_extracts_first_hashtag(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche #trabajo #personal")
        task = task_repo.saved[0]
        assert task.tag == "trabajo"

    def test_removes_hashtag_from_normalized(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche #trabajo")
        task = task_repo.saved[0]
        assert "#trabajo" not in task.normalized_text
        assert "comprar leche" in task.normalized_text

    def test_no_hashtag_returns_none(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche")
        assert task_repo.saved[0].tag is None


# -- Deadline Extraction (BR-CAP-04) -----------------------------------------


class TestDeadlineExtraction:
    def test_manana(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche para mañana")
        task = task_repo.saved[0]
        assert task.deadline is not None
        assert task.deadline.hour == 9

    def test_hoy(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche para hoy")
        task = task_repo.saved[0]
        assert task.deadline is not None
        assert task.deadline.hour == 23

    def test_urgente(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche urgente")
        task = task_repo.saved[0]
        assert task.deadline is not None
        assert task.deadline.hour == 23

    def test_date_dd_mm(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "entregar reporte para 25/12")
        task = task_repo.saved[0]
        assert task.deadline is not None
        assert task.deadline.month == 12
        assert task.deadline.day == 25
        assert task.deadline.hour == 9

    def test_date_iso(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "entregar reporte para 2026-06-15")
        task = task_repo.saved[0]
        assert task.deadline is not None
        assert task.deadline == datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc)

    def test_no_deadline_returns_none(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche")
        assert task_repo.saved[0].deadline is None

    def test_removes_temporal_from_normalized(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche para mañana")
        task = task_repo.saved[0]
        assert "mañana" not in task.normalized_text
        assert "comprar leche" in task.normalized_text


# -- Deduplication (BR-CAP-05) -----------------------------------------------


class TestDedup:
    def test_duplicate_is_skipped(self):
        svc, task_repo, _, dedup_repo = _make_service()
        dedup_repo.records["u1:comprar leche"] = "existing-task"
        result = svc.process_message("u1", "comprar leche")
        assert len(result.created) == 0
        assert result.duplicated == 1

    def test_non_duplicate_passes(self):
        svc, *_ = _make_service()
        result = svc.process_message("u1", "comprar leche")
        assert len(result.created) == 1
        assert result.duplicated == 0

    def test_mixed_duplicates(self):
        svc, _, _, dedup_repo = _make_service()
        dedup_repo.records["u1:tarea uno"] = "existing"
        result = svc.process_message("u1", "tarea uno\ntarea dos")
        assert len(result.created) == 1
        assert result.duplicated == 1

    def test_records_dedup_after_creation(self):
        svc, _, _, dedup_repo = _make_service()
        svc.process_message("u1", "comprar leche")
        assert "u1:comprar leche" in dedup_repo.records


# -- Task Limit (BR-CAP-06) --------------------------------------------------


class TestTaskLimit:
    def test_under_limit_creates(self):
        svc, *_ = _make_service(active_count=49)
        result = svc.process_message("u1", "nueva tarea")
        assert len(result.created) == 1

    def test_at_limit_rejects(self):
        svc, *_ = _make_service(active_count=50)
        result = svc.process_message("u1", "nueva tarea")
        assert len(result.created) == 0
        assert result.limit_reached == 1

    def test_partial_batch_limit(self):
        svc, *_ = _make_service(active_count=49, limit=50)
        result = svc.process_message("u1", "tarea 1\ntarea 2\ntarea 3")
        assert len(result.created) == 1
        assert result.limit_reached == 2


# -- Task Creation & Status (BR-CAP-10) --------------------------------------


class TestTaskCreation:
    def test_task_transitions_to_pending(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche")
        assert task_repo.saved[0].status == TaskStatus.PENDING

    def test_task_persisted(self):
        svc, task_repo, *_ = _make_service()
        svc.process_message("u1", "comprar leche")
        assert len(task_repo.saved) == 1


# -- Event Emission (BR-CAP-08) ----------------------------------------------


class TestEventEmission:
    def test_event_emitted(self):
        svc, _, event_repo, _ = _make_service()
        svc.process_message("u1", "comprar leche")
        assert len(event_repo.events) == 1
        assert event_repo.events[0].event_type == "INTENT_CAPTURED"

    def test_event_failure_does_not_block(self):
        svc, task_repo, _, _ = _make_service(event_fail=True)
        result = svc.process_message("u1", "comprar leche")
        assert len(result.created) == 1
        assert len(task_repo.saved) == 1


# -- Confirmation Messages (BR-CAP-07) ---------------------------------------


class TestConfirmation:
    def test_single_task(self):
        svc, *_ = _make_service()
        result = CaptureResult(created=[TaskState(
            user_id="u1", original_text="a", normalized_text="a", source_intent_id="i1",
        )])
        msg = svc.build_confirmation(result)
        assert "Capturado" in msg
        assert "Tu tarea ha sido registrada" in msg

    def test_multiple_tasks(self):
        svc, *_ = _make_service()
        tasks = [
            TaskState(user_id="u1", original_text=f"t{i}", normalized_text=f"t{i}", source_intent_id="i1")
            for i in range(3)
        ]
        result = CaptureResult(created=tasks)
        msg = svc.build_confirmation(result)
        assert "3 tareas han sido registradas" in msg

    def test_with_duplicates(self):
        svc, *_ = _make_service()
        result = CaptureResult(
            created=[TaskState(user_id="u1", original_text="a", normalized_text="a", source_intent_id="i1")],
            duplicated=2,
        )
        msg = svc.build_confirmation(result)
        assert "Capturado" in msg
        assert "2 duplicada(s) omitida(s)" in msg

    def test_with_limit(self):
        svc, *_ = _make_service()
        result = CaptureResult(
            created=[TaskState(user_id="u1", original_text="a", normalized_text="a", source_intent_id="i1")],
            limit_reached=1,
        )
        msg = svc.build_confirmation(result)
        assert "Limite alcanzado" in msg

    def test_all_duplicates(self):
        svc, *_ = _make_service()
        result = CaptureResult(duplicated=3)
        msg = svc.build_confirmation(result)
        assert "No se registraron tareas nuevas" in msg

    def test_all_limit_reached(self):
        svc, *_ = _make_service()
        result = CaptureResult(limit_reached=2)
        msg = svc.build_confirmation(result)
        assert "Limite de tareas activas alcanzado" in msg

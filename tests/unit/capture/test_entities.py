from datetime import datetime, timezone

from ppai.capture.domain.entities import Intent, TaskState, CaptureEvent, DedupRecord
from ppai.capture.domain.value_objects import TaskStatus


class TestIntent:
    def test_create_with_defaults(self):
        intent = Intent(user_id="u1", raw_text="comprar leche")
        assert intent.user_id == "u1"
        assert intent.raw_text == "comprar leche"
        assert intent.source == "telegram"
        assert intent.intent_id  # UUID generated
        assert intent.created_at.tzinfo == timezone.utc

    def test_custom_source(self):
        intent = Intent(user_id="u1", raw_text="test", source="api")
        assert intent.source == "api"


class TestTaskState:
    def test_create_defaults_to_captured(self):
        task = TaskState(
            user_id="u1",
            original_text="comprar leche",
            normalized_text="comprar leche",
            source_intent_id="intent-1",
        )
        assert task.status == TaskStatus.CAPTURED
        assert task.tag is None
        assert task.deadline is None
        assert task.task_id
        assert task.created_at.tzinfo == timezone.utc

    def test_create_with_tag_and_deadline(self):
        dl = datetime(2026, 3, 18, 9, 0, tzinfo=timezone.utc)
        task = TaskState(
            user_id="u1",
            original_text="comprar leche #trabajo para manana",
            normalized_text="comprar leche",
            source_intent_id="intent-1",
            tag="trabajo",
            deadline=dl,
        )
        assert task.tag == "trabajo"
        assert task.deadline == dl

    def test_transition_to_pending(self):
        task = TaskState(
            user_id="u1",
            original_text="test",
            normalized_text="test",
            source_intent_id="i1",
        )
        assert task.status == TaskStatus.CAPTURED
        old_updated = task.updated_at

        task.transition_to_pending()

        assert task.status == TaskStatus.PENDING
        assert task.updated_at >= old_updated

    def test_unique_ids(self):
        t1 = TaskState(user_id="u1", original_text="a", normalized_text="a", source_intent_id="i1")
        t2 = TaskState(user_id="u1", original_text="b", normalized_text="b", source_intent_id="i1")
        assert t1.task_id != t2.task_id


class TestCaptureEvent:
    def test_create_with_defaults(self):
        event = CaptureEvent(
            task_id="t1",
            user_id="u1",
            original_text="comprar leche",
            correlation_id="corr-1",
        )
        assert event.event_type == "INTENT_CAPTURED"
        assert event.event_id
        assert event.timestamp.tzinfo == timezone.utc

    def test_unique_event_ids(self):
        e1 = CaptureEvent(task_id="t1", user_id="u1", original_text="a", correlation_id="c1")
        e2 = CaptureEvent(task_id="t2", user_id="u1", original_text="b", correlation_id="c2")
        assert e1.event_id != e2.event_id


class TestDedupRecord:
    def test_create(self):
        record = DedupRecord(user_id="u1", exact_text="comprar leche", task_id="t1")
        assert record.user_id == "u1"
        assert record.exact_text == "comprar leche"
        assert record.last_seen_at.tzinfo == timezone.utc

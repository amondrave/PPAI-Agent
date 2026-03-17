from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from moto import mock_aws

from ppai.capture.application.capture_service import CaptureService
from ppai.capture.domain.exceptions import InvalidInputError
from ppai.capture.domain.value_objects import TaskStatus
from ppai.capture.infrastructure.dynamodb_dedup_repo import DynamoDBDedupRepository
from ppai.capture.infrastructure.dynamodb_event_repo import DynamoDBEventRepository
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.capture.infrastructure.telegram_adapter import TelegramAdapter
from ppai.shared.infrastructure.config import Settings
from ppai.shared.infrastructure.rate_limiter import InMemoryRateLimiter


@pytest.fixture()
def settings():
    return Settings(
        telegram_bot_token="fake-token",
        dynamodb_table_prefix="ppai",
        active_task_limit=50,
        dedup_window_seconds=300,
        rate_limit_per_minute=10,
    )


@pytest.fixture()
def repos(dynamodb_resource, settings):
    task_repo = DynamoDBTaskStateRepository(dynamodb_resource.Table("ppai-tasks"))
    event_repo = DynamoDBEventRepository(dynamodb_resource.Table("ppai-events"))
    dedup_repo = DynamoDBDedupRepository(dynamodb_resource.Table("ppai-dedup"), settings)
    return task_repo, event_repo, dedup_repo


@pytest.fixture()
def adapter(repos, settings):
    task_repo, event_repo, dedup_repo = repos
    capture_service = CaptureService(
        task_repo=task_repo,
        event_repo=event_repo,
        dedup_repo=dedup_repo,
        active_task_limit=settings.active_task_limit,
    )
    rate_limiter = InMemoryRateLimiter(
        max_requests=settings.rate_limit_per_minute,
        window_seconds=60,
    )
    return TelegramAdapter(capture_service, rate_limiter)


def _fake_update(user_id: int = 12345, text: str | None = "comprar leche"):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


# -- Full capture flow --------------------------------------------------------


class TestFullCaptureFlow:
    @pytest.mark.asyncio
    async def test_single_task_captured(self, adapter, repos):
        task_repo, event_repo, _ = repos
        update = _fake_update(text="comprar leche")

        await adapter.message_handler(update, MagicMock())

        update.message.reply_text.assert_called_once()
        reply = update.message.reply_text.call_args[0][0]
        assert "Capturado" in reply
        assert "Tu tarea ha sido registrada" in reply

        tasks = task_repo._table.scan()["Items"]
        assert len(tasks) == 1
        assert tasks[0]["normalizedText"] == "comprar leche"
        assert tasks[0]["status"] == TaskStatus.PENDING.value

        events = event_repo._table.scan()["Items"]
        assert len(events) == 1
        assert events[0]["eventType"] == "INTENT_CAPTURED"

    @pytest.mark.asyncio
    async def test_multiline_creates_multiple_tasks(self, adapter, repos):
        task_repo, _, _ = repos
        update = _fake_update(text="tarea uno\ntarea dos\ntarea tres")

        await adapter.message_handler(update, MagicMock())

        reply = update.message.reply_text.call_args[0][0]
        assert "3 tareas han sido registradas" in reply

        tasks = task_repo._table.scan()["Items"]
        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_tag_and_deadline_extracted(self, adapter, repos):
        task_repo, _, _ = repos
        update = _fake_update(text="entregar reporte #trabajo para mañana")

        await adapter.message_handler(update, MagicMock())

        tasks = task_repo._table.scan()["Items"]
        assert len(tasks) == 1
        assert tasks[0]["tag"] == "trabajo"
        assert "deadline" in tasks[0]


# -- Empty / invalid input ----------------------------------------------------


class TestInvalidInput:
    @pytest.mark.asyncio
    async def test_empty_message(self, adapter):
        update = _fake_update(text="")

        await adapter.message_handler(update, MagicMock())

        reply = update.message.reply_text.call_args[0][0]
        assert "No pude interpretar" in reply

    @pytest.mark.asyncio
    async def test_none_text(self, adapter):
        update = _fake_update(text=None)

        await adapter.message_handler(update, MagicMock())

        reply = update.message.reply_text.call_args[0][0]
        assert "No pude interpretar" in reply

    @pytest.mark.asyncio
    async def test_emojis_only(self, adapter):
        update = _fake_update(text="😀🎉")

        await adapter.message_handler(update, MagicMock())

        reply = update.message.reply_text.call_args[0][0]
        assert "No pude interpretar" in reply


# -- Deduplication -------------------------------------------------------------


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_duplicate_message_skipped(self, adapter, repos):
        task_repo, _, _ = repos
        update1 = _fake_update(text="comprar leche")
        update2 = _fake_update(text="comprar leche")

        await adapter.message_handler(update1, MagicMock())
        await adapter.message_handler(update2, MagicMock())

        reply = update2.message.reply_text.call_args[0][0]
        assert "duplicada" in reply.lower() or "No se registraron" in reply

        tasks = task_repo._table.scan()["Items"]
        assert len(tasks) == 1


# -- Task limit ----------------------------------------------------------------


class TestTaskLimit:
    @pytest.mark.asyncio
    async def test_limit_reached(self, adapter, repos, settings):
        task_repo, _, _ = repos

        for i in range(50):
            from ppai.capture.domain.entities import TaskState
            task = TaskState(
                user_id="12345",
                original_text=f"task {i}",
                normalized_text=f"task {i}",
                source_intent_id=f"intent-{i}",
            )
            task.transition_to_pending()
            task_repo.save(task)

        update = _fake_update(text="tarea nueva")
        await adapter.message_handler(update, MagicMock())

        reply = update.message.reply_text.call_args[0][0]
        assert "Limite" in reply or "limite" in reply


# -- Rate limiting -------------------------------------------------------------


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, adapter):
        for _ in range(10):
            update = _fake_update(text="tarea")
            await adapter.message_handler(update, MagicMock())

        update = _fake_update(text="una mas")
        await adapter.message_handler(update, MagicMock())

        reply = update.message.reply_text.call_args[0][0]
        assert "Demasiados mensajes" in reply

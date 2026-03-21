"""E2E tests for UOW-02 Decision Core — /top3 command + inline callbacks.

Uses moto DynamoDB (via conftest) + MagicMock for Telegram objects.
No real Telegram connection needed.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.decision.application.decision_service import DecisionService
from ppai.decision.domain.scoring_engine import ScoringEngine
from ppai.decision.infrastructure.decision_telegram_adapter import DecisionTelegramAdapter
from ppai.decision.infrastructure.dynamodb_cycle_repo import DynamoDBCycleRepository

USER_ID = 99999
USER_STR = str(USER_ID)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def task_repo(dynamodb_resource):
    return DynamoDBTaskStateRepository(dynamodb_resource.Table("ppai-tasks"))


@pytest.fixture()
def cycle_repo(dynamodb_resource):
    return DynamoDBCycleRepository(dynamodb_resource.Table("ppai-cycles"))


@pytest.fixture()
def decision_service(task_repo, cycle_repo):
    return DecisionService(
        task_repo=task_repo,
        cycle_repo=cycle_repo,
        scoring_engine=ScoringEngine(),
    )


@pytest.fixture()
def adapter(decision_service):
    return DecisionTelegramAdapter(decision_service)


def _fake_command_update(user_id: int = USER_ID) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def _fake_callback_update(user_id: int = USER_ID, data: str = "done:task-1") -> MagicMock:
    update = MagicMock()
    update.callback_query.from_user.id = user_id
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    update.callback_query.message.reply_text = AsyncMock()
    return update


def _save_pending_task(task_repo, user_id: str = USER_STR, snooze_count: int = 0) -> TaskState:
    task = TaskState(
        user_id=user_id,
        original_text="tarea de prueba",
        normalized_text="Tarea de prueba",
        source_intent_id="intent-1",
        status=TaskStatus.PENDING,
        snooze_count=snooze_count,
    )
    task_repo.save(task)
    return task


# ---------------------------------------------------------------------------
# /top3 — empty inbox (BR-DEC-07)
# ---------------------------------------------------------------------------

class TestTop3CommandEmptyInbox:
    @pytest.mark.asyncio
    async def test_empty_inbox_sends_empty_message(self, adapter):
        update = _fake_command_update()
        await adapter.top3_handler(update, MagicMock())

        update.message.reply_text.assert_called_once()
        reply = update.message.reply_text.call_args[0][0]
        assert "bandeja está vacía" in reply

    @pytest.mark.asyncio
    async def test_empty_inbox_does_not_send_keyboard(self, adapter):
        update = _fake_command_update()
        await adapter.top3_handler(update, MagicMock())

        # reply_text called once, with no InlineKeyboardMarkup
        call_kwargs = update.message.reply_text.call_args
        assert call_kwargs[1].get("reply_markup") is None if call_kwargs[1] else True


# ---------------------------------------------------------------------------
# /top3 — with tasks (BR-DEC-06)
# ---------------------------------------------------------------------------

class TestTop3CommandWithTasks:
    @pytest.mark.asyncio
    async def test_sends_one_message_per_task(self, adapter, task_repo):
        for _ in range(3):
            _save_pending_task(task_repo)

        update = _fake_command_update()
        await adapter.top3_handler(update, MagicMock())

        # 3 task messages (no partial message when exactly 3)
        assert update.message.reply_text.call_count == 3

    @pytest.mark.asyncio
    async def test_message_includes_position_number(self, adapter, task_repo):
        _save_pending_task(task_repo)

        update = _fake_command_update()
        await adapter.top3_handler(update, MagicMock())

        first_call_text = update.message.reply_text.call_args_list[0][0][0]
        assert first_call_text.startswith("1.")

    @pytest.mark.asyncio
    async def test_message_has_inline_keyboard(self, adapter, task_repo):
        _save_pending_task(task_repo)

        update = _fake_command_update()
        await adapter.top3_handler(update, MagicMock())

        call_kwargs = update.message.reply_text.call_args_list[0][1]
        keyboard = call_kwargs.get("reply_markup")
        assert keyboard is not None

        # Verify 3 buttons: done, snooze, clarify
        buttons = keyboard.inline_keyboard[0]
        labels = [b.text for b in buttons]
        assert any("Hecho" in l for l in labels)
        assert any("Posponer" in l for l in labels)
        assert any("Aclarar" in l for l in labels)

    @pytest.mark.asyncio
    async def test_tasks_transition_to_prioritized(self, adapter, task_repo):
        tasks = [_save_pending_task(task_repo) for _ in range(2)]

        update = _fake_command_update()
        await adapter.top3_handler(update, MagicMock())

        for task in tasks:
            saved = task_repo.get_by_id(USER_STR, task.task_id)
            assert saved.status == TaskStatus.PRIORITIZED

    @pytest.mark.asyncio
    async def test_cycle_created_in_db(self, adapter, task_repo, cycle_repo):
        _save_pending_task(task_repo)

        update = _fake_command_update()
        await adapter.top3_handler(update, MagicMock())

        from datetime import date
        today = date.today().isoformat()
        cycle = cycle_repo.get_active(USER_STR, today)
        assert cycle is not None


# ---------------------------------------------------------------------------
# /top3 — partial inbox (BR-DEC-07)
# ---------------------------------------------------------------------------

class TestTop3CommandPartialInbox:
    @pytest.mark.asyncio
    async def test_2_tasks_shows_motivational_message(self, adapter, task_repo):
        _save_pending_task(task_repo)
        _save_pending_task(task_repo)

        update = _fake_command_update()
        await adapter.top3_handler(update, MagicMock())

        # 2 task messages + 1 motivational
        assert update.message.reply_text.call_count == 3

        last_reply = update.message.reply_text.call_args_list[-1][0][0]
        assert "Captúralos" in last_reply or "más pendientes" in last_reply

    @pytest.mark.asyncio
    async def test_1_task_shows_motivational_message(self, adapter, task_repo):
        _save_pending_task(task_repo)

        update = _fake_command_update()
        await adapter.top3_handler(update, MagicMock())

        assert update.message.reply_text.call_count == 2
        last_reply = update.message.reply_text.call_args_list[-1][0][0]
        assert "Captúralos" in last_reply or "más pendientes" in last_reply


# ---------------------------------------------------------------------------
# Callback — done (BR-DEC-04 / UOW-04 stub)
# ---------------------------------------------------------------------------

class TestCallbackDone:
    @pytest.mark.asyncio
    async def test_done_acks_button(self, adapter, task_repo):
        task = _save_pending_task(task_repo)

        # Populate cache via get_top3
        adapter._service.get_top3(USER_STR)

        update = _fake_callback_update(data=f"done:{task.task_id}")
        await adapter.callback_handler(update, MagicMock())

        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_reply_markup.assert_called_once_with(reply_markup=None)
        update.callback_query.message.reply_text.assert_called_once()
        reply = update.callback_query.message.reply_text.call_args[0][0]
        assert "Anotado" in reply or "✓" in reply

    @pytest.mark.asyncio
    async def test_done_invalidates_cache(self, adapter, task_repo):
        task = _save_pending_task(task_repo)
        r1 = adapter._service.get_top3(USER_STR)

        update = _fake_callback_update(data=f"done:{task.task_id}")
        await adapter.callback_handler(update, MagicMock())

        # Cache should be invalidated — next call recomputes
        adapter._service._task_repo.save  # ensure repo still valid
        r2 = adapter._service.get_top3(USER_STR)
        assert r1 is not r2


# ---------------------------------------------------------------------------
# Callback — clarify (BR-DEC-10)
# ---------------------------------------------------------------------------

class TestCallbackClarify:
    @pytest.mark.asyncio
    async def test_clarify_transitions_task_status(self, adapter, task_repo):
        task = _save_pending_task(task_repo)
        adapter._service.get_top3(USER_STR)  # populate cache

        update = _fake_callback_update(data=f"clarify:{task.task_id}")
        await adapter.callback_handler(update, MagicMock())

        saved = task_repo.get_by_id(USER_STR, task.task_id)
        assert saved.status == TaskStatus.NEEDS_CLARIFICATION

    @pytest.mark.asyncio
    async def test_clarify_sends_question(self, adapter, task_repo):
        task = _save_pending_task(task_repo)
        adapter._service.get_top3(USER_STR)

        update = _fake_callback_update(data=f"clarify:{task.task_id}")
        await adapter.callback_handler(update, MagicMock())

        update.callback_query.message.reply_text.assert_called_once()
        question = update.callback_query.message.reply_text.call_args[0][0]
        assert "?" in question or "necesitas" in question.lower()

    @pytest.mark.asyncio
    async def test_clarify_acks_button(self, adapter, task_repo):
        task = _save_pending_task(task_repo)
        adapter._service.get_top3(USER_STR)

        update = _fake_callback_update(data=f"clarify:{task.task_id}")
        await adapter.callback_handler(update, MagicMock())

        update.callback_query.answer.assert_called_once()

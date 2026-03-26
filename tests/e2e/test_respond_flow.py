"""E2E tests for UOW-04 Respond & State Transition.

Uses moto DynamoDB (via conftest) + MagicMock for Telegram objects.
Full flow: done/snooze/clarify through real repos and services.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.capture.infrastructure.dynamodb_event_repo import DynamoDBEventRepository
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.decision.application.decision_service import DecisionService
from ppai.decision.domain.scoring_engine import ScoringEngine
from ppai.decision.infrastructure.dynamodb_cycle_repo import DynamoDBCycleRepository
from ppai.push.infrastructure.cycle_event_repo import DynamoDBCycleEventRepository
from ppai.respond.application.response_service import ResponseService
from ppai.respond.infrastructure.dynamodb_interaction_event_repo import DynamoDBInteractionEventRepository
from ppai.respond.infrastructure.response_telegram_adapter import ResponseTelegramAdapter

USER_ID = 88888
USER_STR = str(USER_ID)
NOW = datetime(2026, 3, 26, 14, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def task_repo(dynamodb_resource):
    return DynamoDBTaskStateRepository(dynamodb_resource.Table("ppai-tasks"))


@pytest.fixture()
def event_repo(dynamodb_resource):
    return DynamoDBEventRepository(dynamodb_resource.Table("ppai-events"))


@pytest.fixture()
def interaction_event_repo(event_repo):
    return DynamoDBInteractionEventRepository(event_repo)


@pytest.fixture()
def cycle_repo(dynamodb_resource):
    return DynamoDBCycleRepository(dynamodb_resource.Table("ppai-cycles"))


@pytest.fixture()
def cycle_event_repo(dynamodb_resource):
    return DynamoDBCycleEventRepository(dynamodb_resource.Table("ppai-cycles"))


@pytest.fixture()
def decision_service(task_repo, cycle_repo):
    return DecisionService(
        task_repo=task_repo,
        cycle_repo=cycle_repo,
        scoring_engine=ScoringEngine(),
    )


@pytest.fixture()
def response_service(task_repo, interaction_event_repo, cycle_event_repo, cycle_repo, decision_service):
    return ResponseService(
        task_repo=task_repo,
        event_repo=interaction_event_repo,
        cycle_event_repo=cycle_event_repo,
        cycle_repo=cycle_repo,
        decision_service=decision_service,
    )


@pytest.fixture()
def adapter(response_service):
    return ResponseTelegramAdapter(response_service)


def _save_nudged_task(task_repo, user_id=USER_STR, task_id=None, snooze_count=0) -> TaskState:
    task = TaskState(
        user_id=user_id,
        original_text="Enviar propuesta",
        normalized_text="enviar propuesta",
        source_intent_id="i1",
        status=TaskStatus.NUDGED,
        snooze_count=snooze_count,
    )
    if task_id:
        task.task_id = task_id
    task_repo.save(task)
    return task


def _callback_update(data: str, user_id: int = USER_ID) -> MagicMock:
    update = MagicMock()
    update.callback_query = MagicMock()
    update.callback_query.from_user = MagicMock()
    update.callback_query.from_user.id = user_id
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    update.callback_query.message = MagicMock()
    update.callback_query.message.reply_text = AsyncMock()
    return update


def _text_update(text: str, user_id: int = USER_ID) -> MagicMock:
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.callback_query = None
    return update


# ---------------------------------------------------------------------------
# E2E: Done flow (press → confirm → DONE)
# ---------------------------------------------------------------------------

class TestDoneFlow:
    @pytest.mark.asyncio
    async def test_full_done_flow(self, adapter, task_repo, response_service):
        task = _save_nudged_task(task_repo)
        tid = task.task_id

        # Step 1: press Done → confirmation prompt
        update1 = _callback_update(f"done:{tid}")
        await adapter.callback_handler(update1, None)
        reply1 = update1.callback_query.message.reply_text.call_args[0][0]
        assert "Confirmas" in reply1

        # Step 2: confirm → DONE
        update2 = _callback_update(f"confirm_done:{tid}")
        await adapter.callback_handler(update2, None)
        reply2 = update2.callback_query.message.reply_text.call_args[0][0]
        assert "completada" in reply2.lower() or "Tarea" in reply2

        # Verify DB state
        saved = task_repo.get_by_id(USER_STR, tid)
        assert saved.status == TaskStatus.DONE
        assert saved.completed_at is not None


# ---------------------------------------------------------------------------
# E2E: Snooze flow
# ---------------------------------------------------------------------------

class TestSnoozeFlow:
    @pytest.mark.asyncio
    async def test_snooze_sets_cooldown(self, adapter, task_repo):
        task = _save_nudged_task(task_repo)
        tid = task.task_id

        update = _callback_update(f"snooze:{tid}")
        await adapter.callback_handler(update, None)

        saved = task_repo.get_by_id(USER_STR, tid)
        assert saved.status == TaskStatus.SNOOZED
        assert saved.snooze_count == 1
        assert saved.snoozed_until is not None

    @pytest.mark.asyncio
    async def test_snooze_available_after_cooldown(self, adapter, task_repo, decision_service):
        task = _save_nudged_task(task_repo)
        tid = task.task_id

        # Snooze the task
        update = _callback_update(f"snooze:{tid}")
        await adapter.callback_handler(update, None)

        # Manually expire cooldown
        saved = task_repo.get_by_id(USER_STR, tid)
        saved.snoozed_until = NOW - timedelta(minutes=1)
        task_repo.save(saved)

        # get_top3 should unsnoze and include it
        result = decision_service.get_top3(USER_STR, now=NOW)
        assert len(result.ranked_scores) >= 1


# ---------------------------------------------------------------------------
# E2E: Snooze limit → auto-clarify
# ---------------------------------------------------------------------------

class TestSnoozeLimitFlow:
    @pytest.mark.asyncio
    async def test_3_snoozes_then_auto_clarify(self, adapter, task_repo):
        task = _save_nudged_task(task_repo, snooze_count=3)
        tid = task.task_id

        update = _callback_update(f"snooze:{tid}")
        await adapter.callback_handler(update, None)

        reply = update.callback_query.message.reply_text.call_args[0][0]
        assert "3 veces" in reply

        saved = task_repo.get_by_id(USER_STR, tid)
        assert saved.status == TaskStatus.NEEDS_CLARIFICATION


# ---------------------------------------------------------------------------
# E2E: Clarify flow (press → question → text → PENDING)
# ---------------------------------------------------------------------------

class TestClarifyFlow:
    @pytest.mark.asyncio
    async def test_full_clarify_flow(self, adapter, task_repo):
        task = _save_nudged_task(task_repo)
        tid = task.task_id

        # Step 1: press Clarify
        update1 = _callback_update(f"clarify:{tid}")
        await adapter.callback_handler(update1, None)

        saved_mid = task_repo.get_by_id(USER_STR, tid)
        assert saved_mid.status == TaskStatus.NEEDS_CLARIFICATION

        # Step 2: send text response
        update2 = _text_update("Necesito cotizar primero")
        await adapter.clarify_response_handler(update2, None)

        saved_final = task_repo.get_by_id(USER_STR, tid)
        assert saved_final.status == TaskStatus.PENDING
        assert "Aclarado: Necesito cotizar primero" in saved_final.normalized_text
        assert saved_final.snooze_count == 0


# ---------------------------------------------------------------------------
# E2E: Idempotent double-press
# ---------------------------------------------------------------------------

class TestIdempotent:
    @pytest.mark.asyncio
    async def test_double_done_second_informative(self, adapter, task_repo):
        task = _save_nudged_task(task_repo)
        tid = task.task_id

        # First: confirm done
        await adapter.callback_handler(_callback_update(f"done:{tid}"), None)
        await adapter.callback_handler(_callback_update(f"confirm_done:{tid}"), None)

        # Second: press done again
        update = _callback_update(f"done:{tid}")
        await adapter.callback_handler(update, None)
        reply = update.callback_query.message.reply_text.call_args[0][0]
        assert "ya fue completada" in reply


# ---------------------------------------------------------------------------
# E2E: Authorization — other user rejected
# ---------------------------------------------------------------------------

class TestAuthorization:
    @pytest.mark.asyncio
    async def test_other_user_rejected(self, adapter, task_repo):
        task = _save_nudged_task(task_repo, user_id=USER_STR)
        tid = task.task_id

        # Different user tries to press Done
        other_user_id = 77777
        update = _callback_update(f"done:{tid}", user_id=other_user_id)
        await adapter.callback_handler(update, None)

        # Task not found for other user → "No encontré esa tarea"
        reply = update.callback_query.message.reply_text.call_args[0][0]
        assert "No encontré" in reply

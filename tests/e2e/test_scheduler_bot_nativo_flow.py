"""E2E tests for UOW-05 Scheduler Bot Nativo.

Exercises the real DynamoDB repositories plus the UOW-05 application wiring:
- daily start reminder
- daily end summary
- rescue suggestion
- zen activation / deactivation
- config persistence
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.push.application.daily_summary_builder import DailySummaryBuilder
from ppai.push.application.nudge_service import NudgeService
from ppai.push.application.rescue_evaluator import RescueEvaluator
from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import NudgeDispatchStatus
from ppai.push.infrastructure.config_telegram_adapter import ConfigTelegramAdapter
from ppai.push.infrastructure.cycle_event_repo import DynamoDBCycleEventRepository
from ppai.push.infrastructure.dynamodb_preferences_repo import DynamoDBPreferencesRepository
from ppai.push.infrastructure.zen_telegram_adapter import ZenTelegramAdapter

USER_ID = "501"
START_NOW = datetime(2026, 3, 27, 13, 0, tzinfo=timezone.utc)  # 08:00 Bogota
MID_NOW = datetime(2026, 3, 27, 17, 0, tzinfo=timezone.utc)    # 12:00 Bogota
END_NOW = datetime(2026, 3, 27, 23, 0, tzinfo=timezone.utc)    # 18:00 Bogota


class FakeDecisionService:
    def __init__(self, top3: Top3Result | None):
        self._top3 = top3

    def get_top3(self, user_id: str, now=None):
        if self._top3 is None:
            raise Exception("no top3")
        return self._top3


class FakeTelegramPort:
    def __init__(self, should_succeed: bool = True):
        self._should_succeed = should_succeed
        self.messages_sent: list[tuple[str, str]] = []
        self.nudges_sent: list[tuple[str, object]] = []

    def send_message(self, chat_id: str, text: str) -> bool:
        self.messages_sent.append((chat_id, text))
        return self._should_succeed

    def send_nudge(self, chat_id: str, message) -> bool:
        self.nudges_sent.append((chat_id, message))
        return self._should_succeed


@pytest.fixture()
def prefs_repo(dynamodb_resource):
    return DynamoDBPreferencesRepository(dynamodb_resource.Table("ppai-preferences"))


@pytest.fixture()
def cycle_event_repo(dynamodb_resource):
    return DynamoDBCycleEventRepository(dynamodb_resource.Table("ppai-cycles"))


@pytest.fixture()
def task_repo(dynamodb_resource):
    return DynamoDBTaskStateRepository(dynamodb_resource.Table("ppai-tasks"))


def _make_task(
    task_id: str,
    text: str,
    status: TaskStatus = TaskStatus.PENDING,
    completed_at: datetime | None = None,
) -> TaskState:
    return TaskState(
        user_id=USER_ID,
        original_text=text,
        normalized_text=text,
        source_intent_id=f"intent-{task_id}",
        status=status,
        task_id=task_id,
        completed_at=completed_at,
    )


def _make_top3(*task_ids: str) -> Top3Result:
    ranked_scores = tuple(
        PriorityScore(
            task_id=task_id,
            urgency_score=10 - i,
            age_score=5,
            snooze_score=0,
            total_score=15 - i,
            explanation="prioridad actual",
        )
        for i, task_id in enumerate(task_ids)
    )
    cycle = ExecutionCycle(user_id=USER_ID, date="2026-03-27")
    return Top3Result(cycle_id=cycle.cycle_id, user_id=USER_ID, ranked_scores=ranked_scores)


def _build_service(
    prefs_repo,
    cycle_event_repo,
    task_repo,
    telegram_port,
    top3: Top3Result | None,
    zen_manager: ZenSessionManager | None = None,
):
    return NudgeService(
        prefs_repo=prefs_repo,
        cycle_event_repo=cycle_event_repo,
        task_repo=task_repo,
        telegram_port=telegram_port,
        decision_service=FakeDecisionService(top3),
        zen_manager=zen_manager,
        daily_summary_builder=DailySummaryBuilder(task_repo),
        rescue_evaluator=RescueEvaluator(),
    )


def _make_update(user_id: str = USER_ID):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = int(user_id)
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


class TestSchedulerBotNativoFlow:
    def test_daily_start_sends_top3_message(
        self, prefs_repo, cycle_event_repo, task_repo
    ):
        task_repo.save(_make_task("t1", "Preparar propuesta"))
        task_repo.save(_make_task("t2", "Enviar invoice"))
        prefs_repo.save(UserNudgePreferences(user_id=USER_ID))

        telegram = FakeTelegramPort()
        service = _build_service(
            prefs_repo,
            cycle_event_repo,
            task_repo,
            telegram,
            _make_top3("t1", "t2"),
        )

        outcomes = service.run_tick([USER_ID], now=START_NOW)

        assert any(o.reason == "daily_start" and o.status == NudgeDispatchStatus.sent for o in outcomes)
        assert len(telegram.messages_sent) == 1
        assert "Top 3 para hoy" in telegram.messages_sent[0][1]
        assert "Preparar propuesta" in telegram.messages_sent[0][1]

    def test_daily_end_sends_detailed_summary(
        self, prefs_repo, cycle_event_repo, task_repo
    ):
        task_repo.save(
            _make_task("done-1", "Cerrar propuesta", TaskStatus.DONE, completed_at=END_NOW)
        )
        task_repo.save(_make_task("pending-1", "Llamar cliente", TaskStatus.PENDING))
        task_repo.save(_make_task("snoozed-1", "Actualizar CRM", TaskStatus.SNOOZED))
        prefs_repo.save(UserNudgePreferences(user_id=USER_ID))

        telegram = FakeTelegramPort()
        service = _build_service(
            prefs_repo,
            cycle_event_repo,
            task_repo,
            telegram,
            _make_top3("pending-1"),
        )

        outcomes = service.run_tick([USER_ID], now=END_NOW)

        assert any(o.reason == "daily_end" and o.status == NudgeDispatchStatus.sent for o in outcomes)
        summary_text = telegram.messages_sent[0][1]
        assert "Completadas (1)" in summary_text
        assert "Pendientes (1)" in summary_text
        assert "Pospuestas (1)" in summary_text
        assert "Cerrar propuesta" in summary_text

    def test_daily_end_triggers_rescue_for_dia_caido(
        self, prefs_repo, cycle_event_repo, task_repo
    ):
        task_repo.save(_make_task("pending-1", "Retomar landing", TaskStatus.PENDING))
        prefs_repo.save(UserNudgePreferences(user_id=USER_ID))

        telegram = FakeTelegramPort()
        service = _build_service(
            prefs_repo,
            cycle_event_repo,
            task_repo,
            telegram,
            _make_top3("pending-1"),
        )

        outcomes = service.run_tick([USER_ID], now=END_NOW)

        assert any(o.reason == "daily_end" for o in outcomes)
        message = telegram.messages_sent[0][1]
        assert "día difícil" in message.lower()
        assert "Dedícale solo 5 minutos" in message

    @pytest.mark.asyncio
    async def test_zen_activate_and_deactivate_via_command(
        self, prefs_repo, cycle_event_repo
    ):
        zen_manager = ZenSessionManager()
        adapter = ZenTelegramAdapter(prefs_repo, cycle_event_repo, zen_manager)

        update_on = _make_update()
        context_on = MagicMock()
        context_on.args = []
        await adapter.zen_handler(update_on, context_on)

        saved_prefs = prefs_repo.get(USER_ID)
        assert saved_prefs is not None
        assert saved_prefs.zen_active is True
        assert zen_manager.get(USER_ID) is not None

        update_off = _make_update()
        context_off = MagicMock()
        context_off.args = ["off"]
        await adapter.zen_handler(update_off, context_off)

        saved_prefs = prefs_repo.get(USER_ID)
        assert saved_prefs.zen_active is False
        assert zen_manager.get(USER_ID) is None

    def test_zen_auto_deactivates_after_reaching_cap(
        self, prefs_repo, cycle_event_repo, task_repo
    ):
        task_repo.save(_make_task("t1", "Escribir PRD", TaskStatus.PRIORITIZED))
        prefs = UserNudgePreferences(
            user_id=USER_ID,
            zen_active=True,
            zen_interval_minutes=10,
            zen_max_nudges=1,
        )
        prefs_repo.save(prefs)

        zen_manager = ZenSessionManager()
        zen_manager.activate(USER_ID, zen_max_nudges=1, zen_interval_minutes=10)
        zen_manager.record_nudge(USER_ID)

        telegram = FakeTelegramPort()
        service = _build_service(
            prefs_repo,
            cycle_event_repo,
            task_repo,
            telegram,
            _make_top3("t1"),
            zen_manager=zen_manager,
        )

        outcomes = service.run_tick([USER_ID], now=MID_NOW)

        assert outcomes == []
        updated_prefs = prefs_repo.get(USER_ID)
        assert updated_prefs.zen_active is False
        assert zen_manager.get(USER_ID) is None
        assert any("Modo zen completado" in text for _, text in telegram.messages_sent)

    def test_daily_start_is_idempotent_within_same_window(
        self, prefs_repo, cycle_event_repo, task_repo
    ):
        task_repo.save(_make_task("t1", "Preparar demo"))
        prefs_repo.save(UserNudgePreferences(user_id=USER_ID))

        telegram = FakeTelegramPort()
        service = _build_service(
            prefs_repo,
            cycle_event_repo,
            task_repo,
            telegram,
            _make_top3("t1"),
        )

        service.run_tick([USER_ID], now=START_NOW)
        service.run_tick([USER_ID], now=START_NOW)

        cycle = cycle_event_repo.get_active(USER_ID, START_NOW.date())
        assert cycle is not None
        assert cycle_event_repo.has_event_today(cycle.cycle_id, "DAILY_START_SENT") is True
        assert len(telegram.messages_sent) == 1

    @pytest.mark.asyncio
    async def test_config_inicio_y_cierre_are_persisted(
        self, prefs_repo
    ):
        adapter = ConfigTelegramAdapter(prefs_repo)

        update_start = _make_update()
        context_start = MagicMock()
        context_start.args = ["inicio", "09:15"]
        await adapter.config_handler(update_start, context_start)

        update_end = _make_update()
        context_end = MagicMock()
        context_end.args = ["cierre", "19:30"]
        await adapter.config_handler(update_end, context_end)

        saved = prefs_repo.get(USER_ID)
        assert saved.daily_start_time == "09:15"
        assert saved.daily_end_time == "19:30"

    @pytest.mark.asyncio
    async def test_config_motivacion_sanitizes_html_and_rejects_urls(
        self, prefs_repo
    ):
        adapter = ConfigTelegramAdapter(prefs_repo)

        update_ok = _make_update()
        context_ok = MagicMock()
        context_ok.args = ["motivacion", "<b>Hoy</b>", "sí", "se", "puede"]
        await adapter.config_handler(update_ok, context_ok)

        saved = prefs_repo.get(USER_ID)
        assert saved.motivational_message == "Hoy sí se puede"

        update_bad = _make_update()
        context_bad = MagicMock()
        context_bad.args = ["motivacion", "visita", "https://bad.test"]
        await adapter.config_handler(update_bad, context_bad)

        text = update_bad.message.reply_text.call_args[0][0]
        assert "URLs" in text

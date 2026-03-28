"""E2E tests for the push tick flow under the UOW-05 scheduler model.

Uses moto for DynamoDB and a mock TelegramPushPort to exercise the full
NudgeService stack against real repository implementations.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from ppai.capture.domain.entities import TaskState
from ppai.capture.domain.value_objects import TaskStatus
from ppai.capture.infrastructure.dynamodb_task_repo import DynamoDBTaskStateRepository
from ppai.decision.domain.entities import ExecutionCycle, PriorityScore, Top3Result
from ppai.decision.domain.value_objects import CycleStatus
from ppai.push.application.nudge_service import NudgeService
from ppai.push.application.zen_session_manager import ZenSessionManager
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.domain.value_objects import NudgeDispatchStatus
from ppai.push.infrastructure.cycle_event_repo import DynamoDBCycleEventRepository
from ppai.push.infrastructure.dynamodb_preferences_repo import DynamoDBPreferencesRepository

USER = "e2e-push-user-01"
NOW = datetime(2026, 3, 25, 17, 0, 0, tzinfo=timezone.utc)  # 17:00 UTC = 12:00 America/Bogota


def make_task(task_id: str = "t1", status: TaskStatus = TaskStatus.PRIORITIZED) -> TaskState:
    return TaskState(
        user_id=USER,
        original_text="Enviar propuesta al cliente",
        normalized_text="Enviar propuesta al cliente",
        source_intent_id="intent-1",
        status=status,
        task_id=task_id,
    )


def make_top3(task_id: str = "t1") -> Top3Result:
    score = PriorityScore(
        task_id=task_id,
        urgency_score=3,
        age_score=2,
        snooze_score=0,
        total_score=5,
        explanation="Alta urgencia",
    )
    return Top3Result(
        cycle_id="cycle-e2e",
        user_id=USER,
        ranked_scores=(score,),
    )


def empty_top3() -> Top3Result:
    return Top3Result(cycle_id="cycle-e2e", user_id=USER, ranked_scores=())


@pytest.fixture()
def prefs_repo(dynamodb_resource):
    return DynamoDBPreferencesRepository(dynamodb_resource.Table("ppai-preferences"))


@pytest.fixture()
def cycle_event_repo(dynamodb_resource):
    return DynamoDBCycleEventRepository(dynamodb_resource.Table("ppai-cycles"))


@pytest.fixture()
def task_repo(dynamodb_resource):
    return DynamoDBTaskStateRepository(dynamodb_resource.Table("ppai-tasks"))


def build_service(prefs_repo, cycle_event_repo, task_repo, telegram_mock, top3_result, prefs=None):
    decision_mock = MagicMock()
    decision_mock.get_top3.return_value = top3_result
    prefs = prefs or UserNudgePreferences(user_id=USER, zen_active=True)
    prefs_repo.save(prefs)
    zen_manager = ZenSessionManager()
    if prefs.zen_active:
        zen_manager.activate(
            user_id=USER,
            zen_max_nudges=prefs.zen_max_nudges,
            zen_interval_minutes=prefs.zen_interval_minutes,
        )
    return NudgeService(
        prefs_repo=prefs_repo,
        cycle_event_repo=cycle_event_repo,
        task_repo=task_repo,
        telegram_port=telegram_mock,
        decision_service=decision_mock,
        zen_manager=zen_manager,
    )


# ---------------------------------------------------------------------------
# Scenario 1: Tick without Top 3 → NUDGE_SKIPPED
# ---------------------------------------------------------------------------

class TestTickWithoutTop3:
    def test_outcome_is_skipped_no_top3(self, prefs_repo, cycle_event_repo, task_repo):
        telegram = MagicMock()
        svc = build_service(prefs_repo, cycle_event_repo, task_repo, telegram, empty_top3())

        outcomes = svc.run_tick([USER], now=NOW)

        assert len(outcomes) == 1
        assert outcomes[0].status == NudgeDispatchStatus.skipped_no_top3
        telegram.send_nudge.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 2: Tick with Top 3 → NUDGE_SENT, task → nudged
# ---------------------------------------------------------------------------

class TestTickWithTop3:
    def test_outcome_is_sent_and_task_transitions_to_nudged(
        self, prefs_repo, cycle_event_repo, task_repo
    ):
        task = make_task()
        task_repo.save(task)

        telegram = MagicMock()
        telegram.send_nudge.return_value = True

        svc = build_service(prefs_repo, cycle_event_repo, task_repo, telegram, make_top3(task.task_id))

        with patch("time.sleep"):  # skip retry delay
            outcomes = svc.run_tick([USER], now=NOW)

        assert outcomes[0].status == NudgeDispatchStatus.sent
        assert outcomes[0].task_id == task.task_id

        updated_task = task_repo.get_by_id(USER, task.task_id)
        assert updated_task.status == TaskStatus.NUDGED

    def test_nudge_sent_event_is_recorded(self, prefs_repo, cycle_event_repo, task_repo):
        task = make_task()
        task_repo.save(task)

        telegram = MagicMock()
        telegram.send_nudge.return_value = True

        svc = build_service(prefs_repo, cycle_event_repo, task_repo, telegram, make_top3(task.task_id))

        with patch("time.sleep"):
            outcomes = svc.run_tick([USER], now=NOW)

        cycle_id = outcomes[0].cycle_id
        count = cycle_event_repo.get_nudge_count(cycle_id)
        assert count == 1


# ---------------------------------------------------------------------------
# Scenario 3: Silence window active → NUDGE_SKIPPED
# ---------------------------------------------------------------------------

class TestSilenceWindowSkip:
    def test_zen_sent_during_silence_window_override(self, prefs_repo, cycle_event_repo, task_repo):
        # Silence 11:00 – 13:00 America/Bogota — NOW is 12:00 local, but zen overrides silence
        prefs = UserNudgePreferences(
            user_id=USER,
            silence_start="11:00",
            silence_end="13:00",
            zen_active=True,
        )

        task = make_task()
        task_repo.save(task)

        telegram = MagicMock()
        telegram.send_nudge.return_value = True
        svc = build_service(
            prefs_repo, cycle_event_repo, task_repo, telegram, make_top3(task.task_id), prefs=prefs
        )

        outcomes = svc.run_tick([USER], now=NOW)

        assert outcomes[0].status == NudgeDispatchStatus.sent
        telegram.send_nudge.assert_called_once()


# ---------------------------------------------------------------------------
# Scenario 4: Recent activity (<60 min) → NUDGE_SKIPPED
# ---------------------------------------------------------------------------

class TestRecentActivitySkip:
    def test_skipped_when_activity_within_60_minutes(
        self, prefs_repo, cycle_event_repo, task_repo
    ):
        task = make_task()
        task_repo.save(task)

        # Seed a cycle with a NUDGE_SENT event 30 minutes ago
        cycle = ExecutionCycle(user_id=USER, date="2026-03-25")
        cycle_event_repo.create(cycle)
        cycle_event_repo.record_nudge_event(
            cycle.cycle_id,
            "NUDGE_SENT",
            {"taskId": task.task_id},
        )

        telegram = MagicMock()
        svc = build_service(prefs_repo, cycle_event_repo, task_repo, telegram, make_top3(task.task_id))

        # NOW is after the event; event timestamp is set by record_nudge_event (current UTC)
        # Use a NOW far in the future enough that it's within 60 min of the event
        outcomes = svc.run_tick([USER], now=datetime.now(timezone.utc) + timedelta(minutes=10))

        # Filter to nudge-related outcomes (daily_start may also fire)
        activity_outcomes = [o for o in outcomes if o.reason == "recent_activity"]
        assert len(activity_outcomes) == 1
        assert activity_outcomes[0].status == NudgeDispatchStatus.skipped_activity
        telegram.send_nudge.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 5: Daily cap reached → NUDGE_SKIPPED
# ---------------------------------------------------------------------------

class TestDailyCapSkip:
    def test_skipped_when_daily_cap_reached(self, prefs_repo, cycle_event_repo, task_repo):
        prefs = UserNudgePreferences(user_id=USER, max_nudges_per_day=2, zen_active=True)

        task = make_task()
        task_repo.save(task)

        # Use NOW far enough in future to avoid recent_activity guard
        future_now = datetime.now(timezone.utc) + timedelta(hours=2)

        # Cycle date must match the date NudgeService resolves for future_now
        from zoneinfo import ZoneInfo
        local_date = future_now.astimezone(ZoneInfo(prefs.timezone)).strftime("%Y-%m-%d")
        cycle = ExecutionCycle(user_id=USER, date=local_date)
        cycle_event_repo.create(cycle)
        # Record 2 NUDGE_SENT events (= cap)
        for _ in range(2):
            cycle_event_repo.record_nudge_event(cycle.cycle_id, "NUDGE_SENT", {"taskId": "t0"})

        telegram = MagicMock()
        svc = build_service(
            prefs_repo, cycle_event_repo, task_repo, telegram, make_top3(task.task_id), prefs=prefs
        )

        outcomes = svc.run_tick([USER], now=future_now)

        assert outcomes[0].status == NudgeDispatchStatus.skipped_activity
        assert outcomes[0].reason == "daily_cap_reached"
        telegram.send_nudge.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 6: Re-engagement (>24h inactive) → sent with re-engagement tone
# ---------------------------------------------------------------------------

class TestReengagement:
    def test_reengagement_message_sent_after_24h_inactivity(
        self, prefs_repo, cycle_event_repo, task_repo
    ):
        task = make_task()
        task_repo.save(task)

        # Seed a cycle with an event >24h ago
        cycle = ExecutionCycle(user_id=USER, date="2026-03-24")
        cycle_event_repo.create(cycle)
        # Record old event by injecting directly
        old_ts = (NOW - timedelta(hours=25)).isoformat()
        cycle_event_repo._table.update_item(
            Key={"cycleId": cycle.cycle_id},
            UpdateExpression="SET nudgeEvents = list_append(if_not_exists(nudgeEvents, :empty), :evt)",
            ExpressionAttributeValues={
                ":evt": [{"eventType": "NUDGE_SENT", "timestamp": old_ts}],
                ":empty": [],
            },
        )

        telegram = MagicMock()
        telegram.send_nudge.return_value = True

        svc = build_service(prefs_repo, cycle_event_repo, task_repo, telegram, make_top3(task.task_id))

        with patch("time.sleep"):
            outcomes = svc.run_tick([USER], now=NOW)

        assert outcomes[0].status == NudgeDispatchStatus.sent
        call_args = telegram.send_nudge.call_args
        sent_message = call_args[0][1]
        # Re-engagement template uses "Cuando estés listo"
        assert "Cuando estés listo" in sent_message.task_title


# ---------------------------------------------------------------------------
# Scenario 7: Retry — first attempt fails, second succeeds → NUDGE_SENT
# ---------------------------------------------------------------------------

class TestRetrySuccess:
    def test_sent_on_second_attempt(self, prefs_repo, cycle_event_repo, task_repo):
        task = make_task()
        task_repo.save(task)

        telegram = MagicMock()
        telegram.send_nudge.side_effect = [False, True]  # fail, succeed

        svc = build_service(prefs_repo, cycle_event_repo, task_repo, telegram, make_top3(task.task_id))

        with patch("time.sleep"):
            outcomes = svc.run_tick([USER], now=NOW)

        assert outcomes[0].status == NudgeDispatchStatus.sent
        assert telegram.send_nudge.call_count == 2


# ---------------------------------------------------------------------------
# Scenario 8: Total failure (3 retries) → NUDGE_FAILED recorded
# ---------------------------------------------------------------------------

class TestRetryTotalFailure:
    def test_nudge_failed_after_3_attempts(self, prefs_repo, cycle_event_repo, task_repo):
        task = make_task()
        task_repo.save(task)

        telegram = MagicMock()
        telegram.send_nudge.return_value = False  # always fails

        svc = build_service(prefs_repo, cycle_event_repo, task_repo, telegram, make_top3(task.task_id))

        with patch("time.sleep"):
            outcomes = svc.run_tick([USER], now=NOW)

        assert outcomes[0].status == NudgeDispatchStatus.failed
        assert telegram.send_nudge.call_count == 3

        cycle_id = outcomes[0].cycle_id
        count = cycle_event_repo.get_nudge_count(cycle_id)
        assert count == 0  # no NUDGE_SENT — only NUDGE_FAILED recorded

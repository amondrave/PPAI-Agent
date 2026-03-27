"""Integration tests for UOW-03 DynamoDB repositories (moto mock).

Covers: DynamoDBPreferencesRepository + DynamoDBCycleEventRepository.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from botocore.exceptions import ClientError

from ppai.decision.domain.entities import ExecutionCycle
from ppai.decision.domain.value_objects import CycleStatus
from ppai.push.domain.entities import UserNudgePreferences
from ppai.push.infrastructure.cycle_event_repo import DynamoDBCycleEventRepository
from ppai.push.infrastructure.dynamodb_preferences_repo import DynamoDBPreferencesRepository

USER = "user-push-integ-01"
TODAY = date(2026, 3, 25)
NOW = datetime(2026, 3, 25, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def prefs_repo(dynamodb_resource):
    table = dynamodb_resource.Table("ppai-preferences")
    return DynamoDBPreferencesRepository(table)


@pytest.fixture()
def cycle_event_repo(dynamodb_resource):
    table = dynamodb_resource.Table("ppai-cycles")
    return DynamoDBCycleEventRepository(table)


def make_cycle(user_id: str = USER, for_date: date = TODAY) -> ExecutionCycle:
    return ExecutionCycle(
        user_id=user_id,
        date=for_date.strftime("%Y-%m-%d"),
        status=CycleStatus.ACTIVE,
        top3_task_ids=["t1", "t2", "t3"],
    )


# ---------------------------------------------------------------------------
# DynamoDBPreferencesRepository
# ---------------------------------------------------------------------------

class TestDynamoDBPreferencesRepository:
    def test_get_returns_none_if_not_exists(self, prefs_repo):
        result = prefs_repo.get("nonexistent-user")
        assert result is None

    def test_save_and_get_roundtrip(self, prefs_repo):
        prefs = UserNudgePreferences(
            user_id=USER,
            timezone="America/Bogota",
            max_nudges_per_day=3,
        )
        prefs_repo.save(prefs)

        found = prefs_repo.get(USER)
        assert found is not None
        assert found.user_id == USER
        assert found.timezone == "America/Bogota"
        assert found.max_nudges_per_day == 3
        assert found.silence_start is None
        assert found.silence_end is None

    def test_save_with_silence_window(self, prefs_repo):
        prefs = UserNudgePreferences(
            user_id=USER,
            silence_start="22:00",
            silence_end="08:00",
        )
        prefs_repo.save(prefs)

        found = prefs_repo.get(USER)
        assert found.silence_start == "22:00"
        assert found.silence_end == "08:00"
        assert found.has_silence_window() is True

    def test_save_updates_existing_preferences(self, prefs_repo):
        prefs = UserNudgePreferences(user_id=USER, max_nudges_per_day=3)
        prefs_repo.save(prefs)

        updated = UserNudgePreferences(user_id=USER, max_nudges_per_day=5)
        prefs_repo.save(updated)

        found = prefs_repo.get(USER)
        assert found.max_nudges_per_day == 5

    def test_defaults_applied_on_get(self, prefs_repo):
        # Save minimal item directly via underlying table to simulate legacy data
        prefs = UserNudgePreferences(user_id=USER)
        prefs_repo.save(prefs)

        found = prefs_repo.get(USER)
        assert found.timezone == "America/Bogota"
        assert found.max_nudges_per_day == 3

    # --- UOW-05 tests ---

    def test_save_and_get_uow05_fields(self, prefs_repo):
        prefs = UserNudgePreferences(
            user_id=USER,
            daily_start_time="09:00",
            daily_end_time="17:00",
            zen_active=True,
            zen_interval_minutes=10,
            zen_max_nudges=20,
            motivational_message="Vamos con todo!",
        )
        prefs_repo.save(prefs)

        found = prefs_repo.get(USER)
        assert found.daily_start_time == "09:00"
        assert found.daily_end_time == "17:00"
        assert found.zen_active is True
        assert found.zen_interval_minutes == 10
        assert found.zen_max_nudges == 20
        assert found.motivational_message == "Vamos con todo!"

    def test_get_all_returns_all_users(self, prefs_repo):
        prefs_repo.save(UserNudgePreferences(user_id="user-a"))
        prefs_repo.save(UserNudgePreferences(user_id="user-b"))

        all_prefs = prefs_repo.get_all()
        user_ids = {p.user_id for p in all_prefs}
        assert "user-a" in user_ids
        assert "user-b" in user_ids

    def test_uow05_defaults_for_legacy_data(self, prefs_repo):
        # Simulate legacy item without UOW-05 fields
        prefs_repo._table.put_item(Item={
            "userId": "legacy-user",
            "timezone": "America/Bogota",
            "maxNudgesPerDay": 3,
        })
        found = prefs_repo.get("legacy-user")
        assert found.daily_start_time == "08:00"
        assert found.daily_end_time == "18:00"
        assert found.zen_active is False
        assert found.zen_interval_minutes == 15
        assert found.zen_max_nudges == 10
        assert found.motivational_message == "A darle con todo hoy"


# ---------------------------------------------------------------------------
# DynamoDBCycleEventRepository
# ---------------------------------------------------------------------------

class TestDynamoDBCycleEventRepository:
    def test_get_active_returns_none_if_not_exists(self, cycle_event_repo):
        result = cycle_event_repo.get_active("nonexistent-user", TODAY)
        assert result is None

    def test_create_and_get_active(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)

        found = cycle_event_repo.get_active(USER, TODAY)
        assert found is not None
        assert found.cycle_id == cycle.cycle_id
        assert found.user_id == USER
        assert found.top3_task_ids == ["t1", "t2", "t3"]

    def test_create_fails_if_cycle_already_exists(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)

        duplicate = ExecutionCycle(
            cycle_id=cycle.cycle_id,
            user_id=USER,
            date=TODAY.strftime("%Y-%m-%d"),
        )
        with pytest.raises(ClientError) as exc_info:
            cycle_event_repo.create(duplicate)
        assert exc_info.value.response["Error"]["Code"] == "ConditionalCheckFailedException"

    def test_record_nudge_event_nudge_scheduled(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)
        cycle_event_repo.record_nudge_event(
            cycle.cycle_id, "NUDGE_SCHEDULED", {"taskId": "t1"}
        )

        count = cycle_event_repo.get_nudge_count(cycle.cycle_id)
        assert count == 0  # NUDGE_SCHEDULED does not count

    def test_record_nudge_event_nudge_sent(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)
        cycle_event_repo.record_nudge_event(
            cycle.cycle_id, "NUDGE_SENT", {"taskId": "t1"}
        )

        count = cycle_event_repo.get_nudge_count(cycle.cycle_id)
        assert count == 1

    def test_record_nudge_event_nudge_failed(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)
        cycle_event_repo.record_nudge_event(
            cycle.cycle_id, "NUDGE_FAILED", {"taskId": "t1", "attempts": "3"}
        )

        count = cycle_event_repo.get_nudge_count(cycle.cycle_id)
        assert count == 0  # NUDGE_FAILED does not count

    def test_get_nudge_count_counts_only_sent(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)
        cycle_event_repo.record_nudge_event(cycle.cycle_id, "NUDGE_SCHEDULED", {"taskId": "t1"})
        cycle_event_repo.record_nudge_event(cycle.cycle_id, "NUDGE_SENT", {"taskId": "t1"})
        cycle_event_repo.record_nudge_event(cycle.cycle_id, "NUDGE_SENT", {"taskId": "t2"})
        cycle_event_repo.record_nudge_event(cycle.cycle_id, "NUDGE_FAILED", {"taskId": "t3"})

        count = cycle_event_repo.get_nudge_count(cycle.cycle_id)
        assert count == 2

    def test_get_last_activity_at_returns_none_for_new_user(self, cycle_event_repo):
        result = cycle_event_repo.get_last_activity_at("no-activity-user")
        assert result is None

    # --- UOW-05 tests ---

    def test_has_event_today_true(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)
        cycle_event_repo.record_nudge_event(cycle.cycle_id, "DAILY_START_SENT", {"sent_at": "2026-03-25T14:00:00"})
        assert cycle_event_repo.has_event_today(cycle.cycle_id, "DAILY_START_SENT") is True

    def test_has_event_today_false(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)
        assert cycle_event_repo.has_event_today(cycle.cycle_id, "DAILY_START_SENT") is False

    def test_has_event_today_with_multiple_events(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)
        cycle_event_repo.record_nudge_event(cycle.cycle_id, "NUDGE_SENT", {"taskId": "t1"})
        cycle_event_repo.record_nudge_event(cycle.cycle_id, "DAILY_END_SENT", {"sent_at": "2026-03-25T23:00:00"})
        assert cycle_event_repo.has_event_today(cycle.cycle_id, "DAILY_END_SENT") is True
        assert cycle_event_repo.has_event_today(cycle.cycle_id, "RESCUE_TRIGGERED") is False

    def test_get_last_activity_at_returns_most_recent_timestamp(self, cycle_event_repo):
        cycle = make_cycle()
        cycle_event_repo.create(cycle)
        cycle_event_repo.record_nudge_event(cycle.cycle_id, "NUDGE_SENT", {"taskId": "t1"})
        cycle_event_repo.record_nudge_event(cycle.cycle_id, "NUDGE_SENT", {"taskId": "t2"})

        result = cycle_event_repo.get_last_activity_at(USER)
        assert result is not None
        assert isinstance(result, datetime)

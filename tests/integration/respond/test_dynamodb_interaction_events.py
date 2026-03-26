"""Integration tests for InteractionEvent persistence in ppai-events (Step 10 — US-08)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from ppai.capture.domain.entities import CaptureEvent
from ppai.capture.infrastructure.dynamodb_event_repo import DynamoDBEventRepository
from ppai.respond.domain.entities import InteractionEvent
from ppai.respond.infrastructure.dynamodb_interaction_event_repo import DynamoDBInteractionEventRepository

_TTL_90_DAYS = 7_776_000


@pytest.fixture()
def event_repo(dynamodb_resource):
    table = dynamodb_resource.Table("ppai-events")
    return DynamoDBEventRepository(table)


@pytest.fixture()
def interaction_repo(event_repo):
    return DynamoDBInteractionEventRepository(event_repo)


@pytest.fixture()
def events_table(dynamodb_resource):
    return dynamodb_resource.Table("ppai-events")


class TestDynamoDBInteractionEvents:
    def test_append_interaction_persists_with_ttl(self, interaction_repo, events_table):
        now = datetime(2026, 3, 26, 14, 0, 0, tzinfo=timezone.utc)
        event = InteractionEvent(
            user_id="u1",
            task_id="t1",
            event_type="TASK_DONE",
            correlation_id="cycle-1",
            metadata={"previous_status": "nudged"},
            timestamp=now,
        )
        interaction_repo.append(event)

        # Read back from raw table
        resp = events_table.scan()
        items = [i for i in resp["Items"] if i.get("eventType") == "TASK_DONE"]
        assert len(items) == 1

        item = items[0]
        assert item["userId"] == "u1"
        assert item["taskId"] == "t1"
        assert item["correlationId"] == "cycle-1"
        assert item["eventType"] == "TASK_DONE"

        # TTL = timestamp + 90 days
        expected_ttl = int(now.timestamp()) + _TTL_90_DAYS
        assert int(item["ttl"]) == expected_ttl

        # metadata persisted as JSON string
        meta = json.loads(item["metadata"])
        assert meta["previous_status"] == "nudged"

    def test_ttl_value_correct_90_days(self, interaction_repo, events_table):
        now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        event = InteractionEvent(
            user_id="u1",
            task_id="t2",
            event_type="TASK_SNOOZED",
            correlation_id="cycle-2",
            timestamp=now,
        )
        interaction_repo.append(event)

        resp = events_table.scan()
        items = [i for i in resp["Items"] if i.get("eventType") == "TASK_SNOOZED"]
        item = items[0]

        expected_ttl = int(now.timestamp()) + _TTL_90_DAYS
        assert int(item["ttl"]) == expected_ttl

    def test_interaction_and_capture_events_coexist(self, event_repo, interaction_repo, events_table):
        """InteractionEvent and CaptureEvent coexist in the same ppai-events table."""
        # Write a CaptureEvent
        capture_event = CaptureEvent(
            task_id="t1",
            user_id="u1",
            original_text="comprar leche",
            correlation_id="corr-1",
        )
        event_repo.append(capture_event)

        # Write an InteractionEvent
        interaction_event = InteractionEvent(
            user_id="u1",
            task_id="t1",
            event_type="TASK_DONE",
            correlation_id="cycle-1",
        )
        interaction_repo.append(interaction_event)

        # Both should be in the table
        resp = events_table.scan()
        event_types = {i["eventType"] for i in resp["Items"]}
        assert "INTENT_CAPTURED" in event_types
        assert "TASK_DONE" in event_types

    def test_interaction_event_without_metadata(self, interaction_repo, events_table):
        event = InteractionEvent(
            user_id="u1",
            task_id="t3",
            event_type="TASK_CLARIFIED",
            correlation_id="cycle-3",
        )
        interaction_repo.append(event)

        resp = events_table.scan()
        items = [i for i in resp["Items"] if i.get("eventType") == "TASK_CLARIFIED"]
        item = items[0]
        assert "metadata" not in item  # empty metadata is not persisted

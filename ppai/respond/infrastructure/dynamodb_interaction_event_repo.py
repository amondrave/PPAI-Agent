"""Adapter that satisfies InteractionEventRepository Protocol using DynamoDBEventRepository."""
from __future__ import annotations

from ppai.capture.infrastructure.dynamodb_event_repo import DynamoDBEventRepository
from ppai.respond.domain.entities import InteractionEvent


class DynamoDBInteractionEventRepository:
    """Wraps DynamoDBEventRepository to provide the InteractionEventRepository Protocol."""

    def __init__(self, event_repo: DynamoDBEventRepository) -> None:
        self._repo = event_repo

    def append(self, event: InteractionEvent) -> None:
        self._repo.append_interaction(event)

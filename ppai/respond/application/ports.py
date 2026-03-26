from __future__ import annotations

from typing import Protocol, runtime_checkable

from ppai.respond.domain.entities import InteractionEvent


@runtime_checkable
class InteractionEventRepository(Protocol):
    """Port for recording interaction events (done, snooze, clarify) in ppai-events."""

    def append(self, event: InteractionEvent) -> None:
        """Persist an interaction event. TTL managed by infrastructure layer."""
        ...

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ppai.capture.domain.value_objects import TaskStatus
from ppai.shared.domain.base_entity import generate_id
from ppai.respond.domain.value_objects import ResponseAction


@dataclass
class InteractionEvent:
    user_id: str
    task_id: str
    event_type: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=generate_id)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TransitionResult:
    success: bool
    task_id: str
    action: ResponseAction
    message: str
    requires_confirmation: bool = False
    previous_status: TaskStatus | None = None
    new_status: TaskStatus | None = None

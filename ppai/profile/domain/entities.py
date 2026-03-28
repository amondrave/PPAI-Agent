from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import Optional

from ppai.profile.domain.value_objects import CommunicationStyle, WeekendMode


@dataclass
class UserProfile:
    user_id: str
    name: str = ""
    occupation: str = ""
    work_start: Optional[time] = None
    work_end: Optional[time] = None
    protected_blocks: list[dict] = field(default_factory=list)
    communication_style: CommunicationStyle = CommunicationStyle.GENTLE
    timezone: str = "America/Bogota"
    days_off: list[str] = field(default_factory=list)
    holidays_country: Optional[str] = None
    weekend_mode: WeekendMode = WeekendMode.DESCANSO
    onboarding_completed: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

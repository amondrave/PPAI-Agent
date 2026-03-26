from datetime import timedelta
from enum import StrEnum


class ResponseAction(StrEnum):
    DONE = "done"
    SNOOZE = "snooze"
    CLARIFY = "clarify"


MAX_SNOOZE_COUNT = 3
SNOOZE_COOLDOWN = timedelta(hours=1)

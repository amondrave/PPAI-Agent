from enum import StrEnum


class CommunicationStyle(StrEnum):
    GENTLE = "gentle"
    DIRECT = "direct"
    CONFRONTATIONAL = "confrontational"


class WeekendMode(StrEnum):
    DESCANSO = "descanso"
    PERSONAL = "personal"
    MIXTO = "mixto"


class OnboardingStep(StrEnum):
    NAME = "name"
    OCCUPATION = "occupation"
    WORK_START = "work_start"
    WORK_END = "work_end"
    PROTECTED_BLOCKS = "protected_blocks"
    COMMUNICATION_STYLE = "communication_style"
    CONFIRM = "confirm"

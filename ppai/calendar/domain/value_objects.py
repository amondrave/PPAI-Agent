from __future__ import annotations

from enum import StrEnum


class TaskCategory(StrEnum):
    WORK = "work"
    PERSONAL = "personal"
    LEARNING = "learning"
    HEALTH = "health"
    SOCIAL = "social"
    ERRAND = "errand"


class BlockStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


CATEGORY_KEYWORDS: dict[TaskCategory, list[str]] = {
    TaskCategory.WORK: [
        "HU", "sprint", "código", "deploy", "merge", "PR", "bug",
        "API", "feature", "release", "jira", "ticket",
    ],
    TaskCategory.SOCIAL: [
        "llamar", "mamá", "papá", "amigo", "cena", "cumpleaños",
        "reunión social",
    ],
    TaskCategory.LEARNING: [
        "leer", "curso", "estudiar", "tutorial", "libro", "aprender",
    ],
    TaskCategory.HEALTH: [
        "gym", "correr", "médico", "doctor", "ejercicio", "yoga", "dentista",
    ],
    TaskCategory.ERRAND: [
        "pagar", "comprar", "trámite", "banco", "supermercado", "recoger",
    ],
}

DEFAULT_ESTIMATED_MINUTES: int = 30
BLOCK_BUFFER_MINUTES: int = 10

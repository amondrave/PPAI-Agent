from __future__ import annotations

import re

from ppai.calendar.domain.value_objects import (
    CATEGORY_KEYWORDS,
    DEFAULT_ESTIMATED_MINUTES,
    TaskCategory,
)

_TIME_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(\d+)\s*min", re.IGNORECASE), "minutes"),
    (re.compile(r"(\d+)\s*h(?:oras?)?", re.IGNORECASE), "hours"),
]

_HASHTAG_CATEGORY_MAP: dict[str, TaskCategory] = {
    "#work": TaskCategory.WORK,
    "#personal": TaskCategory.PERSONAL,
    "#learning": TaskCategory.LEARNING,
    "#health": TaskCategory.HEALTH,
    "#social": TaskCategory.SOCIAL,
    "#errand": TaskCategory.ERRAND,
}


class CategoryClassifier:
    """Classifies task text into a category and estimates duration."""

    def classify(self, text: str, tags: list[str] | None = None) -> TaskCategory:
        """
        Classify text into a TaskCategory.
        Priority: hashtag override > keyword matching > fallback (personal).
        """
        # Check hashtag override in tags
        if tags:
            for tag in tags:
                tag_lower = f"#{tag.lower()}" if not tag.startswith("#") else tag.lower()
                if tag_lower in _HASHTAG_CATEGORY_MAP:
                    return _HASHTAG_CATEGORY_MAP[tag_lower]

        # Check hashtag override in text
        for hashtag, category in _HASHTAG_CATEGORY_MAP.items():
            if hashtag in text.lower():
                return category

        # Keyword matching
        text_lower = text.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return category

        # Fallback
        return TaskCategory.PERSONAL

    def estimate_minutes(self, text: str) -> int:
        """
        Extract time estimate from text.
        Looks for patterns like '30min', '1h', '2 horas'.
        Returns DEFAULT_ESTIMATED_MINUTES if no pattern found.
        """
        for pattern, unit in _TIME_PATTERNS:
            match = pattern.search(text)
            if match:
                value = int(match.group(1))
                if unit == "hours":
                    return value * 60
                return value

        return DEFAULT_ESTIMATED_MINUTES

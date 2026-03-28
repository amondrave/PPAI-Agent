"""ER4 — Domain entities for LLM intelligence layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaskAnalysis:
    """Result of LLM-based task analysis (HU-R4.1)."""

    title: str
    category: str
    estimated_minutes: int
    urgency: str  # "high", "medium", "low"
    context: str = ""


@dataclass
class MessageRequest:
    """Input for LLM message generation (HU-R4.2)."""

    user_name: str
    communication_style: str
    occupation: str
    top3_tasks: list[str] = field(default_factory=list)
    completed_today: int = 0
    pending_today: int = 0
    snoozed_today: int = 0
    blocks_completed: int = 0
    blocks_planned: int = 0
    yesterday_completed: int = 0
    stuck_task: Optional[str] = None


@dataclass
class FrictionAnalysis:
    """Result of LLM friction analysis (HU-R4.3)."""

    diagnosis: str
    strategies: list[str]
    micro_action: str


@dataclass
class WeeklyInsight:
    """Result of LLM weekly report enrichment (HU-R4.4)."""

    what_went_well: str
    problematic_pattern: str
    suggestion: str
    question: str

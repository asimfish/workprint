"""Data models shared across collectors, miners, and generators."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TraceType(str, Enum):
    SHELL = "shell"
    GIT_COMMIT = "git_commit"
    NOTE = "note"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Trace:
    """A single raw behavioral trace from any source."""
    type: TraceType
    content: str
    timestamp: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
        }


@dataclass
class BehaviorAtom:
    """Minimal unit of behavior extracted from a trace."""
    verb: str            # what was done (run, commit, write, use)
    subject: str         # what it was done to (pytest, main.py, docker)
    context: str = ""    # surrounding situation
    source_trace: Trace | None = None
    timestamp: datetime | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class Evidence:
    """Concrete instance backing a pattern."""
    description: str
    timestamp: datetime | None = None
    raw: str = ""

    def format(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d") if self.timestamp else "unknown"
        return f"- {ts}: {self.description}"


@dataclass
class BehaviorPattern:
    """A recurring pattern distilled from multiple behavioral atoms."""
    name: str
    description: str
    pattern_type: str           # workflow | decision | style | preference | tool
    confidence: ConfidenceLevel
    evidence: list[Evidence] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    anti_pattern: bool = False  # True = pattern of what they avoid

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def date_range(self) -> str:
        dates = [e.timestamp for e in self.evidence if e.timestamp]
        if not dates:
            return "unknown"
        first = min(dates).strftime("%Y-%m-%d")
        last = max(dates).strftime("%Y-%m-%d")
        return f"{first} — {last}"


@dataclass
class WorkflowPattern:
    """An ordered sequence of steps that appears repeatedly."""
    name: str
    description: str
    steps: list[str]
    triggers: list[str] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    occurrence_count: int = 0

    @property
    def confidence_from_count(self) -> ConfidenceLevel:
        if self.occurrence_count >= 10:
            return ConfidenceLevel.HIGH
        if self.occurrence_count >= 3:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW


@dataclass
class WorkprintProfile:
    """The final distilled behavioral profile for a user."""
    name: str
    display_name: str
    total_traces: int
    date_range: str
    patterns: list[BehaviorPattern] = field(default_factory=list)
    workflows: list[WorkflowPattern] = field(default_factory=list)
    tool_preferences: dict[str, int] = field(default_factory=dict)
    language_preferences: dict[str, int] = field(default_factory=dict)
    style_notes: list[str] = field(default_factory=list)
    honest_limits: list[str] = field(default_factory=list)

    @property
    def high_confidence_patterns(self) -> list[BehaviorPattern]:
        return [p for p in self.patterns if p.confidence == ConfidenceLevel.HIGH]

    @property
    def anti_patterns(self) -> list[BehaviorPattern]:
        return [p for p in self.patterns if p.anti_pattern]

    @property
    def behavioral_patterns(self) -> list[BehaviorPattern]:
        return [p for p in self.patterns if not p.anti_pattern]

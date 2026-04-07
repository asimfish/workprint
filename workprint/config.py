"""Workprint configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WorkprintConfig:
    name: str = "workprint"
    display_name: str = ""
    shell_history_paths: list[Path] = field(default_factory=list)
    git_dirs: list[Path] = field(default_factory=list)
    note_dirs: list[Path] = field(default_factory=list)
    confidence_threshold: str = "low"   # low | medium | high
    max_evidence_per_pattern: int = 5   # shown in output
    include_anti_patterns: bool = True
    days_limit: int | None = 90         # only analyze traces from last N days

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.name

    @classmethod
    def auto_detect(cls) -> "WorkprintConfig":
        """Detect common trace sources on the current machine."""
        cfg = cls()
        for candidate in [
            Path.home() / ".zsh_history",
            Path.home() / ".bash_history",
        ]:
            if candidate.exists():
                cfg.shell_history_paths.append(candidate)
        return cfg

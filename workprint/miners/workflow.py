"""Workflow miner — detects ordered sequences that appear repeatedly.

Uses a sliding-window approach over shell history to find common command chains.
"""

from __future__ import annotations

from collections import Counter
from itertools import islice

from workprint.models import (
    ConfidenceLevel,
    Trace,
    TraceType,
    WorkflowPattern,
)


def _base(cmd: str) -> str:
    """Reduce command to its verb (first word)."""
    return cmd.split()[0] if cmd.split() else cmd


def _window(iterable, n: int):
    """Sliding window generator."""
    it = iter(iterable)
    current = list(islice(it, n))
    if len(current) == n:
        yield tuple(current)
    for item in it:
        current.append(item)
        current.pop(0)
        yield tuple(current)


class WorkflowMiner:
    """Finds repeated command sequences in shell history."""

    def __init__(self, traces: list[Trace], min_occurrences: int = 3):
        self.shell_traces = [t for t in traces if t.type == TraceType.SHELL]
        self.min_occurrences = min_occurrences

    # ------------------------------------------------------------------
    def mine(self) -> list[WorkflowPattern]:
        if not self.shell_traces:
            return []

        bases = [_base(t.content) for t in self.shell_traces]
        patterns: list[WorkflowPattern] = []

        # 2- and 3-step sequences
        for window_size in (2, 3):
            counter: Counter = Counter()
            for w in _window(bases, window_size):
                if len(set(w)) == window_size:   # no repetition within window
                    counter[w] += 1

            for seq, count in counter.most_common(10):
                if count < self.min_occurrences:
                    break
                wp = self._describe_sequence(seq, count)
                if wp:
                    patterns.append(wp)

        # Dedup: remove 2-step sequences that are subsets of a 3-step one
        patterns = self._dedup(patterns)
        return patterns[:8]

    # ------------------------------------------------------------------
    def _describe_sequence(self, seq: tuple[str, ...], count: int) -> WorkflowPattern | None:
        known = _KNOWN_WORKFLOWS.get(seq)
        if known:
            return WorkflowPattern(
                name=known["name"],
                description=known["description"],
                steps=list(seq),
                triggers=known.get("triggers", []),
                confidence=ConfidenceLevel.HIGH if count >= 10 else ConfidenceLevel.MEDIUM,
                occurrence_count=count,
            )

        # Generic: unknown sequence still worth noting if frequent enough
        if count >= 5:
            steps_str = " → ".join(f"`{s}`" for s in seq)
            return WorkflowPattern(
                name=f"Common sequence: {steps_str}",
                description=f"Runs {steps_str} together {count} times.",
                steps=list(seq),
                confidence=ConfidenceLevel.LOW,
                occurrence_count=count,
            )
        return None

    @staticmethod
    def _dedup(patterns: list[WorkflowPattern]) -> list[WorkflowPattern]:
        three_step_steps = {tuple(p.steps) for p in patterns if len(p.steps) == 3}
        result = []
        for p in patterns:
            if len(p.steps) == 2:
                # skip 2-step if it's a prefix of a known 3-step
                is_prefix = any(
                    three[:2] == tuple(p.steps) for three in three_step_steps
                )
                if is_prefix:
                    continue
            result.append(p)
        return result


# ---------------------------------------------------------------------------
# Named workflow library
# ---------------------------------------------------------------------------

_KNOWN_WORKFLOWS: dict[tuple[str, ...], dict] = {
    ("git", "pytest"): {
        "name": "Test-before-commit workflow",
        "description": "Runs tests immediately after git operations, ensuring commits don't break the build.",
        "triggers": ["Before staging changes", "Before pushing"],
    },
    ("pytest", "git"): {
        "name": "Test-then-commit workflow",
        "description": "Tests pass first, then commits — strong quality discipline.",
        "triggers": ["After implementing a feature"],
    },
    ("git", "ruff", "pytest"): {
        "name": "Lint-then-test before commit",
        "description": "Full quality gate: lint → test → commit. Thorough discipline.",
        "triggers": ["Before submitting work"],
    },
    ("ruff", "pytest"): {
        "name": "Lint-then-test",
        "description": "Runs linter before tests — catches syntax issues early.",
        "triggers": ["After editing Python files"],
    },
    ("docker", "pytest"): {
        "name": "Container-first testing",
        "description": "Runs tests inside/against Docker, suggests containerized workflow.",
        "triggers": ["Integration testing"],
    },
    ("npm", "git"): {
        "name": "Build-then-commit",
        "description": "Builds the project before committing — ensures no broken builds land.",
        "triggers": ["After frontend changes"],
    },
    ("pnpm", "git"): {
        "name": "Build-then-commit (pnpm)",
        "description": "pnpm build → git commit discipline.",
        "triggers": ["After frontend changes"],
    },
    ("git", "git"): {
        "name": "Frequent git operations",
        "description": "Runs git commands in rapid succession — common for rebasing, status-checking workflow.",
        "triggers": ["Branch management", "Review workflow"],
    },
    ("cd", "git"): {
        "name": "Navigate-then-git",
        "description": "Changes into a project directory and immediately does git work.",
        "triggers": ["Switching between projects"],
    },
    ("uvicorn", "pytest"): {
        "name": "Dev server → test cycle",
        "description": "Starts server, then runs tests — integration testing pattern.",
        "triggers": ["API development"],
    },
}

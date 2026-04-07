"""Statistical pattern miner — extracts BehaviorPatterns from collected Traces.

No ML, no API calls. Pure frequency analysis + heuristics.
Each pattern is backed by concrete evidence from real traces.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime

from workprint.models import (
    BehaviorAtom,
    BehaviorPattern,
    ConfidenceLevel,
    Evidence,
    Trace,
    TraceType,
)


# ---------------------------------------------------------------------------
# Shell command taxonomy
# ---------------------------------------------------------------------------

# Each group maps to a list of command prefixes (matched against full command string).
# More specific entries take priority — a command matches only the FIRST group that claims it.
_TOOL_GROUPS: dict[str, list[str]] = {
    "test": [
        "pytest", "jest", "vitest", "go test", "cargo test",
        "npm test", "npm run test", "pnpm test", "pnpm run test",
    ],
    "lint": [
        "ruff", "eslint", "pylint", "flake8", "mypy", "black", "prettier",
        "npm run lint", "pnpm run lint",
    ],
    "build": [
        "make", "cargo build", "go build",
        "npm run build", "pnpm build", "pnpm run build", "tsc",
    ],
    "container": ["docker", "podman", "docker-compose", "kubectl", "helm"],
    "git": ["git"],
    "package": ["pip", "pip3", "uv pip", "uv add", "npm install", "npm i ", "pnpm install", "pnpm add", "yarn add", "cargo add", "go get"],
    "editor": ["vim", "nvim", "nano", "code", "cursor"],
    "search": ["grep", "rg ", "ag ", "fd ", "find "],
    "devserver": ["uvicorn", "fastapi dev", "flask run", "node ", "bun run", "deno run"],
}

_COMMIT_TYPE_LABELS = {
    "feat": "feature development",
    "fix": "bug fixing",
    "refactor": "code refactoring",
    "docs": "documentation",
    "test": "test writing",
    "chore": "maintenance",
    "perf": "performance optimization",
    "ci": "CI/CD work",
}


class PatternMiner:
    """Mines behavioral patterns from raw traces."""

    def __init__(self, traces: list[Trace]):
        self.traces = traces
        self._shell = [t for t in traces if t.type == TraceType.SHELL]
        self._commits = [t for t in traces if t.type == TraceType.GIT_COMMIT]
        self._notes = [t for t in traces if t.type == TraceType.NOTE]

    # ------------------------------------------------------------------
    def mine(self) -> list[BehaviorPattern]:
        patterns: list[BehaviorPattern] = []
        patterns.extend(self._mine_tool_preferences())
        patterns.extend(self._mine_commit_style())
        patterns.extend(self._mine_command_habits())
        patterns.extend(self._mine_language_preferences())
        patterns.extend(self._mine_testing_behavior())
        patterns.extend(self._mine_anti_patterns())
        return patterns

    # ------------------------------------------------------------------
    # Tool preference patterns
    # ------------------------------------------------------------------

    def _mine_tool_preferences(self) -> list[BehaviorPattern]:
        if not self._shell:
            return []

        group_counts: dict[str, list[Trace]] = defaultdict(list)
        for t in self._shell:
            cmd = t.content.strip()
            # match against first group whose prefix matches (priority order)
            for group, prefixes in _TOOL_GROUPS.items():
                if any(cmd == p or cmd.startswith(p + " ") or cmd.startswith(p.split()[0] + " ")
                       and p.split()[0] == cmd.split()[0] and len(p.split()) == 1
                       for p in prefixes):
                    matched = next(
                        (p for p in prefixes
                         if cmd == p or cmd.startswith(p + " ")),
                        None,
                    )
                    if matched or any(cmd.split()[0] == p for p in prefixes if " " not in p):
                        group_counts[group].append(t)
                        break   # each trace goes to at most one group

        patterns: list[BehaviorPattern] = []
        for group, group_traces in group_counts.items():
            if len(group_traces) < 3:
                continue
            # find the most-used prefix within group
            prefix_counter: Counter = Counter()
            for t in group_traces:
                for p in _TOOL_GROUPS[group]:
                    cmd = t.content.strip()
                    if cmd == p or cmd.startswith(p + " "):
                        prefix_counter[p] += 1
                        break
                else:
                    prefix_counter[t.content.split()[0]] += 1
            top_tool, top_count = prefix_counter.most_common(1)[0]

            evidence = [
                Evidence(
                    description=f"`{t.content[:80]}`",
                    timestamp=t.timestamp,
                    raw=t.content,
                )
                for t in group_traces[-5:]
            ]
            patterns.append(BehaviorPattern(
                name=f"Prefers `{top_tool}` for {group}",
                description=(
                    f"Uses `{top_tool}` as primary tool for {group}-related tasks. "
                    f"Observed {top_count} times out of {len(group_traces)} {group} operations."
                ),
                pattern_type="tool",
                confidence=_confidence(len(group_traces)),
                evidence=evidence,
                tags=[group, top_tool],
            ))
        return patterns

    # ------------------------------------------------------------------
    # Commit style patterns
    # ------------------------------------------------------------------

    def _mine_commit_style(self) -> list[BehaviorPattern]:
        if not self._commits:
            return []

        patterns: list[BehaviorPattern] = []

        # Commit size (files changed)
        file_counts = [t.metadata.get("files_changed", 0) for t in self._commits if t.metadata.get("files_changed")]
        if file_counts:
            avg_files = sum(file_counts) / len(file_counts)
            style = "small, focused" if avg_files < 5 else "large, batched" if avg_files > 15 else "medium-sized"
            evidence = [
                Evidence(
                    description=f"`{t.content[:60]}` — {t.metadata.get('files_changed', '?')} files",
                    timestamp=t.timestamp,
                )
                for t in self._commits[-5:]
            ]
            patterns.append(BehaviorPattern(
                name=f"Prefers {style} commits",
                description=(
                    f"Average {avg_files:.1f} files per commit. "
                    f"Commits tend to be {style} and well-scoped."
                ),
                pattern_type="workflow",
                confidence=_confidence(len(self._commits)),
                evidence=evidence,
                tags=["git", "commit-style"],
            ))

        # Conventional commits
        typed_commits = [t for t in self._commits if t.metadata.get("type") != "other"]
        if len(typed_commits) > len(self._commits) * 0.6:
            type_dist = Counter(t.metadata.get("type") for t in typed_commits)
            top_types = [f"`{k}` ({v})" for k, v in type_dist.most_common(3)]
            evidence = [
                Evidence(
                    description=f"`{t.content[:70]}`",
                    timestamp=t.timestamp,
                )
                for t in typed_commits[-5:]
            ]
            patterns.append(BehaviorPattern(
                name="Follows Conventional Commits",
                description=(
                    f"Uses structured commit message format. "
                    f"Most common types: {', '.join(top_types)}."
                ),
                pattern_type="style",
                confidence=_confidence(len(typed_commits)),
                evidence=evidence,
                tags=["git", "commit-style", "conventional-commits"],
            ))

        # Primary commit type
        type_counter = Counter(t.metadata.get("type", "other") for t in self._commits)
        top_type, top_type_count = type_counter.most_common(1)[0]
        if top_type != "other" and top_type_count > 3:
            label = _COMMIT_TYPE_LABELS.get(top_type, top_type)
            patterns.append(BehaviorPattern(
                name=f"Focus on {label.title()}",
                description=(
                    f"Primary commit activity is {label} ({top_type_count} of {len(self._commits)} commits). "
                    f"Suggests current work phase is {label}-heavy."
                ),
                pattern_type="decision",
                confidence=_confidence(top_type_count),
                evidence=[
                    Evidence(
                        description=f"`{t.content[:70]}`",
                        timestamp=t.timestamp,
                    )
                    for t in self._commits
                    if t.metadata.get("type") == top_type
                ][-5:],
                tags=["git", "focus", top_type],
            ))

        return patterns

    # ------------------------------------------------------------------
    # Command habit patterns
    # ------------------------------------------------------------------

    def _mine_command_habits(self) -> list[BehaviorPattern]:
        if not self._shell:
            return []

        patterns: list[BehaviorPattern] = []
        cmd_counter: Counter = Counter()
        for t in self._shell:
            base = t.content.split()[0] if t.content.split() else t.content
            cmd_counter[base] += 1

        # Commands used 10+ times are habits
        for cmd, count in cmd_counter.most_common(20):
            if count < 10 or not cmd or cmd.startswith("#"):
                continue
            instances = [t for t in self._shell if t.content.split()[0] == cmd]
            evidence = [
                Evidence(
                    description=f"`{t.content[:80]}`",
                    timestamp=t.timestamp,
                )
                for t in instances[-5:]
            ]
            patterns.append(BehaviorPattern(
                name=f"Frequent use of `{cmd}`",
                description=f"Runs `{cmd}` regularly ({count} times in analysis window).",
                pattern_type="tool",
                confidence=_confidence(count),
                evidence=evidence,
                tags=["shell", cmd],
            ))

        return patterns[:8]  # cap at top 8

    # ------------------------------------------------------------------
    # Language preference patterns
    # ------------------------------------------------------------------

    def _mine_language_preferences(self) -> list[BehaviorPattern]:
        lang_traces: dict[str, list[Trace]] = defaultdict(list)

        for t in self._shell:
            lang = _detect_language_from_cmd(t.content)
            if lang:
                lang_traces[lang].append(t)

        for t in self._notes:
            headings_text = " ".join(t.metadata.get("headings", []))
            content_sample = t.content[:500]
            for lang, keywords in _LANG_KEYWORDS.items():
                if any(kw in content_sample or kw in headings_text for kw in keywords):
                    lang_traces[lang].append(t)

        patterns: list[BehaviorPattern] = []
        total = sum(len(v) for v in lang_traces.values())
        if total == 0:
            return []

        for lang, traces in sorted(lang_traces.items(), key=lambda x: -len(x[1])):
            if len(traces) < 3:
                continue
            pct = int(100 * len(traces) / total)
            evidence = [
                Evidence(description=f"`{t.content[:70]}`", timestamp=t.timestamp)
                for t in traces[-3:]
            ]
            patterns.append(BehaviorPattern(
                name=f"Primary language: {lang}",
                description=f"Works in {lang} approximately {pct}% of the time.",
                pattern_type="preference",
                confidence=_confidence(len(traces)),
                evidence=evidence,
                tags=["language", lang.lower()],
            ))
        return patterns[:5]

    # ------------------------------------------------------------------
    # Testing behavior
    # ------------------------------------------------------------------

    def _mine_testing_behavior(self) -> list[BehaviorPattern]:
        test_traces = [
            t for t in self._shell
            if any(t.content.split()[0] == tool.split()[0]
                   for tool in _TOOL_GROUPS["test"])
        ]
        if not test_traces:
            return []

        test_commits = [
            t for t in self._commits
            if t.metadata.get("type") == "test"
        ]

        evidence = [
            Evidence(description=f"`{t.content[:70]}`", timestamp=t.timestamp)
            for t in test_traces[-5:]
        ]

        desc = (
            f"Runs tests regularly — {len(test_traces)} test invocations detected. "
        )
        if test_commits:
            desc += f"Also writes test code ({len(test_commits)} test commits)."

        return [BehaviorPattern(
            name="Regular testing habit",
            description=desc,
            pattern_type="workflow",
            confidence=_confidence(len(test_traces)),
            evidence=evidence,
            tags=["testing", "quality"],
        )]

    # ------------------------------------------------------------------
    # Anti-patterns (things consistently avoided)
    # ------------------------------------------------------------------

    def _mine_anti_patterns(self) -> list[BehaviorPattern]:
        patterns: list[BehaviorPattern] = []

        # Check if force-push appears — if never, it's an anti-pattern
        force_push = [
            t for t in self._shell
            if "git push" in t.content and "--force" in t.content
        ]
        if not force_push and self._shell:
            patterns.append(BehaviorPattern(
                name="Avoids force-push",
                description=(
                    "No `git push --force` commands detected in analysis window. "
                    "Suggests discipline around shared branch safety."
                ),
                pattern_type="decision",
                confidence=ConfidenceLevel.MEDIUM,
                evidence=[],
                tags=["git", "safety"],
                anti_pattern=True,
            ))

        # Check for sudo usage — if rare, note it
        sudo_cmds = [t for t in self._shell if t.content.startswith("sudo ")]
        if self._shell and len(sudo_cmds) < len(self._shell) * 0.02:
            patterns.append(BehaviorPattern(
                name="Minimal sudo usage",
                description=(
                    f"Uses `sudo` rarely ({len(sudo_cmds)} times). "
                    "Suggests working in well-configured environments with proper permissions."
                ),
                pattern_type="preference",
                confidence=ConfidenceLevel.LOW,
                evidence=[
                    Evidence(description=f"`{t.content[:60]}`", timestamp=t.timestamp)
                    for t in sudo_cmds[:3]
                ],
                tags=["shell", "security"],
                anti_pattern=True,
            ))

        return patterns


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _confidence(count: int) -> ConfidenceLevel:
    if count >= 10:
        return ConfidenceLevel.HIGH
    if count >= 4:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


_LANG_KEYWORDS: dict[str, list[str]] = {
    "Python": ["python", "py", "pytest", "pip", "uv", "ruff", "mypy", "fastapi", "django"],
    "TypeScript": ["typescript", "tsx", "tsc", "eslint", "pnpm", "npm", "vite"],
    "JavaScript": ["javascript", "node", "bun", "deno", "jest"],
    "Rust": ["rust", "cargo", "clippy", "rustfmt"],
    "Go": ["golang", "go build", "go test", "gopls"],
}


def _detect_language_from_cmd(cmd: str) -> str | None:
    base = cmd.split()[0] if cmd.split() else cmd
    mapping = {
        "python": "Python", "python3": "Python", "uv": "Python",
        "pytest": "Python", "ruff": "Python", "mypy": "Python",
        "pip": "Python", "pip3": "Python",
        "node": "JavaScript", "bun": "JavaScript", "deno": "JavaScript",
        "npm": "TypeScript", "pnpm": "TypeScript", "tsc": "TypeScript",
        "cargo": "Rust", "rustup": "Rust",
        "go": "Go",
    }
    return mapping.get(base)

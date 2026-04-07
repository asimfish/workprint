"""Tests for Workprint collectors, miners, and generators."""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

from workprint.collectors.shell import ShellCollector
from workprint.collectors.git import GitCollector
from workprint.collectors.notes import NotesCollector
from workprint.generators.skill import SkillGenerator
from workprint.miners.pattern import PatternMiner
from workprint.miners.workflow import WorkflowMiner
from workprint.models import (
    BehaviorPattern,
    ConfidenceLevel,
    Evidence,
    Trace,
    TraceType,
    WorkprintProfile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts(day: int = 1) -> datetime:
    return datetime(2026, 3, day, 12, 0, 0, tzinfo=timezone.utc)


def _shell(cmd: str, day: int = 1) -> Trace:
    return Trace(type=TraceType.SHELL, content=cmd, timestamp=_ts(day))


def _commit(msg: str, day: int = 1, files: int = 3, tp: str = "feat") -> Trace:
    return Trace(
        type=TraceType.GIT_COMMIT,
        content=msg,
        timestamp=_ts(day),
        metadata={"files_changed": files, "type": tp, "repo": "testrepo",
                  "insertions": 10, "deletions": 2, "sha": "abc123"},
    )


# ---------------------------------------------------------------------------
# ShellCollector
# ---------------------------------------------------------------------------

class TestShellCollector:
    def test_parses_plain_history(self, tmp_path):
        hist = tmp_path / ".zsh_history"
        hist.write_text("git status\nnpm run dev\npytest\n")
        traces = ShellCollector([hist], days_limit=None).collect()
        assert len(traces) == 3
        assert traces[0].content == "git status"
        assert traces[0].type == TraceType.SHELL

    def test_parses_extended_zsh_history(self, tmp_path):
        hist = tmp_path / ".zsh_history"
        # zsh extended: `: timestamp:elapsed;command`
        hist.write_text(": 1743000000:0;git log --oneline\n: 1743000001:0;ls\n")
        traces = ShellCollector([hist], days_limit=None).collect()
        assert len(traces) == 2
        assert traces[0].content == "git log --oneline"
        assert traces[0].timestamp is not None

    def test_skips_empty_lines(self, tmp_path):
        hist = tmp_path / ".zsh_history"
        hist.write_text("git status\n\n\ngit diff\n")
        traces = ShellCollector([hist], days_limit=None).collect()
        assert len(traces) == 2

    def test_summarize(self):
        traces = [_shell("git status"), _shell("git diff"), _shell("npm run dev")]
        stats = ShellCollector.summarize(traces)
        assert stats["total"] == 3
        assert stats["unique_commands"] == 2
        assert stats["top_10"][0][0] == "git"  # git appears twice

    def test_missing_file_returns_empty(self):
        traces = ShellCollector([Path("/nonexistent/file")], days_limit=None).collect()
        assert traces == []


# ---------------------------------------------------------------------------
# PatternMiner
# ---------------------------------------------------------------------------

class TestPatternMiner:
    def test_detects_git_usage(self):
        traces = [_shell("git commit -m 'fix'") for _ in range(10)]
        patterns = PatternMiner(traces).mine()
        names = [p.name for p in patterns]
        assert any("git" in n.lower() for n in names)

    def test_detects_conventional_commits(self):
        traces = [
            _commit(f"feat: add feature {i}", files=2) for i in range(8)
        ] + [
            _commit(f"fix: bug {i}", files=1, tp="fix") for i in range(2)
        ]
        patterns = PatternMiner(traces).mine()
        conventional = [p for p in patterns if "Conventional" in p.name]
        assert conventional, "Should detect conventional commits pattern"
        assert conventional[0].confidence == ConfidenceLevel.HIGH

    def test_detects_commit_size(self):
        traces = [_commit(f"feat: f{i}", files=20) for i in range(10)]
        patterns = PatternMiner(traces).mine()
        size_patterns = [p for p in patterns if "commit" in p.name.lower() and "batched" in p.name.lower()]
        assert size_patterns

    def test_anti_pattern_no_force_push(self):
        traces = [_shell("git push origin main") for _ in range(5)]
        patterns = PatternMiner(traces).mine()
        anti = [p for p in patterns if p.anti_pattern and "force" in p.name.lower()]
        assert anti

    def test_no_patterns_from_empty_traces(self):
        patterns = PatternMiner([]).mine()
        assert patterns == []

    def test_confidence_levels(self):
        # 15 occurrences → high
        traces = [_shell("pytest") for _ in range(15)]
        patterns = PatternMiner(traces).mine()
        high = [p for p in patterns if p.confidence == ConfidenceLevel.HIGH]
        assert high


# ---------------------------------------------------------------------------
# WorkflowMiner
# ---------------------------------------------------------------------------

class TestWorkflowMiner:
    def test_detects_repeated_sequence(self):
        traces = []
        for _ in range(5):
            traces.extend([_shell("pytest"), _shell("git")])
        workflows = WorkflowMiner(traces).mine()
        assert workflows, "Should detect pytest → git sequence"

    def test_no_workflows_from_empty(self):
        workflows = WorkflowMiner([]).mine()
        assert workflows == []

    def test_min_occurrence_threshold(self):
        # Only 2 occurrences — below default threshold of 3
        traces = [_shell("pytest"), _shell("git")] * 2
        workflows = WorkflowMiner(traces, min_occurrences=3).mine()
        assert not workflows

    def test_dedup_removes_subset(self):
        # 3-step sequence should suppress 2-step subset
        traces = []
        for _ in range(5):
            traces.extend([_shell("ruff"), _shell("pytest"), _shell("git")])
        workflows = WorkflowMiner(traces).mine()
        two_step_ruff_pytest = [
            w for w in workflows
            if len(w.steps) == 2 and w.steps == ["ruff", "pytest"]
        ]
        # The 2-step prefix should be removed because 3-step ruff→pytest→git exists
        assert not two_step_ruff_pytest


# ---------------------------------------------------------------------------
# SkillGenerator
# ---------------------------------------------------------------------------

class TestSkillGenerator:
    def _sample_profile(self) -> WorkprintProfile:
        return WorkprintProfile(
            name="alice",
            display_name="Alice",
            total_traces=100,
            date_range="2026-01-01 — 2026-03-31",
            patterns=[
                BehaviorPattern(
                    name="Test-first",
                    description="Runs tests before committing.",
                    pattern_type="workflow",
                    confidence=ConfidenceLevel.HIGH,
                    evidence=[Evidence("ran pytest", _ts(1))],
                ),
            ],
        )

    def test_render_contains_name(self):
        profile = self._sample_profile()
        output = SkillGenerator(profile).render()
        assert "Alice" in output
        assert "workprint/alice" in output

    def test_render_contains_pattern(self):
        profile = self._sample_profile()
        output = SkillGenerator(profile).render()
        assert "Test-first" in output

    def test_render_contains_usage_block(self):
        profile = self._sample_profile()
        output = SkillGenerator(profile).render()
        assert "/workprint alice" in output

    def test_render_contains_honest_limits(self):
        profile = self._sample_profile()
        output = SkillGenerator(profile).render()
        assert "Honest Limits" in output

    def test_write_creates_file(self, tmp_path):
        profile = self._sample_profile()
        out = tmp_path / "skill.md"
        SkillGenerator(profile).write(out)
        assert out.exists()
        content = out.read_text()
        assert len(content) > 100

    def test_frontmatter_format(self):
        profile = self._sample_profile()
        output = SkillGenerator(profile).render()
        assert output.startswith("---\n")
        assert "name: workprint/alice" in output
        assert "total_traces: 100" in output


# ---------------------------------------------------------------------------
# NotesCollector
# ---------------------------------------------------------------------------

class TestNotesCollector:
    def test_collects_markdown_files(self, tmp_path):
        (tmp_path / "note1.md").write_text("# Hello\nSome content here")
        (tmp_path / "note2.md").write_text("# World\nMore content")
        (tmp_path / "skip.txt").write_text("ignored")  # .txt also supported
        traces = NotesCollector([tmp_path], days_limit=None).collect()
        assert len(traces) == 3  # both .md and .txt

    def test_extracts_headings(self, tmp_path):
        note = tmp_path / "test.md"
        note.write_text("# Main Topic\n\n## Sub Topic\n\nSome text")
        traces = NotesCollector([tmp_path], days_limit=None).collect()
        assert traces[0].metadata["headings"] == ["Main Topic", "Sub Topic"]

    def test_detects_code_blocks(self, tmp_path):
        note = tmp_path / "dev.md"
        note.write_text("# Dev\n\n```python\nprint('hello')\n```")
        traces = NotesCollector([tmp_path], days_limit=None).collect()
        assert traces[0].metadata["has_code"] is True

    def test_missing_dir_returns_empty(self):
        traces = NotesCollector([Path("/nonexistent")], days_limit=None).collect()
        assert traces == []

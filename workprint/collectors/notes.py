"""Notes collector — parses markdown/text files into Traces."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from workprint.models import Trace, TraceType

_SUPPORTED_SUFFIXES = {".md", ".txt", ".markdown", ".rst"}
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

# Heading pattern to extract topics
_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
# Task/todo markers
_TODO_RE = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+(.+)$", re.MULTILINE)


class NotesCollector:
    """Recursively scans directories for markdown/text notes."""

    def __init__(self, dirs: list[Path], days_limit: int | None = 90):
        self.dirs = dirs
        self.cutoff = self._cutoff(days_limit)

    # ------------------------------------------------------------------
    def collect(self) -> list[Trace]:
        traces: list[Trace] = []
        for d in self.dirs:
            for path in self._iter_files(d):
                traces.extend(self._parse_file(path))
        return traces

    # ------------------------------------------------------------------
    def _iter_files(self, root: Path):
        if root.is_file() and root.suffix in _SUPPORTED_SUFFIXES:
            yield root
            return
        for p in sorted(root.rglob("*")):
            if p.suffix in _SUPPORTED_SUFFIXES and p.is_file():
                yield p

    def _parse_file(self, path: Path) -> list[Trace]:
        try:
            content = path.read_text(errors="replace")
        except OSError:
            return []

        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        ts = self._extract_date(content, path) or mtime

        if self.cutoff and ts and ts < self.cutoff:
            return []

        headings = _HEADING_RE.findall(content)
        todos = _TODO_RE.findall(content)
        word_count = len(content.split())

        # One trace per file, content is the full text (truncated for storage)
        return [Trace(
            type=TraceType.NOTE,
            content=content[:4000],   # keep first 4KB for pattern analysis
            timestamp=ts,
            metadata={
                "path": str(path),
                "filename": path.name,
                "headings": headings,
                "todos": todos,
                "word_count": word_count,
                "has_code": "```" in content,
            },
        )]

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_date(content: str, path: Path) -> datetime | None:
        # try to find a date in the first 200 chars
        snippet = content[:200]
        m = _DATE_RE.search(snippet)
        if m:
            try:
                return datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        # fall back to file mtime
        return None

    @staticmethod
    def _cutoff(days: int | None) -> datetime | None:
        if days is None:
            return None
        from datetime import timedelta
        return datetime.now(tz=timezone.utc) - timedelta(days=days)

    # ------------------------------------------------------------------
    @staticmethod
    def summarize(traces: list[Trace]) -> dict:
        if not traces:
            return {"total": 0}
        total_words = sum(t.metadata.get("word_count", 0) for t in traces)
        with_code = sum(1 for t in traces if t.metadata.get("has_code"))
        all_headings: list[str] = []
        for t in traces:
            all_headings.extend(t.metadata.get("headings", []))
        return {
            "total": len(traces),
            "total_words": total_words,
            "notes_with_code": with_code,
            "sample_headings": all_headings[:10],
        }

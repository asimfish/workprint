"""Shell history collector — parses zsh/bash history into Traces."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from workprint.models import Trace, TraceType


# zsh extended history: `: <timestamp>:<elapsed>;<command>`
_ZSH_EXTENDED_RE = re.compile(r"^: (\d+):\d+;(.+)$")


class ShellCollector:
    """Reads shell history files and yields Trace objects."""

    def __init__(self, paths: list[Path], days_limit: int | None = 90):
        self.paths = paths
        self.cutoff = self._cutoff(days_limit)

    # ------------------------------------------------------------------
    def collect(self) -> list[Trace]:
        traces: list[Trace] = []
        for path in self.paths:
            traces.extend(self._parse_file(path))
        return traces

    # ------------------------------------------------------------------
    def _parse_file(self, path: Path) -> list[Trace]:
        try:
            raw = path.read_text(errors="replace")
        except OSError:
            return []

        traces: list[Trace] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            m = _ZSH_EXTENDED_RE.match(line)
            if m:
                ts = datetime.fromtimestamp(int(m.group(1)), tz=timezone.utc)
                cmd = m.group(2).strip()
            else:
                ts = None
                cmd = line.lstrip("#").strip()

            if not cmd:
                continue
            if self.cutoff and ts and ts < self.cutoff:
                continue

            traces.append(Trace(
                type=TraceType.SHELL,
                content=cmd,
                timestamp=ts,
                metadata={"source": str(path)},
            ))
        return traces

    # ------------------------------------------------------------------
    @staticmethod
    def _cutoff(days: int | None) -> datetime | None:
        if days is None:
            return None
        from datetime import timedelta
        return datetime.now(tz=timezone.utc) - timedelta(days=days)

    # ------------------------------------------------------------------
    @staticmethod
    def summarize(traces: list[Trace]) -> dict:
        """Return quick stats for display."""
        if not traces:
            return {"total": 0}
        top_cmds: dict[str, int] = {}
        for t in traces:
            base = t.content.split()[0] if t.content.split() else t.content
            top_cmds[base] = top_cmds.get(base, 0) + 1
        sorted_cmds = sorted(top_cmds.items(), key=lambda x: -x[1])
        return {
            "total": len(traces),
            "unique_commands": len(top_cmds),
            "top_10": sorted_cmds[:10],
        }

"""Git log collector — parses git commits into Traces."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from workprint.models import Trace, TraceType


_GIT_FORMAT = "%H%x00%ae%x00%ai%x00%s%x00%b%x00---END---"


class GitCollector:
    """Reads git log from one or more repositories."""

    def __init__(self, git_dirs: list[Path], days_limit: int | None = 90):
        self.git_dirs = git_dirs
        self.days_limit = days_limit

    # ------------------------------------------------------------------
    def collect(self) -> list[Trace]:
        traces: list[Trace] = []
        for d in self.git_dirs:
            traces.extend(self._parse_repo(d))
        return traces

    # ------------------------------------------------------------------
    def _parse_repo(self, path: Path) -> list[Trace]:
        cmd = [
            "git", "-C", str(path),
            "log",
            "--format=" + _GIT_FORMAT,
        ]
        if self.days_limit:
            cmd += [f"--since={self.days_limit} days ago"]
        cmd += ["--author-date-order"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

        if result.returncode != 0:
            return []

        raw = result.stdout
        traces: list[Trace] = []
        for block in raw.split("---END---\n"):
            block = block.strip()
            if not block:
                continue
            parts = block.split("\x00")
            if len(parts) < 4:
                continue

            sha, email, ts_str, subject = parts[0], parts[1], parts[2], parts[3]
            body = parts[4] if len(parts) > 4 else ""

            try:
                ts = datetime.fromisoformat(ts_str.strip())
            except ValueError:
                ts = None

            # get changed file stats
            stats = self._file_stats(path, sha)

            traces.append(Trace(
                type=TraceType.GIT_COMMIT,
                content=subject.strip(),
                timestamp=ts,
                metadata={
                    "sha": sha[:8],
                    "email": email,
                    "body": body.strip(),
                    "repo": path.name,
                    "files_changed": stats.get("files", 0),
                    "insertions": stats.get("insertions", 0),
                    "deletions": stats.get("deletions", 0),
                    "type": self._commit_type(subject),
                },
            ))
        return traces

    # ------------------------------------------------------------------
    @staticmethod
    def _file_stats(path: Path, sha: str) -> dict:
        try:
            r = subprocess.run(
                ["git", "-C", str(path), "show", "--stat", "--format=", sha],
                capture_output=True, text=True, timeout=10,
            )
            lines = r.stdout.strip().splitlines()
            if not lines:
                return {}
            summary = lines[-1]
            files = _extract_int(summary, "file")
            ins = _extract_int(summary, "insertion")
            dels = _extract_int(summary, "deletion")
            return {"files": files, "insertions": ins, "deletions": dels}
        except Exception:
            return {}

    @staticmethod
    def _commit_type(subject: str) -> str:
        # conventional commits prefix
        for prefix in ("feat", "fix", "refactor", "docs", "test", "chore", "perf", "ci"):
            if subject.lower().startswith(prefix):
                return prefix
        return "other"

    # ------------------------------------------------------------------
    @staticmethod
    def summarize(traces: list[Trace]) -> dict:
        if not traces:
            return {"total": 0}
        types: dict[str, int] = {}
        repos: dict[str, int] = {}
        total_files = 0
        for t in traces:
            tp = t.metadata.get("type", "other")
            types[tp] = types.get(tp, 0) + 1
            repo = t.metadata.get("repo", "?")
            repos[repo] = repos.get(repo, 0) + 1
            total_files += t.metadata.get("files_changed", 0)
        return {
            "total": len(traces),
            "commit_types": dict(sorted(types.items(), key=lambda x: -x[1])),
            "repos": dict(sorted(repos.items(), key=lambda x: -x[1])),
            "avg_files_per_commit": round(total_files / len(traces), 1),
        }


def _extract_int(text: str, keyword: str) -> int:
    import re
    m = re.search(r"(\d+)\s+" + keyword, text)
    return int(m.group(1)) if m else 0

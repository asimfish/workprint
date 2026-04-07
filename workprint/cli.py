"""Workprint CLI — main entry point."""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from workprint import __version__, __tagline__
from workprint.collectors import GitCollector, NotesCollector, ShellCollector
from workprint.config import WorkprintConfig
from workprint.generators import SkillGenerator
from workprint.miners import PatternMiner, WorkflowMiner
from workprint.models import WorkprintProfile

console = Console()


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(__version__, prog_name="workprint")
def main():
    """Workprint — Distill real behavior traces into executable AI skills."""


# ---------------------------------------------------------------------------
# workprint analyze
# ---------------------------------------------------------------------------

@main.command()
@click.option("--name", "-n", default="me", show_default=True,
              help="Identifier for this workprint (slug).")
@click.option("--display-name", "-d", default="", help="Display name (defaults to --name).")
@click.option("--shell-history", multiple=True, type=click.Path(),
              help="Path(s) to shell history file.")
@click.option("--git-dir", multiple=True, type=click.Path(),
              help="Path(s) to git repository root(s).")
@click.option("--notes", multiple=True, type=click.Path(),
              help="Path(s) to notes directory or file.")
@click.option("--days", default=90, show_default=True,
              help="Only analyze traces from the last N days.")
@click.option("--output", "-o", default="workprint.md",
              help="Output SKILL.md path.", show_default=True)
@click.option("--confidence", default="low",
              type=click.Choice(["low", "medium", "high"]),
              help="Minimum confidence level to include in output.", show_default=True)
@click.option("--auto-detect/--no-auto-detect", default=True,
              help="Auto-detect shell history in home directory.")
def analyze(name, display_name, shell_history, git_dir, notes,
            days, output, confidence, auto_detect):
    """Collect traces, mine patterns, and generate SKILL.md in one step."""

    _print_banner()

    cfg = WorkprintConfig(
        name=name,
        display_name=display_name or name,
        shell_history_paths=[Path(p) for p in shell_history],
        git_dirs=[Path(p) for p in git_dir],
        note_dirs=[Path(p) for p in notes],
        days_limit=days,
        confidence_threshold=confidence,
    )

    if auto_detect and not cfg.shell_history_paths:
        auto_cfg = WorkprintConfig.auto_detect()
        cfg.shell_history_paths = auto_cfg.shell_history_paths
        if cfg.shell_history_paths:
            console.print(f"[dim]Auto-detected shell history: "
                          f"{', '.join(str(p) for p in cfg.shell_history_paths)}[/dim]")

    all_traces = []
    stats = {}

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        console=console, transient=True,
    ) as progress:

        # -- Shell --
        if cfg.shell_history_paths:
            t = progress.add_task("Collecting shell history…")
            collector = ShellCollector(cfg.shell_history_paths, days_limit=cfg.days_limit)
            shell_traces = collector.collect()
            all_traces.extend(shell_traces)
            stats["shell"] = ShellCollector.summarize(shell_traces)
            progress.remove_task(t)

        # -- Git --
        if cfg.git_dirs:
            t = progress.add_task("Collecting git log…")
            collector = GitCollector(cfg.git_dirs, days_limit=cfg.days_limit)
            git_traces = collector.collect()
            all_traces.extend(git_traces)
            stats["git"] = GitCollector.summarize(git_traces)
            progress.remove_task(t)

        # -- Notes --
        if cfg.note_dirs:
            t = progress.add_task("Collecting notes…")
            collector = NotesCollector(cfg.note_dirs, days_limit=cfg.days_limit)
            note_traces = collector.collect()
            all_traces.extend(note_traces)
            stats["notes"] = NotesCollector.summarize(note_traces)
            progress.remove_task(t)

        # -- Mine --
        t = progress.add_task("Mining behavioral patterns…")
        pattern_miner = PatternMiner(all_traces)
        patterns = pattern_miner.mine()

        workflow_miner = WorkflowMiner(all_traces)
        workflows = workflow_miner.mine()
        progress.remove_task(t)

    if not all_traces:
        console.print("[yellow]No traces found. Provide --shell-history, --git-dir, or --notes.[/yellow]")
        raise click.Abort()

    # Filter by confidence
    conf_order = {"low": 0, "medium": 1, "high": 2}
    min_conf = conf_order[confidence]
    patterns = [p for p in patterns if conf_order[p.confidence.value] >= min_conf]

    # Build profile
    dates = [t.timestamp for t in all_traces if t.timestamp]
    if dates:
        date_range = f"{min(dates).strftime('%Y-%m-%d')} — {max(dates).strftime('%Y-%m-%d')}"
    else:
        date_range = "unknown"

    profile = WorkprintProfile(
        name=cfg.name,
        display_name=cfg.display_name,
        total_traces=len(all_traces),
        date_range=date_range,
        patterns=patterns,
        workflows=workflows,
    )

    # Generate SKILL.md
    out_path = Path(output)
    SkillGenerator(profile).write(out_path)

    # Print summary
    _print_summary(stats, patterns, workflows, out_path)


# ---------------------------------------------------------------------------
# workprint info
# ---------------------------------------------------------------------------

@main.command()
@click.argument("skill_path", type=click.Path(exists=True))
def info(skill_path):
    """Show summary of an existing SKILL.md."""
    content = Path(skill_path).read_text()
    lines = content.splitlines()
    console.print(Panel(
        "\n".join(lines[:30]),
        title=f"[bold]{skill_path}[/bold]",
        subtitle=f"{len(lines)} lines total",
    ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_banner():
    console.print(
        Panel(
            f"[bold cyan]Workprint[/bold cyan] v{__version__}\n"
            f"[dim]{__tagline__}[/dim]",
            expand=False,
        )
    )


def _print_summary(stats, patterns, workflows, out_path):
    console.print()

    # Trace stats table
    table = Table(title="Collected Traces", show_header=True, header_style="bold")
    table.add_column("Source", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Details")

    if "shell" in stats:
        s = stats["shell"]
        top = ", ".join(f"`{c}`" for c, _ in (s.get("top_10") or [])[:5])
        table.add_row("Shell", str(s.get("total", 0)), f"Top: {top}")

    if "git" in stats:
        s = stats["git"]
        types = ", ".join(f"{k}:{v}" for k, v in list((s.get("commit_types") or {}).items())[:3])
        table.add_row("Git commits", str(s.get("total", 0)),
                      f"Types: {types} | Avg {s.get('avg_files_per_commit','?')} files/commit")

    if "notes" in stats:
        s = stats["notes"]
        table.add_row("Notes", str(s.get("total", 0)),
                      f"{s.get('total_words', 0)} words, {s.get('notes_with_code', 0)} with code")

    console.print(table)
    console.print()

    # Pattern summary
    high = sum(1 for p in patterns if p.confidence.value == "high")
    medium = sum(1 for p in patterns if p.confidence.value == "medium")
    low = sum(1 for p in patterns if p.confidence.value == "low")
    anti = sum(1 for p in patterns if p.anti_pattern)

    console.print(
        f"[green]Mined[/green] {len(patterns)} patterns "
        f"([bold]{high}[/bold] high / {medium} medium / {low} low) "
        f"+ {len(workflows)} workflow sequences"
        + (f" + {anti} anti-patterns" if anti else "")
    )
    console.print(f"\n[bold green]SKILL.md written to:[/bold green] {out_path}")
    console.print(
        f"\n[dim]Load it in Claude ​Code with: "
        f"`/skill load {out_path}` or add to your project's SKILL.md[/dim]"
    )

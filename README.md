# Workprint

**Distill real behavior traces into executable AI skills.**

Workprint extracts behavioral patterns from your actual traces (shell history, git commits, notes) and generates executable Claude Code skills—not personality simulation, but true behavioral replication.

## The Difference

| Tool | Input | Output | Use Case |
|------|-------|--------|----------|
| **nuwa-skill** | Public figures' writings | Cognitive framework | AI thinks like them |
| **yourself-skill** | Your diary + chats | Personality model | AI talks like you |
| **Workprint** | Your real traces (git, shell, notes) | Behavioral skill | AI works like you |

## Why Behavioral Traces?

- **More honest**: People do ≠ people say
- **Empirically grounded**: Each pattern backed by real evidence
- **Continuously updatable**: New traces = automatic pattern updates
- **Executable**: AI can actually use it to replace your workflows

## Features

- 📊 **Multi-source collection**: Shell history, git log, markdown notes
- 🧮 **Statistical pattern mining**: No ML overhead, privacy-first analysis
- 📈 **Confidence scoring**: High/medium/low with evidence counts
- 🎯 **Workflow inference**: Detect common sequences and decision patterns
- 📝 **SKILL.md generation**: Compatible with Claude Code ecosystem
- 🔒 **100% local processing**: Everything runs on your machine

## Quick Start

```bash
# Install
pip install workprint

# Initialize
workprint init --name "my_workprint" --user-dir ~

# Analyze your traces
workprint analyze --shell-history ~/.zsh_history --git-dir ~/myrepo --notes ~/notes/

# Generate SKILL.md
workprint generate --output ./my_skill.md
```

## Example Output

```markdown
# Workprint: alice

> Distilled from 1,247 behavioral traces across 90 days

## Core Patterns

### Incremental Commits
**Confidence**: High (47 occurrences)
**Pattern**: Prefers small, focused commits with clear messages

**Evidence**:
- 2026-03-15: `fix: typo in auth.py` (1 file, 2 changes)
- 2026-03-16: `feat: add login validation` (2 files, 18 changes)
- 2026-03-20: `refactor: extract utils module` (3 files, 42 changes)

Avg files/commit: 2.3 | Avg msg length: 48 chars

### Async-First Architecture
**Confidence**: High
**Triggers**: When building backend services
**Pattern**: Consistently uses async patterns over sync

## Tool Preferences

- **Editor**: Cursor, VSCode (95% of edits)
- **Language**: Python (60%), TypeScript (35%), Shell (5%)
- **Workflow**: Feature branch → PR → squash merge
```

## Project Structure

```
workprint/
├── workprint/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration management
│   ├── collectors/
│   │   ├── shell.py        # Shell history parsing
│   │   ├── git.py          # Git log analysis
│   │   └── notes.py        # Markdown/text collection
│   ├── miners/
│   │   ├── pattern.py      # Statistical pattern mining
│   │   └── workflow.py     # Sequence analysis
│   ├── generators/
│   │   └── skill.py        # SKILL.md generation
│   └── models.py           # Data models
├── tests/
├── examples/
└── pyproject.toml
```

## How It Works

```
Collect → Parse → Extract → Cluster → Generate
  ↓        ↓        ↓         ↓         ↓
 Traces   Events   Atoms   Patterns  SKILL.md
```

1. **Collect**: Read from shell history, git, notes
2. **Parse**: Extract timestamps, metadata, context
3. **Extract**: Atomic behaviors (commands, commits, topics)
4. **Cluster**: Group into statistical patterns
5. **Generate**: Output executable SKILL.md format

## Design Principles

1. **Privacy First**: All computation local, no data sent anywhere
2. **Evidence-Driven**: Every pattern backed by concrete traces
3. **Empirical**: Statistical analysis, not ML hallucination
4. **Executable**: Output is actionable, not just descriptive
5. **Transparent**: Show all evidence behind each pattern

## Comparison

### vs. yourself-skill
- ✅ Input is what you DO, not what you SAY
- ✅ Automatically updates with new traces
- ✅ No manual diary needed
- ✅ Works even for implicit behaviors

### vs. nuwa-skill
- ✅ No dependency on public figures' writing volume
- ✅ Captures your actual quirks, not idealized thoughts
- ✅ Respects privacy (no API calls needed)
- ✅ Real-time updates possible

## Usage Examples

```bash
# Analyze just a git repo
workprint analyze --git-dir ~/projects/myapp

# Combine multiple sources
workprint analyze \
  --shell-history ~/.zsh_history \
  --git-dir ~/projects/app1 ~/projects/app2 \
  --notes ~/notes/ ~/journal/

# Generate with custom settings
workprint generate \
  --output ./alice_workprint.md \
  --confidence-threshold medium \
  --include-anti-patterns true
```

## Roadmap

- [ ] v1.0: Core CLI with collectors, miners, generators
- [ ] v1.1: VSCode extension for in-editor skill sync
- [ ] v1.2: Optional Claude API integration for semantic analysis
- [ ] v2.0: Continuous monitoring mode (auto-update on new traces)
- [ ] v2.1: Skill ecosystem (share, combine, version)

## Contributing

Issues and PRs welcome! See CONTRIBUTING.md for guidelines.

## License

MIT

---

**Philosophy**: Not "Here's a digital copy of you" but rather "Here's a mirror of how you actually work. Refine it. Use it to help yourself think."

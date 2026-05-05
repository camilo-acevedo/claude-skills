# session-handoff

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that lets you save and restore task context between sessions on your terms — instead of relying on `/compact` to choose what to keep.

Three operations:

| Subcommand | Use it when |
|------------|-------------|
| `save` | Wrapping up a session, mid-task, or before a long break. |
| `list` | "What was I working on last?" / "Show recent handoffs". |
| `resume` | Start of a new session that should continue prior work. |

Handoff files live at `<repo>/.claude/handoff/` with frontmatter (timestamp, branch, slug) and a structured Markdown body.

> **Estimated savings:** avoids paying for a full conversation re-load and gives you control over what state survives session boundaries.

## Requirements

- Python 3.8+ (standard library only).
- `git` on PATH (optional — used to record the current branch).

## Installation

See the [top-level README](../README.md#installation).

```bash
./install/install.sh session-handoff       # macOS / Linux
```

```powershell
.\install\install.ps1 session-handoff      # Windows
```

## Usage

Inside any Claude Code session:

```
/session-handoff save --task "rewrite auth middleware" --decisions "use JWT, drop session cookies" --next "wire to /login, add tests"
/session-handoff list
/session-handoff resume
```

Or run directly:

```bash
python ~/.claude/skills/session-handoff/scripts/handoff.py save --task "X" --next "Y"
python ~/.claude/skills/session-handoff/scripts/handoff.py list --limit 5
python ~/.claude/skills/session-handoff/scripts/handoff.py resume --name auth
```

For long handoff bodies, pipe the full markdown via stdin:

```bash
python ~/.claude/skills/session-handoff/scripts/handoff.py save --from-stdin --name auth-rewrite < handoff.md
```

## Save fields

| Flag | Section in the handoff |
|------|------------------------|
| `--name SLUG` | Override the auto-derived filename slug. |
| `--task TEXT` | "Current task" section + title. |
| `--decisions TEXT` | "Decisions made". |
| `--open TEXT` | "Open questions". |
| `--files a,b,c` | "Files touched" (comma-separated). |
| `--next TEXT` | "Next steps". |
| `--notes TEXT` | "Notes" (free-form). |
| `--from-stdin` | Read the full Markdown body from stdin (overrides field flags). |

The script auto-records the current git branch and timestamp.

## Output examples

`save`:
```
session-handoff: wrote .claude/handoff/20260504-180000-auth-rewrite.md
```

`list`:
```
.claude/handoff/
  20260504-180000-auth-rewrite.md   on skill/auth (3h ago)
  20260503-220000-fix-pagination.md on main (1d ago)
```

`resume`:
```markdown
# resuming 20260504-180000-auth-rewrite.md (saved 2026-05-04T18:00:00Z on skill/auth, 3h ago)

# Handoff: rewrite auth middleware

## Current task
Working on POST /users with validation for email format…
```

## Notes

- The `.claude/handoff/` directory should be in your `.gitignore` (or the whole `.claude/`).
- Resuming a stale handoff (file paths that no longer exist, deleted branch) is fine — the data is informational. Verify against the current code before acting on it.
- Slugs are derived from `--name` when set, else from the first words of `--task`.

## License

MIT — inherited from the [parent repo](../LICENSE).

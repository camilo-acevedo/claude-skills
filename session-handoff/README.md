# session-handoff

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that lets you save and restore task context between sessions on your terms — instead of relying on `/compact` to choose what to keep.

Three operations:

| Subcommand | Use it when |
|------------|-------------|
| `save` | Wrapping up a session, mid-task, or before a long break. |
| `list` | "What was I working on last?" / "Show recent handoffs". |
| `resume` | Start of a new session that should continue prior work. |

Handoff files live at `<repo>/.claude/handoff/` with YAML frontmatter (timestamp, branch, slug) and a structured Markdown body.

> **Estimated savings:** avoids paying for a full conversation re-load and gives you control over what state survives session boundaries.

## How it works

This skill is **100% Markdown — no Python, no external scripts**. The [`SKILL.md`](SKILL.md) tells Claude exactly which files to read/write under `.claude/handoff/`, the YAML frontmatter format, and the slug/age rules. Claude uses its built-in Bash, Read, Write, and Glob tools.

## Requirements

- `git` on `PATH` (optional — only used to record the current branch).
- That's it — no Python, no Node, no other runtimes.

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
/session-handoff save task="rewrite auth middleware" decisions="use JWT, drop session cookies" next="wire to /login, add tests"
/session-handoff list
/session-handoff resume
/session-handoff resume name=auth
```

These are free-form arguments — Claude reads them as natural language and maps them to the fields in `SKILL.md`. You can also just say "save a handoff for what we did today" and Claude will build the fields from the conversation.

## Save fields

| Field | Section in the handoff |
|-------|------------------------|
| `name` | Override the auto-derived filename slug. |
| `task` | "Current task" section + title. |
| `decisions` | "Decisions made". |
| `open` | "Open questions". |
| `files` | "Files touched" (list of paths). |
| `next` | "Next steps". |
| `notes` | "Notes" (free-form). |

The skill auto-records the current git branch and a UTC timestamp into the frontmatter.

## Output examples

`save`:
```
session-handoff: wrote .claude/handoff/20260514-180000-auth-rewrite.md
```

`list`:
```
.claude/handoff/
  20260514-180000-auth-rewrite.md   on skill/auth (3h ago)
  20260513-220000-fix-pagination.md on main (1d ago)
```

`resume`:
```markdown
# resuming 20260514-180000-auth-rewrite.md (saved 2026-05-14T18:00:00Z on skill/auth, 3h ago)

# Handoff: rewrite auth middleware

## Current task
Working on POST /users with validation for email format…
```

## Notes

- The `.claude/handoff/` directory should be in your `.gitignore` (or the whole `.claude/`).
- Resuming a stale handoff (file paths that no longer exist, deleted branch) is fine — the data is informational. Verify against the current code before acting on it.
- Slugs are derived from `name` when set, else from the first words of `task`.

## License

MIT — inherited from the [parent repo](../LICENSE).

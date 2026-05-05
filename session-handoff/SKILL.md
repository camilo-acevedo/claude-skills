---
name: session-handoff
description: |
  Save / list / resume task context across Claude Code sessions on the
  user's terms (instead of relying on /compact to choose what to keep).
  Writes a structured Markdown handoff file under <root>/.claude/handoff/
  containing the current task, decisions, open questions, files touched,
  and next steps. Use save when wrapping up a session, resume at the
  start of the next one.
---

# session-handoff

## When to invoke

Three operations:

### `save`
Invoke when ANY of these apply:

- The user is wrapping up a session and wants to "save where we are".
- The conversation is getting long and you want to checkpoint state before
  `/compact` summarizes it for you.
- You've just made a non-trivial decision the next session should know about.

### `list`
Invoke when the user asks "what handoffs do I have?" or "what was I working
on last?".

### `resume`
Invoke at the **start of a new session** when the user says "let's continue"
or mentions previous work. Read the most recent handoff (or a specific named
one) and use it to seed the next response.

Do NOT invoke `save` for trivial tasks where the diff alone tells the story.
This is for in-progress work with context that is not in the code itself.

## How to invoke

```bash
python <skill-dir>/scripts/handoff.py save   [--name SLUG] [--task TEXT] [--decisions TEXT] [--open TEXT] [--files a,b,c] [--next TEXT] [--notes TEXT]
python <skill-dir>/scripts/handoff.py list   [--limit N]
python <skill-dir>/scripts/handoff.py resume [--name SLUG]
```

`<skill-dir>` is typically `~/.claude/skills/session-handoff/`.

For long handoff bodies you can pipe a full markdown document via stdin:

```bash
python <skill-dir>/scripts/handoff.py save --from-stdin --name auth-rewrite < handoff.md
```

## Save fields

| Flag | Section in the handoff |
|------|------------------------|
| `--task` | Current task |
| `--decisions` | Decisions made |
| `--open` | Open questions |
| `--files` | Files touched (comma-separated) |
| `--next` | Next steps |
| `--notes` | Free-form notes |

The script auto-records the current branch (via `git`) and the timestamp.

## What you get back

`save`:

```
session-handoff: wrote .claude/handoff/20260504-180000-auth-rewrite.md
```

`list`:

```
.claude/handoff/
  20260504-180000-auth-rewrite.md   on skill/auth (3 hours ago)
  20260503-220000-fix-pagination.md on main (1 day ago)
  20260503-100000-spike-graphql.md  on skill/graphql (2 days ago)
```

`resume`:

```markdown
# Handoff: auth rewrite (saved 2026-05-04T18:00:00Z on skill/auth, 3h ago)

## Current task
Working on POST /users with validation for email format…

## Decisions made
- Use pydantic for validation (not dataclasses) per existing pattern…
…
```

## Notes

- Handoff files live under `<repo>/.claude/handoff/`. The `.claude/` folder
  should be in your project's `.gitignore`.
- Name slugs are derived from `--name` if provided, else from the first words
  of `--task`. Anything not safe for a filename is replaced with `-`.
- Resuming a stale handoff (file paths that no longer exist, branch that has
  been deleted) is fine — the data is purely informational. Verify against
  the current code before acting.

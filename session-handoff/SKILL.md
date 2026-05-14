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

A **Markdown-only** skill — no Python, no scripts. You (Claude) read/write
Markdown files under `<repo-root>/.claude/handoff/` using the Read, Write,
Glob, and Bash tools.

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

## Finding the repo root

For all operations, locate the repo root:

```bash
git rev-parse --show-toplevel
```

If the command fails (not in a git repo), use the current working directory
and warn the user that the handoff is not anchored to a git repo.

The handoff directory is always `<repo-root>/.claude/handoff/`.

## Operation: `save`

### Step 1 — gather metadata in parallel

Run these in a single Bash batch:

| Command | Purpose |
|---------|---------|
| `git rev-parse --show-toplevel` | Repo root. |
| `git symbolic-ref --quiet --short HEAD` | Current branch (or empty / non-zero on detached HEAD). |

The current timestamp comes from `date -u +"%Y-%m-%dT%H:%M:%SZ"` (UTC), and
the filename prefix from `date -u +"%Y%m%d-%H%M%S"`.

### Step 2 — build the slug

The slug is a lowercase, kebab-case, filename-safe string up to 60 chars,
derived from (in priority order):

1. The `name=` argument the user provided.
2. The `task=` text (first ~6 words).
3. Literal `handoff` as last resort.

Replace anything outside `[a-z0-9-]` with `-`, collapse repeated dashes,
strip leading/trailing dashes.

### Step 3 — write the file

Path: `<repo-root>/.claude/handoff/<YYYYMMDD-HHMMSS>-<slug>.md`

Make sure the parent directory exists (`mkdir -p .claude/handoff` on Unix,
`New-Item -ItemType Directory -Force .claude\handoff` on PowerShell).

File contents:

```markdown
---
saved_at: <UTC timestamp, e.g. 2026-05-14T18:00:00Z>
branch: <current branch, or "(no branch)" if detached/no-git>
slug: <slug>
---

# Handoff: <task or slug>

## Current task
<text from task= argument; omit section if empty>

## Decisions made
<text from decisions= argument; omit if empty>

## Open questions
<text from open= argument; omit if empty>

## Files touched
- <path1>
- <path2>
<omit section if empty>

## Next steps
<text from next= argument; omit if empty>

## Notes
<text from notes= argument; omit if empty>
```

If the user passed a full Markdown document (e.g. `from-stdin` style or just
a big block of text), use that as the body verbatim, but still prepend the
YAML frontmatter.

### Step 4 — confirm

Print one line:

```
session-handoff: wrote .claude/handoff/<filename>
```

## Operation: `list`

### Step 1 — list files

```bash
ls -1t <repo-root>/.claude/handoff/*.md
```

(or use Glob with `pattern: ".claude/handoff/*.md"` and sort by mtime
descending). Take the top N (default 10).

### Step 2 — read each file's frontmatter

For each file in the list, read just the first ~10 lines to extract
`saved_at` and `branch` from the YAML frontmatter. Compute "X ago"
from the saved_at timestamp.

### Step 3 — print

```
.claude/handoff/
  20260514-180000-auth-rewrite.md   on skill/auth (3h ago)
  20260513-220000-fix-pagination.md on main (1d ago)
  20260513-100000-spike-graphql.md  on skill/graphql (2d ago)
```

If the directory does not exist or is empty, print:

```
session-handoff: no handoffs found.
```

## Operation: `resume`

### Step 1 — pick the file

- If the user passed `name=<slug>`, glob for `*<slug>*.md` in the handoff
  directory and pick the most recent match.
- Otherwise, pick the most recently modified `*.md` in the handoff directory.
- If no file matches, print
  `session-handoff: error: no handoffs to resume.` and stop.

### Step 2 — print the handoff

Read the file. Strip the YAML frontmatter (everything between the first
two `---` lines). Print a header followed by the body:

```
# resuming <filename> (saved <saved_at> on <branch>, <age>)

<body>
```

Then use the handoff to seed your understanding of the next response — but
verify any file paths or references against the current code before acting
on them (handoffs can go stale).

## Slug examples

| Input | Slug |
|-------|------|
| `name="Auth rewrite"` | `auth-rewrite` |
| `task="Refactor user model + API"` (no name) | `refactor-user-model-api` |
| `task=""` and `name=""` | `handoff` |
| `name="feat/users#42"` | `feat-users-42` |

## Humanizing age

| Seconds since saved | Display |
|---------------------|---------|
| < 60 | `Ns ago` |
| < 3600 | `Nm ago` |
| < 86400 | `Nh ago` |
| ≥ 86400 | `Nd ago` |

## Notes

- Handoff files live under `<repo>/.claude/handoff/`. The `.claude/` folder
  should be in the project's `.gitignore`.
- Resuming a stale handoff (file paths that no longer exist, branch that has
  been deleted) is fine — the data is purely informational. Verify against
  the current code before acting.
- Never overwrite an existing handoff file — the timestamp prefix makes
  collisions effectively impossible, but if one happens, append `-1`, `-2`,
  etc. to the slug.

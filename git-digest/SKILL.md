---
name: git-digest
description: |
  Bundle several git commands (status, log, diff --stat, branch -vv, stash list)
  into a single Markdown digest. Invoke instead of running 4–5 separate git
  commands when you need to understand the working-tree state, recent commits,
  and how the branch relates to its upstream.
---

# git-digest

## When to invoke

Invoke `git-digest` when ANY of these apply:

- You're starting work on an unfamiliar branch and need a quick orientation.
- The user asks "what's going on in this repo?" / "what's left on this branch?" / "what changed lately?".
- You're about to run more than two of: `git status`, `git log`, `git diff --stat`, `git branch -vv`, `git stash list`.

Do NOT invoke when:

- You only need ONE specific piece of git state (just run that one command).
- You're inside a non-git directory.
- The user is asking about a specific commit or file history (use `git log <path>` directly).

## How to invoke

Run from the repo root (or pass `--root`):

```bash
python <skill-dir>/scripts/digest.py [--root <path>] [--commits N] [--against <ref>] [--no-diff]
```

`<skill-dir>` is typically `~/.claude/skills/git-digest/`.

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--root <path>` | `.` | Repo to inspect. |
| `--commits N` | `5` | Number of recent commits to list. |
| `--against <ref>` | upstream (or `HEAD~10`) | Diff stats compared to this ref. |
| `--no-diff` | off | Skip the diffstat section (faster on huge changes). |
| `--quiet` | off | Suppress trailing performance line. |

## What you get back

A single Markdown digest written to stdout:

```markdown
# git-digest — myproject

## Branch
- Current: feature/auth-rewrite
- Tracking: origin/feature/auth-rewrite (ahead 2, behind 0)
- Default: main

## Working tree (3 modified, 1 staged, 2 untracked)
M  src/api/auth.py
M  src/api/users.py
A  tests/test_users.py
?? notes.md

## Recent commits (last 5)
- abc1234 (2h ago) feat: add user create endpoint  — Camilo
- def5678 (1d ago) refactor: extract validation     — Camilo
…

## Diff vs origin/main (4 files, +87 / -12)
- src/api/users.py        +45 / -3
- tests/test_users.py     +30 / -0
- src/api/auth.py         +10 / -8
- src/__init__.py         +2  / -1

## Stash
(empty)
```

Read the digest once and proceed. If you need a full diff, run `git diff <ref>`
directly — the digest tells you which ref to use.

## Notes

- If the branch has no upstream, the digest reports that and falls back to
  `HEAD~10` for the diff section.
- If the working tree is fully clean and HEAD matches its upstream, the digest
  collapses to a single line: `clean working tree, up to date with origin/<branch>`.
- Output is always plain text — safe to read into Claude's context as-is.

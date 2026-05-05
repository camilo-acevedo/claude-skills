---
name: diff-summary
description: |
  Produce a categorized summary of a git diff (stats, top files by lines
  changed, file categories, sample hunks) instead of streaming the full
  diff. Default range is HEAD vs the upstream branch (or main). Use for
  PR review, big refactors, or any change >200 lines you need an
  overview of before deciding what to read in detail.
---

# diff-summary

## When to invoke

Invoke `diff-summary` when ANY of these apply:

- The user asks "what changed in this branch / PR?" or "summarize the diff".
- You need to understand a large changeset (>200 lines) before commenting on it.
- You're about to run `git diff` on something likely to be huge.

Do NOT invoke when:

- The diff is small (<100 lines) — just run `git diff` directly.
- The user asked about a specific file's changes (use `git diff <path>`).
- You need every line of the diff (use `git diff` and read it).

## How to invoke

Run the script. By default it diffs `HEAD` against the tracked upstream (or
`origin/main` if no upstream is configured):

```bash
python <skill-dir>/scripts/summarize.py [--root <path>] [--against <ref>] [--samples N]
```

`<skill-dir>` is typically `~/.claude/skills/diff-summary/`.

Examples:

```bash
python <skill-dir>/scripts/summarize.py                    # HEAD vs upstream
python <skill-dir>/scripts/summarize.py --against main     # HEAD vs main
python <skill-dir>/scripts/summarize.py --against HEAD~5
python <skill-dir>/scripts/summarize.py --staged           # what's staged for commit
```

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--root <path>` | `.` | Repo to inspect. |
| `--against <ref>` | upstream / origin/main | Ref to diff against. |
| `--staged` | off | Use staged changes (vs HEAD) instead of a ref comparison. |
| `--samples N` | `3` | Number of representative hunks to inline. |
| `--top N` | `10` | Files listed in the top-LOC table. |
| `--quiet` | off | Suppress trailing performance hints. |

## What you get back

```markdown
# diff-summary — branch feature/x vs origin/main

## Stats
- 14 files changed, 487 insertions(+), 92 deletions(-)
- Net: +395 lines

## Categories
- src:      9 files  (+412 / -78)
- tests:    3 files  (+62  / -8)
- config:   1 file   (+8   / -2)
- docs:     1 file   (+5   / -4)

## Top files (by total LOC changed)
| File | + | - |
|------|---|---|
| src/api/users.py | 145 | 12 |
| src/api/auth.py  | 87  | 18 |
| ...

## Sample hunks
### src/api/users.py @@ -42,3 +42,9 @@
…

## Path to full diff
git diff origin/main...HEAD
```

## Notes

- "category" is heuristic from the file path (`tests/`, `*.test.ts`, `package.json`,
  `*.md`, etc.). Adjust by reading the table — categories are a hint, not gospel.
- Generated files (lockfiles, build outputs) are listed in their own row and excluded
  from sample hunks.
- For diffs over 1000 changed files the script truncates the file table and reports
  the totals only.

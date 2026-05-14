# diff-summary

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that produces a categorized Markdown summary of a git diff (typical use: PR review, big refactor, branch overview). Instead of streaming a 5000-line `git diff` into Claude's context, the skill returns:

- Total stats (files changed, insertions, deletions, net LOC).
- Files grouped by category (`src` / `tests` / `config` / `docs` / `generated`).
- Top N files by total lines changed.
- Sample first hunks from the most-changed non-generated files.
- The exact `git diff …` command to read the full diff if needed.

> **Estimated savings:** ~80% in code review of large changesets.

## How it works

This skill is **100% Markdown — no Python, no external scripts**. The [`SKILL.md`](SKILL.md) tells Claude exactly which `git diff` commands to run (in parallel), how to categorize files by path glob, and how to render the report. Claude uses its built-in Bash tool.

## Requirements

- `git` available on `PATH`.
- That's it — no Python, no Node, no other runtimes.

## Installation

See the [top-level README](../README.md#installation).

```bash
./install/install.sh diff-summary       # macOS / Linux
```

```powershell
.\install\install.ps1 diff-summary      # Windows
```

## Usage

Inside any Claude Code session:

```
/diff-summary
/diff-summary against=main
/diff-summary staged=true
/diff-summary samples=5 top=15
```

These are free-form arguments — Claude reads them as natural language.

### Supported arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `root=<path>` | cwd / repo root | Repo to inspect. |
| `against=<ref>` | upstream / `origin/main` / `origin/master` / `HEAD~10` | Ref to diff `HEAD` against. |
| `staged=true` | off | Summarize staged changes (`git diff --cached`) instead. |
| `samples=N` | `3` | Number of representative hunks to inline. |
| `top=N` | `10` | Files listed in the top-LOC table. |

## Output example

```markdown
# diff-summary — feature/auth vs origin/main

## Stats
- 14 files changed, 487 insertions(+), 92 deletions(-)
- Net: +395 lines

## Categories
- src:       9 files  (+412 / -78)
- tests:     3 files  (+62  / -8)
- config:    1 file   (+8   / -2)
- docs:      1 file   (+5   / -4)

## Top files (by total LOC changed, generated excluded)
| File | + | - |
|------|---|---|
| src/api/users.py | 145 | 12 |
| src/api/auth.py  | 87  | 18 |
| ...

## Sample hunks

### src/api/users.py @@ -42,3 +42,9 @@
```
…
```

## Path to full diff
git diff origin/main...HEAD
```

## Notes

- Categorization is heuristic from path/extension. The table is a hint, not a contract.
- Generated files (lockfiles, `go.sum`, etc.) are excluded from sample hunks.
- For diffs with > 1000 changed files the file table is truncated to top N; totals are still accurate.

## License

MIT — inherited from the [parent repo](../LICENSE).

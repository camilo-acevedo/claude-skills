# diff-summary

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that produces a categorized Markdown summary of a git diff (typical use: PR review, big refactor, branch overview). Instead of streaming a 5000-line `git diff` into Claude's context, the skill returns:

- Total stats (files changed, insertions, deletions, net LOC).
- Files grouped by category (`src` / `tests` / `config` / `docs` / `ci` / `generated`).
- Top N files by total lines changed.
- Sample first hunks from the most-changed non-generated files.
- The exact `git diff …` command to read the full diff if needed.

> **Estimated savings:** ~80% in code review of large changesets.

## Requirements

- Python 3.8+ (standard library only).
- `git` available on PATH.

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
```

Or run the script directly:

```bash
python ~/.claude/skills/diff-summary/scripts/summarize.py
python ~/.claude/skills/diff-summary/scripts/summarize.py --against main
python ~/.claude/skills/diff-summary/scripts/summarize.py --staged
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--root <path>` | `.` | Repo to inspect. |
| `--against <ref>` | upstream / `origin/main` | Ref to diff `HEAD` against. |
| `--staged` | off | Summarize staged changes (`git diff --cached`) instead. |
| `--samples N` | `3` | Number of representative hunks to inline. |
| `--top N` | `10` | Files listed in the top-LOC table. |

## Output example

```markdown
# diff-summary — myproject

_HEAD vs origin/main_

## Stats
- 14 files changed, 487 insertions(+), 92 deletions(-)
- Net: +395 lines

## Categories
- src: 9 files  (+412 / -78)
- tests: 3 files  (+62 / -8)
- config: 1 file  (+8 / -2)
- docs: 1 file  (+5 / -4)

## Top files (by total LOC changed, top 10)
| File | + | - |
|------|---|---|
| `src/api/users.py` | 145 | 12 |
| `src/api/auth.py`  | 87  | 18 |
| ...

## Sample hunks (3)
### `src/api/users.py` (first hunk)
```diff
@@ -42,3 +42,9 @@
…
```

## Full diff
`git diff origin/main...HEAD`
```

## Notes

- Categorization is heuristic from path/extension. The table is a hint, not a contract.
- Generated files (lockfiles, `go.sum`, etc.) are excluded from sample hunks.
- For diffs with > 1000 changed files the file table is truncated to top N; totals are still accurate.

## License

MIT — inherited from the [parent repo](../LICENSE).

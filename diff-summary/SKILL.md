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

A **Markdown-only** skill — no Python, no scripts. You (Claude) run
`git diff --numstat` and `git diff --stat` in parallel, categorize the files
by path, pick a few representative hunks, and render the report.

## When to invoke

Invoke `diff-summary` when ANY of these apply:

- The user asks "what changed in this branch / PR?" or "summarize the diff".
- You need to understand a large changeset (>200 lines) before commenting on it.
- You're about to run `git diff` on something likely to be huge.

Do NOT invoke when:

- The diff is small (<100 lines) — just run `git diff` directly.
- The user asked about a specific file's changes (use `git diff <path>`).
- You need every line of the diff (use `git diff` and read it).

## Choosing the diff ref

Pick the first that resolves (verify each with `git rev-parse --verify --quiet <ref>`):

1. The user's explicit `against=<ref>` argument.
2. Tracked upstream: `git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'`.
3. `origin/main`.
4. `origin/master`.
5. `HEAD~10`.

Or, if the user passed `staged=true`, skip ref selection and use `--cached`
in the commands below (comparison is staged-vs-HEAD).

## How to run

### Step 1 — gather numbers in parallel

Single Bash batch, all read-only:

| Command | Yields |
|---------|--------|
| `git diff --shortstat <RANGE>` | The `N files changed, X insertions(+), Y deletions(-)` line. |
| `git diff --numstat <RANGE>` | Per-file `<ins>\t<del>\t<path>`. |
| `git rev-parse --abbrev-ref HEAD` | Current branch (for the title). |

Where `<RANGE>` is `<ref>...HEAD` for ref comparisons, or `--cached` for the
staged form.

### Step 2 — parse + categorize

For each numstat row:

- If `ins == "-"` or `del == "-"`, the file is binary — record but exclude
  from the LOC-sum sort.
- Compute `total = ins + del`.
- Assign a **category** by path glob, first match wins:

| Glob (case-insensitive) | Category |
|-------------------------|----------|
| `*.lock`, `package-lock.json`, `poetry.lock`, `pnpm-lock.yaml`, `yarn.lock`, `Cargo.lock`, `go.sum` | `generated` |
| `dist/**`, `build/**`, `out/**`, `__pycache__/**`, `node_modules/**` | `generated` |
| `tests/**`, `test/**`, `*test.go`, `*_test.py`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.js` | `tests` |
| `*.md`, `docs/**`, `README*`, `CHANGELOG*`, `LICENSE*` | `docs` |
| `*.json`, `*.yaml`, `*.yml`, `*.toml`, `*.ini`, `*.cfg`, `Dockerfile*`, `*.env*`, `.github/**`, `.gitlab*` | `config` |
| anything else | `src` |

Sum `ins` and `del` per category.

### Step 3 — pick sample hunks

Pick the top 3 files by `total` LOC changed **excluding `generated`**. For
each, run:

```bash
git diff <RANGE> -- <path>
```

From each output, take the **first hunk only** (the first block starting
with `@@`, up to the next `@@` or end of file). Cap each sample at ~30 lines.
If a sample exceeds 30 lines, truncate and append `… (hunk truncated)`.

Skip the sample step if `samples=0`.

### Step 4 — render

```markdown
# diff-summary — <branch> vs <ref>   (or "staged changes")

## Stats
- <shortstat output, verbatim>
- Net: +<insertions − deletions> lines

## Categories
- src:       <files> files  (+<ins> / -<del>)
- tests:     <files> files  (+<ins> / -<del>)
- config:    <files> files  (+<ins> / -<del>)
- docs:      <files> files  (+<ins> / -<del>)
- generated: <files> files  (+<ins> / -<del>)

(Omit any category with zero files.)

## Top files (by total LOC changed, generated excluded)
| File | + | - |
|------|---|---|
| <path> | <ins> | <del> |
| ... up to `top` rows (default 10) ... |

(If there are more files than the cap, append `… (+N more)` as a final row.)

## Sample hunks

### <path1> @@ <hunk header>
```
<first hunk, ≤30 lines>
```

### <path2> @@ <hunk header>
```
<first hunk>
```

(Up to `samples` blocks; default 3.)

## Path to full diff
git diff <RANGE>
```

If the diff is empty (no files changed), print one line:
`diff-summary: no changes between <RANGE>` and stop.

## Supported arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `root=<path>` | cwd / repo root | Repo to inspect. |
| `against=<ref>` | upstream / origin/main / origin/master / HEAD~10 | Ref to diff against. |
| `staged=true` | off | Use `--cached` (staged-vs-HEAD) instead of a ref comparison. |
| `samples=N` | `3` | Number of sample hunks to include. |
| `top=N` | `10` | Files listed in the top-LOC table. |

## Notes

- "category" is a heuristic from the file path. Use it as a hint, not gospel.
- For >1000 changed files, render only the top table and skip sample hunks;
  point at `git diff <RANGE>` for the rest.
- The full diff command is always shown at the bottom — run it directly if
  the user wants more.

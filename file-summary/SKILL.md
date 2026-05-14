---
name: file-summary
description: |
  Produce or recall a compact summary of a single file (purpose, exported
  symbols with line ranges, notable sections). The summary is cached under
  <repo>/.claude/summaries/ keyed by file hash, so repeated reads of the
  same file cost ~200 tokens instead of the full file's contents. Use
  before reading a large source file you only need an overview of.
---

# file-summary

A **Markdown-only** skill — no Python, no scripts. You (Claude) hash the
target file (`sha256sum` or `Get-FileHash`), check the cache, and if it's a
miss run `grep` against the file to extract exported symbols.

## When to invoke

Invoke `file-summary` when ANY of these apply:

- You are about to `Read` a file > 300 lines and only need an overview.
- The user asks "what's in this file?" or "summarize this file".
- You need to know which symbols a file exports (without their bodies).
- You expect to revisit this file across sessions — the cache amortizes the
  cost.

Do NOT invoke when:

- You need the actual implementation of a specific function (just `Read` it).
- The file is short (< 100 lines) — direct read is cheaper.
- The file is data (CSV / JSON / images) — use the right tool.

## Trade-off vs the old Python parser

The Markdown recipe uses `grep` instead of an AST parser. That means:

- Multi-line declarations, decorators, and dynamic exports may be missed.
- Symbol line ranges are start-only (no end line) — the recipe doesn't try
  to track braces / indentation.
- For Python, `ast`-based parsing would catch more — but for a navigation
  overview, the grep recipe is adequate. Fall back to a direct `Read` when
  you need exact bodies.

## Cache layout

- Directory: `<repo-root>/.claude/summaries/` (find the repo root with
  `git rev-parse --show-toplevel`; if not in a git repo, use the file's
  parent directory).
- One entry per source file: `<sha8>-<basename>.md`
  - `sha8` = first 8 hex chars of sha256 of the file's bytes.
  - `basename` = the file's filename (no path).

## How to run

### Step 1 — hash the file

```bash
sha256sum "<path>" | awk '{print $1}'    # bash
(Get-FileHash -Algorithm SHA256 "<path>").Hash.ToLower()    # PowerShell
```

Record the full hex digest. The first 8 chars are `sha8`.

### Step 2 — check the cache

Glob `<cache-dir>/<sha8>-*.md`. If exactly one file matches AND its
frontmatter contains the same full sha256 → cache hit. Print the file's
body and stop.

If `refresh=true` was passed, skip the cache check and proceed to compute.

### Step 3 — compute the summary

#### Detect language

By extension (same table as codemap):
- `.py` → Python
- `.ts`, `.tsx`, `.mts`, `.cts` → TypeScript
- `.js`, `.jsx`, `.mjs`, `.cjs` → JavaScript
- `.go` → Go
- anything else → generic fallback

#### Gather pieces (single parallel Bash batch)

| Command | Yields |
|---------|--------|
| `wc -l "<path>"` | Total line count. |
| `head -n 30 "<path>"` | First 30 lines (for purpose + imports). |
| `tail -n 10 "<path>"` | Last 10 lines (for `__all__`, exports block, etc.). |
| Language-specific symbol greps (see codemap SKILL.md) | Exported top-level symbols. |

For Python imports, grep:
```
grep -nE '^(from\s+\S+\s+import|import\s+\S)' "<path>" | head -n 20
```

For TS/JS imports:
```
grep -nE '^import\s' "<path>" | head -n 20
```

For Go imports:
```
grep -nE '^import\s' "<path>"
```
Plus the multi-line `import ( … )` block (look for `^import\s*\($` then read
until matching `^)$`).

#### Extract the file's purpose

Same rule as codemap (first docstring / JSDoc / package comment / humanized
filename).

#### Cap symbols at `max=N` (default 40).

### Step 4 — render

```markdown
---
path: <path>
sha256: <full digest>
generated_at: <UTC timestamp>
language: <python|typescript|javascript|go|other>
lines: <count>
---

# <path> — <one-line purpose>

<lines> lines • <Language>

## Imports
- <module> (<symbols if any>)
- …

## Exports
- L<N>  <signature snippet>
- L<N>  <signature snippet>
- …

## Head (first 10 lines)
```
<head>
```

## Tail (last 5 lines)
```
<tail>
```
```

Write it to `<cache-dir>/<sha8>-<basename>.md` (unless `nocache=true`).
Then print the body (without frontmatter) to the user.

## Supported arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `path` (first positional) | required | File to summarize. |
| `root=<path>` | nearest `.git` ancestor or file's parent | Cache base. |
| `refresh=true` | off | Ignore cache, regenerate. |
| `max=N` | `40` | Cap on listed symbols. |
| `nocache=true` | off | Compute and print without writing the cache. |

## Notes

- The `.claude/summaries/` folder should be in `.gitignore` (or just
  `.claude/`).
- Stale cache entries from earlier versions of a file accumulate over time.
  Periodic cleanup is fine — but optional, since matching is by full sha256.
- If the file is binary (sha256 succeeds but `head` returns gibberish),
  bail out with `file-summary: <path> looks binary — skipping` and stop.

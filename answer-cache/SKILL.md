---
name: answer-cache
description: |
  Cache Q&A about the codebase keyed by a normalized question + linked
  source files. The first time a question is asked, research it, then
  save the answer with the files it depends on. Future asks return the
  cached answer instantly — but if any linked file's sha256 has changed,
  the entry is reported as stale and you re-research. Use to avoid
  re-exploring the same concept across sessions.
---

# answer-cache

A **Markdown-only** skill — no Python, no scripts. Each cache entry is a
single Markdown file with YAML frontmatter under `<repo>/.claude/answers/`.
Hashing uses `sha256sum` (Git Bash / Linux / macOS) or `Get-FileHash`
(PowerShell).

## When to invoke

Four operations:

### `ask`
Invoke at the start of any "where is …?" / "how does … work?" / "what calls
…?" question, **before** doing any Glob/Grep/Read of your own. If the cache
has a fresh answer, you save the entire research roundtrip.

### `save`
Invoke immediately after you've answered a question via research. Pass the
files you actually consulted — the cache uses them as the freshness key.

### `list`
Invoke when the user asks "what have we cached?" or to audit the cache.

### `forget`
Invoke when the user says a cached answer is wrong, or to manually invalidate.

## Where things live

- Directory: `<repo-root>/.claude/answers/`
- One entry per file: `<slug>-<qhash8>.md`
  - `slug` = first ~40 chars of the kebab-cased normalized question.
  - `qhash8` = first 8 hex chars of sha256 of the normalized question.
- Optional convenience: `index.md` listing all entries (rebuild on save/forget).

## Question normalization (use this for ALL lookups)

To compute the normalized form:

1. Lowercase.
2. Strip punctuation — replace every char outside `[a-z0-9\s]` with a space.
3. Collapse runs of whitespace to a single space.
4. Trim.

Then `qhash8` = first 8 hex chars of `sha256(normalized)`.

## File layout (per entry)

```markdown
---
question: "<original question, verbatim>"
normalized: "<normalized question>"
saved_at: 2026-05-14T18:00:00Z
files:
  - path: src/api/middleware/auth.py
    sha256: 3f5e…   # full 64-hex sha256 of the file's current bytes
  - path: src/auth/jwt.py
    sha256: 9a12…
---

<answer body — Markdown>
```

Use exactly that frontmatter shape so `ask` can parse it with simple line
patterns.

## Operation: `ask`

### Step 1 — locate the entry

```bash
QNORM="<normalized question>"
QHASH8="<first 8 hex chars of sha256($QNORM)>"
```

Glob for `<repo-root>/.claude/answers/*-$QHASH8.md`. Exactly one file should
match (collisions in 8 hex chars are extremely unlikely for the small entry
counts a single project will have, but if there is more than one match,
read each one's `normalized:` line and pick the exact match).

If no match: print `answer-cache: miss for "<question>"` and stop. The
caller should research and call `save`.

### Step 2 — check freshness

Read the entry's frontmatter. For each `files:` row:

- Compute the current sha256 of `path`:
  - Bash: `sha256sum "<path>" | awk '{print $1}'`
  - PowerShell: `(Get-FileHash -Algorithm SHA256 "<path>").Hash.ToLower()`
- If the file no longer exists, count it as stale.
- If the computed hash differs from the stored hash, count it as stale.

Run these hash commands in **a single parallel Bash batch** — one per file.

### Step 3 — render

#### Fresh (no stale files):

```
# answer-cache: hit (saved <saved_at>, <age>)

<answer body>
```

Exit-equivalent: the cached answer is good — use it without further research.

#### Stale (one or more files changed):

```
answer-cache: STALE (<N>/<total> linked files changed: <path1>, <path2>[, …])

(prior answer follows, treat as outdated:)

<answer body>
```

Re-research the question, then call `save` to overwrite.

## Operation: `save`

### Step 1 — collect inputs

The caller provides:
- The original question.
- The answer body (Markdown).
- A list of files consulted (paths relative to repo root).

### Step 2 — compute hashes

Run in a parallel Bash batch:

```bash
sha256sum "<file1>" "<file2>" "<file3>" …
```

Or per-file with `Get-FileHash` on PowerShell. Record the lowercase hex digest
of each file.

### Step 3 — write the entry

```bash
mkdir -p .claude/answers
```

Write to `.claude/answers/<slug>-<qhash8>.md` (overwrite if exists). Use the
frontmatter shape shown above. The timestamp is `date -u +"%Y-%m-%dT%H:%M:%SZ"`.

If the question normalizes to the same hash as an existing entry, overwrite
that entry (intentional behavior — re-research means new answer).

### Step 4 — confirm

```
answer-cache: saved (<N> files linked: <file1>, <file2>, …)
```

## Operation: `list`

### Step 1 — enumerate

```bash
ls -1t <repo-root>/.claude/answers/*.md
```

(Or Glob `pattern: ".claude/answers/*.md"`, sorted by mtime descending.)

### Step 2 — read each frontmatter

For each file, extract `question`, `saved_at`, and the count of `files:` rows.
Compute age from `saved_at`.

### Step 3 — print

```
.claude/answers/  (<count> entries)
- <question>                  <N> files (saved <age>)
- <question>                  <N> files (saved <age>)
…
```

Cap at `limit=N` (default 20).

If the directory is empty or doesn't exist, print
`answer-cache: no entries.` and stop.

## Operation: `forget`

### Step 1 — compute the hash

Same normalization + `qhash8` as `ask`.

### Step 2 — delete

```bash
rm -f <repo-root>/.claude/answers/*-$QHASH8.md
```

### Step 3 — confirm

If a file was deleted, print:
```
answer-cache: forgot "<question>"
```

If none matched:
```
answer-cache: no entry to forget for "<question>"
```

## Age helper

| Seconds since saved | Display |
|---------------------|---------|
| < 60 | `Ns ago` |
| < 3600 | `Nm ago` |
| < 86400 | `Nh ago` |
| ≥ 86400 | `Nd ago` |

## Notes

- Entries live under `<repo>/.claude/answers/`. The `.claude/` folder should
  be in `.gitignore`.
- Wrong cached answers are worse than no cache at all — when in doubt about
  a hit, re-verify against the actual files before responding to the user.
- v1 matches questions exactly after normalization. If you need to vary
  phrasing, save twice — once under each form.
- New files matching the question are NOT detected automatically — staleness
  is only triggered by content changes to **already-linked** files.

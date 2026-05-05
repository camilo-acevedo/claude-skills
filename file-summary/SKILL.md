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

## How to invoke

```bash
python <skill-dir>/scripts/summarize.py <path> [--root <repo-root>] [--refresh]
```

`<skill-dir>` is typically `~/.claude/skills/file-summary/`.

Examples:

```bash
python <skill-dir>/scripts/summarize.py src/api/users.py
python <skill-dir>/scripts/summarize.py ./big_module.py --refresh
python <skill-dir>/scripts/summarize.py path/to/Component.tsx
```

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `path` (positional) | required | File to summarize. |
| `--root <path>` | nearest `.git` or cwd | Where to put the cache (`<root>/.claude/summaries/`). |
| `--refresh` | off | Ignore cache, regenerate. |
| `--max-symbols N` | `40` | Cap on listed symbols per file. |
| `--no-cache` | off | Compute and print without writing the cache. |
| `--quiet` | off | Suppress trailing performance hints. |

## What you get back

```markdown
# src/api/users.py — CRUD endpoints for /users

312 lines • Python • cached: hit (sha 7f3a..)

## Imports
- fastapi (APIRouter, Depends)
- sqlalchemy.orm (Session)
- ..domain.user (User)
- ..infra.db (get_session)

## Exports
- def list_users(session: Session) -> list[User]      L24-32
- def create_user(payload: CreateUserDTO) -> User     L35-58
- class UserRouter                                    L60-145
  - .add_user                                         L70-90
  - .delete_user                                      L92-110
- USER_SCHEMA: dict                                   L18

## Notable sections
- L1-22: imports + setup
- L24-58: simple handlers
- L60-145: router class
- L147-312: private helpers (`_*`)
```

If the file's hash hasn't changed since the last run, the cached summary is
returned instantly (the `cached: hit` field in the header).

## Languages with structured parsing

- **Python** — `ast`-based: function / class / annotated constants.
- **TypeScript / JavaScript** (incl. `.tsx`, `.jsx`) — regex over `export …`.
- **Go** — regex over exported `func` / `type` / `var` / `const`.

For other languages the script falls back to: file size, head (first 30
lines), tail (last 10 lines), and a list of lines matching `^(def|class|function|interface|fn|public|export)\b`.

## Cache layout

`<root>/.claude/summaries/<sha256-prefix>-<filename>.md`

The cache is keyed by the file's full sha256 (stored inside the markdown
header) — the prefix is just for human-readable filenames. Stale entries are
ignored, not deleted; run with `--refresh` to overwrite.

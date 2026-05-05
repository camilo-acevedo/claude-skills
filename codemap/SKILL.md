---
name: codemap
description: |
  Generate a single CODEMAP.md at the repo root containing a filtered file
  tree, a one-line purpose for each source file, and exported top-level
  symbols (functions, classes, constants). Invoke at the start of a new
  conversation in an unfamiliar repo to avoid spending tokens on repeated
  Glob / Grep / Read exploration. Supports Python, TypeScript/JavaScript,
  and Go for symbol extraction; other files appear in the tree only.
---

# codemap

## When to invoke

Invoke `codemap` when ANY of these apply:

- This is a new conversation in a repository you have not explored yet.
- The user asks "where is X?" without giving a path.
- You are about to make 3+ `Glob` / `Grep` calls just to understand layout.
- The user explicitly types `/codemap` or asks to "regenerate the codemap".

Do NOT invoke when:

- A fresh `CODEMAP.md` already exists at the repo root and was generated today
  (read it instead).
- The task is scoped to one file whose path is already known.
- The repo is trivial (< 10 source files) — direct exploration is cheaper.

## How to invoke

Run the generator script with the project root as the current working
directory. The script is plain Python 3.8+ with no third-party dependencies.

```bash
python <skill-dir>/scripts/generate.py [--root <subdir>] [--refresh] [--max-symbols N]
```

`<skill-dir>` is the directory where this `SKILL.md` lives (typically
`~/.claude/skills/codemap/`). On Windows the same command works with
`python` or `py`.

Common flags:

- `--root <subdir>` — index only this subtree (useful in monorepos).
- `--refresh` — ignore the cache and re-parse every file.
- `--max-symbols N` — cap symbols listed per file (default 30).
- `--include-tests` — include test files in the main tree (default: separate section).

## What you get back

The script writes `CODEMAP.md` to the repo root and prints to stdout:

```
codemap: wrote CODEMAP.md (142 files, 89 with symbols, 0.4s)
cache: 138 reused, 4 reparsed
```

Read `CODEMAP.md` once, then proceed with the user's task. The map gives you:

1. A filtered tree (respects `.gitignore`, skips `node_modules`, `.venv`, etc.).
2. A one-line purpose per source file (extracted from module docstrings or
   leading comments — falls back to a humanized filename).
3. Public top-level symbols with their signatures.

If a symbol you need is not in the map, fall back to `Grep` for the precise
location. The map is a navigation aid, not an exhaustive index.

## Cache and freshness

Per-project cache lives at `<repo>/.claude/codemap-cache.json`. The script
re-parses only files whose `mtime` or `sha256` changed since last run, so
regenerating after small edits is fast.

If `CODEMAP.md` shows a `Generated:` timestamp older than 7 days OR the user
mentions structural changes (new modules, renames, deletions), re-run with
`--refresh` before relying on it.

## Notes

- `CODEMAP.md` and `.claude/codemap-cache.json` are derived artifacts — the
  script will offer to add them to the repo's `.gitignore` if missing.
- For repos with > 5000 files the script aborts and asks for `--root <subdir>`.
- Parser errors on individual files are non-fatal; the file appears in the
  tree marked `(parse error)` and processing continues.

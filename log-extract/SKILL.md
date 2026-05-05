---
name: log-extract
description: |
  Extract relevant lines from a large log file: error / warning / panic /
  traceback patterns plus N lines of surrounding context, with deduplicated
  stack traces. Returns a compact summary instead of streaming the whole
  log into Claude's context. Use for production logs, Sentry exports,
  test output captured to disk, debug traces, etc.
---

# log-extract

## When to invoke

Invoke `log-extract` when ANY of these apply:

- The user points you at a log file and asks "what's wrong?" or "find the error".
- You're about to `cat` / `Read` a log file larger than ~500 lines.
- You need to find specific events in a log without paying for the whole file.

Do NOT invoke when:

- The log is small (<200 lines) — just read it.
- The user wants a specific exact section (use `Read` with line offsets).
- The file is structured data (JSON/CSV) — use the right parser instead.

## How to invoke

Pass the log path; optionally a regex pattern to override the default error filter:

```bash
python <skill-dir>/scripts/extract.py <path> [pattern] [flags]
```

`<skill-dir>` is typically `~/.claude/skills/log-extract/`.

Examples:

```bash
python <skill-dir>/scripts/extract.py /var/log/app.log
python <skill-dir>/scripts/extract.py /tmp/test-output.log "TimeoutError"
python <skill-dir>/scripts/extract.py logs/server.log --context 5 --max-hits 50
```

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--context N` | `2` | Lines of context shown around each match. |
| `--max-hits N` | `30` | Cap on hit groups shown; remaining are counted. |
| `--no-dedup` | off | Disable stack-trace deduplication. |
| `--head N` | `0` | Always include the first N lines (helps with banner / config dumps). |
| `--tail N` | `5` | Always include the last N lines. |
| `--quiet` | off | Suppress trailing performance hints. |

The default pattern matches: `error`, `errno`, `exception`, `traceback`, `failed`, `failure`, `panic`, `fatal`, `WARN`, `WARNING` (case-insensitive). Pass a custom pattern to override.

## What you get back

```
log-extract: /var/log/app.log (12480 lines, 184 hits → 12 unique)

head (5):
  2026-05-04 18:00:01 INFO server starting on :8080
  ...

hits:

[×3 — first at 14:02:01, last at 14:05:33]
  2026-05-04 14:02:00 INFO request POST /api/users
  2026-05-04 14:02:01 ERROR DB connection refused
  2026-05-04 14:02:01 INFO retrying...

[×1 at 14:08:11]
  2026-05-04 14:08:10 INFO request GET /api/health
  2026-05-04 14:08:11 ERROR FATAL out of memory
  2026-05-04 14:08:11 INFO shutting down

… (+9 more hit groups)

tail (5):
  2026-05-04 18:30:00 INFO graceful shutdown complete
  ...
```

## Notes

- Deduplication: hits whose normalized message (stripped timestamps, stripped
  numbers in addresses/PIDs/line numbers) is identical are collapsed into one
  group with a count.
- The script processes the log in a streaming fashion — files in the GB range
  are fine as long as Python can `open()` them.
- For binary files or non-UTF-8 logs the script falls back to `errors='replace'`
  during read.

# log-extract

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill for working with large log files (production logs, Sentry exports, debug traces, captured test output). Instead of reading the full file, the skill extracts only:

- Lines matching error / warning / panic / traceback patterns (or a user-supplied regex).
- N lines of surrounding context per hit (default 2).
- Deduplicated stack traces — repeated events collapse into a single group with a count.
- Optional head / tail of the file (banners, shutdown lines).

> **Estimated savings:** a 50K-line log can collapse into a 100-line response.

## How it works

This skill is **100% Markdown — no Python, no external scripts**. The [`SKILL.md`](SKILL.md) tells Claude how to run `grep -nC` against the log to gather candidate hits, then how to normalize and deduplicate them in-memory. Claude uses its built-in Bash tool.

## Requirements

- A POSIX shell with `grep`, `head`, `tail`, `wc` (Claude Code's built-in Bash tool on all platforms).
- That's it — no Python, no Node, no ripgrep.

## Installation

See the [top-level README](../README.md#installation).

```bash
./install/install.sh log-extract        # macOS / Linux
```

```powershell
.\install\install.ps1 log-extract       # Windows
```

## Usage

Inside any Claude Code session:

```
/log-extract /var/log/app.log
/log-extract /tmp/test-output.log pattern="TimeoutError"
/log-extract logs/server.log context=5 max=50
```

These are free-form arguments — Claude reads them as natural language.

### Supported arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `path` (first positional) | required | Log file to read. |
| `pattern="<regex>"` | error/warn default | POSIX-extended regex to filter lines (case-insensitive). |
| `context=N` | `2` | Lines of context shown around each match. |
| `max=N` | `30` | Cap on hit groups shown. |
| `nodedup=true` | off | Disable stack-trace deduplication. |
| `head=N` | `0` | Lines from the start always included. |
| `tail=N` | `5` | Lines from the end always included. |

The default pattern matches: `error`, `errno`, `exception`, `traceback`, `failed`, `failure`, `panic`, `fatal`, `WARN`, `WARNING` (case-insensitive).

## Output example

```
log-extract: /var/log/app.log (12480 lines, 184 hits → 12 unique)

hits:

[×3 — first at 14:02:01, last at 14:05:33]
  2026-05-14 14:02:00 INFO request POST /api/users
  2026-05-14 14:02:01 ERROR DB connection refused
  2026-05-14 14:02:01 INFO retrying...

[×1 at 14:08:11]
  2026-05-14 14:08:10 INFO request GET /api/health
  2026-05-14 14:08:11 ERROR FATAL out of memory
  2026-05-14 14:08:11 INFO shutting down

… (+9 more hit groups)

tail (5):
  2026-05-14 18:30:00 INFO graceful shutdown complete
```

## How dedup works

A hit's matched line is normalized (timestamps stripped, ANSI escapes stripped, numbers collapsed to `N`) and used as the dedup key. Two hits whose normalized lines match are merged into one group with a `×N` count and the first/last seen times.

Pass `nodedup=true` to see every hit.

## License

MIT — inherited from the [parent repo](../LICENSE).

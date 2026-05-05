# log-extract

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill for working with large log files (production logs, Sentry exports, debug traces, captured test output). Instead of reading the full file, the skill extracts only:

- Lines matching error / warning / panic / traceback patterns (or a user-supplied regex).
- N lines of surrounding context per hit (default 2).
- Deduplicated stack traces — repeated events collapse into a single group with a count.
- Optional head / tail of the file (banners, shutdown lines).

> **Estimated savings:** a 50K-line log can collapse into a 100-line response.

## Requirements

- Python 3.8+ (standard library only — no third-party packages, no ripgrep).

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
/log-extract /path/to/log
/log-extract /path/to/log "TimeoutError"
```

Or run the script directly:

```bash
python ~/.claude/skills/log-extract/scripts/extract.py /var/log/app.log
python ~/.claude/skills/log-extract/scripts/extract.py /tmp/test.log "TimeoutError" --context 5
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `path` (positional) | required | Log file to read. |
| `pattern` (positional) | error/warn default | Regex to filter lines. |
| `--context N` | `2` | Lines of context shown around each match. |
| `--max-hits N` | `30` | Cap on hit groups shown. |
| `--no-dedup` | off | Disable stack-trace deduplication. |
| `--head N` | `0` | Lines from the start always included. |
| `--tail N` | `5` | Lines from the end always included. |

The default pattern matches: `error`, `errno`, `exception`, `traceback`, `failed`, `failure`, `panic`, `fatal`, `WARN`, `WARNING` (case-insensitive).

## Output example

```
log-extract: /var/log/app.log (12480 lines, 184 hits → 12 unique)

hits:

[×3 — first at line 4521, last at line 6210]
  2026-05-04 14:02:00 INFO request POST /api/users
  2026-05-04 14:02:01 ERROR DB connection refused
  2026-05-04 14:02:01 INFO retrying...

[×1 at line 8011]
  2026-05-04 14:08:10 INFO request GET /api/health
  2026-05-04 14:08:11 ERROR FATAL out of memory
  2026-05-04 14:08:11 INFO shutting down

… (+9 more hit groups)

tail (5):
  2026-05-04 18:30:00 INFO graceful shutdown complete
```

## How dedup works

A hit's center line is normalized (timestamps stripped, hex addresses replaced, large numeric IDs collapsed) and used as the dedup key. Two hits whose normalized centers match are merged into one group with a `×N` count and the first/last line numbers.

Pass `--no-dedup` to see every hit.

## License

MIT — inherited from the [parent repo](../LICENSE).

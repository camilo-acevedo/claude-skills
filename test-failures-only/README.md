# test-failures-only

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that runs a test suite and returns **only the failing tests** with condensed tracebacks. If everything passes, the response is a single line.

Auto-detects **pytest**, **jest**, **vitest**, and **go test** from the command. Falls back to a generic `FAIL/ERROR` line filter for other runners.

> **Estimated savings:** a verbose 200-test suite output (~15K tokens) becomes a ~500-token digest. Clean runs collapse to one line.

## Requirements

- Python 3.8+ (standard library only).
- Whatever test runner you want to wrap.

## Installation

See the [top-level README](../README.md#installation).

```bash
./install/install.sh test-failures-only        # macOS / Linux
```

```powershell
.\install\install.ps1 test-failures-only       # Windows
```

## Usage

Inside any Claude Code session:

```
/test-failures-only pytest -v
```

Or run the script directly. The test command goes after `--`:

```bash
python ~/.claude/skills/test-failures-only/scripts/run_tests.py -- pytest -v
python ~/.claude/skills/test-failures-only/scripts/run_tests.py -- npx jest
python ~/.claude/skills/test-failures-only/scripts/run_tests.py -- go test ./...
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--root <path>` | cwd | Working directory; logs go under `<root>/.claude/test-logs/`. |
| `--framework <name>` | auto | Force a parser (`pytest`, `jest`, `vitest`, `go`, `generic`). |
| `--max-failures N` | `20` | Cap on failures shown. |
| `--no-trace` | off | Show only failing test names, no traceback snippet. |
| `--shell` | off | Run via the system shell. |
| `--quiet` | off | Suppress the leading `$ <cmd>` line. |

## Auto-injected flags

To keep output compact without forcing the user to remember runner-specific flags, the wrapper injects:

- `pytest` → adds `--tb=line` if no `--tb` was passed.
- `go test` → adds `-json` so events can be parsed structurally.

`jest` / `vitest` are not modified — pass `--reporters=json` yourself if you want JSON parsing instead of regex parsing.

## Output examples

**Clean pytest run:**

```
$ pytest
OK — 174 passed in 2.34s  •  log: .claude/test-logs/20260504-203000-pytest.log
```

**Failing pytest run:**

```
$ pytest --tb=line
FAIL — 3 failed, 174 passed in 4.21s
log: .claude/test-logs/20260504-203012-pytest.log

✗ tests/test_users.py::test_create
    AssertionError: expected 200, got 500

✗ tests/test_users.py::test_update
    KeyError: 'user_id'

✗ tests/test_admin.py::test_delete
    TimeoutError after 30s
```

**Crash with no parseable failures:** falls back to the last 20 log lines so you can see what happened.

## Limitations

- For jest/vitest the regex parser catches `FAIL ` / `●` / `×` markers; for cleaner detail, pass `--reporters=json`.
- The `generic` parser is a coarse line filter — only use when no framework is detected.
- Long tracebacks are truncated to the first non-empty lines per failure.

## License

MIT — inherited from the [parent repo](../LICENSE).

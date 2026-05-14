# test-failures-only

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that runs a test suite and returns **only the failing tests** with condensed tracebacks. If everything passes, the response is a single line.

Auto-detects **pytest**, **jest**, **vitest**, and **go test** from the command. Falls back to a generic `FAIL/ERROR` line filter for other runners.

> **Estimated savings:** a verbose 200-test suite output (~15K tokens) becomes a ~500-token digest. Clean runs collapse to one line.

## How it works

This skill is **100% Markdown — no Python, no external scripts**. The [`SKILL.md`](SKILL.md) lays out the framework-detection rules, the per-framework parsing recipes, and the output format. Claude runs the command with output redirected to a log, then parses it using `grep` + framework-specific knowledge.

## Requirements

- A POSIX shell or PowerShell (Claude Code's built-in Bash tool works on all platforms).
- Whatever test runner you want to wrap.
- No Python, no Node, no other runtimes.

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
/test-failures-only npx jest
/test-failures-only go test ./...
/test-failures-only framework=pytest -- python -m pytest tests/
```

These are free-form arguments — Claude reads them as natural language. You can also just say "run the tests and only show me the failures".

### Supported arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `root=<path>` | cwd | Working directory; logs under `<root>/.claude/test-logs/`. |
| `framework=<name>` | auto | Force a parser (`pytest`, `jest`, `vitest`, `go`, `generic`). |
| `max=N` | `20` | Cap on failures shown. |
| `notrace=true` | off | Show only failing test names, no traceback snippet. |

## Auto-injected flags

To keep output compact without forcing the user to remember runner-specific flags, the skill injects:

- `pytest` → adds `--tb=line` if no `--tb` was passed; adds `-q` if no verbosity flag.
- `go test` → adds `-json` so events can be parsed structurally.

`jest` / `vitest` are not modified — they're quiet enough by default.

## Output examples

**Clean pytest run:**

```
$ pytest -q
OK — 174 passed in 2.34s  •  log: .claude/test-logs/20260514-203000-pytest.log
```

**Failing pytest run:**

```
$ pytest --tb=line -q
FAIL — 3 failed, 174 passed in 4.21s
log: .claude/test-logs/20260514-203012-pytest.log

✗ tests/test_users.py::test_create
    AssertionError: expected 200, got 500

✗ tests/test_users.py::test_update
    KeyError: 'user_id'

✗ tests/test_admin.py::test_delete
    TimeoutError after 30s
```

**Crash with no parseable failures:** falls back to the last 20 log lines so you can see what happened.

## Limitations

- For jest/vitest the parser catches `●` markers; for cleaner detail, pass `--reporters=json` and Claude will parse it.
- The `generic` parser is a coarse line filter — only use when no framework is detected.
- Long tracebacks are truncated to the first non-empty lines per failure.

## License

MIT — inherited from the [parent repo](../LICENSE).

---
name: test-failures-only
description: |
  Run a test suite and return ONLY the failing tests with condensed
  tracebacks. If every test passes, return one line. Supports pytest
  (Python), jest / vitest (JS/TS), and go test out of the box; falls
  back to a generic FAIL/ERROR line filter for other runners.
---

# test-failures-only

## When to invoke

Invoke `test-failures-only` instead of running the test command directly when:

- You need to know which tests fail and why, but not what passed.
- The test suite is large (>50 tests) and the verbose output would dominate the conversation.
- The user asks "are tests passing?" / "what's failing?" / "run the tests".

Do NOT invoke when:

- The user specifically asks to see all test output (use `run-quiet --no-trim` instead).
- You need to debug a single specific test (run that test directly).
- The command is something other than a test runner.

## How to invoke

Pass the test command after `--`:

```bash
python <skill-dir>/scripts/run_tests.py [flags] -- <test-command> [args...]
```

Examples:

```bash
python <skill-dir>/scripts/run_tests.py -- pytest -v
python <skill-dir>/scripts/run_tests.py -- npx jest
python <skill-dir>/scripts/run_tests.py -- go test ./...
python <skill-dir>/scripts/run_tests.py --framework pytest -- python -m pytest tests/
```

`<skill-dir>` is typically `~/.claude/skills/test-failures-only/`.

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--root <path>` | cwd | Working directory; full output saved under `<root>/.claude/test-logs/`. |
| `--framework <name>` | auto-detected | Force a parser (`pytest`, `jest`, `vitest`, `go`, `generic`). |
| `--max-failures N` | `20` | Cap on failures shown. Remaining are counted. |
| `--no-trace` | off | Show only the failing test names, not the traceback snippet. |
| `--shell` | off | Run via system shell (allows pipes, env interpolation). |
| `--quiet` | off | Suppress the leading `$ <cmd>` line. |

## What you get back

Clean run (everything passes):

```
$ pytest
OK — 174 passed in 2.34s  •  log: .claude/test-logs/20260504-203000-pytest.log
```

Failing run:

```
$ pytest
FAIL — 3 failed, 174 passed in 4.21s
log: .claude/test-logs/20260504-203012-pytest.log

✗ tests/test_users.py::test_create
    AssertionError: expected 200, got 500

✗ tests/test_users.py::test_update
    KeyError: 'user_id'

✗ tests/test_admin.py::test_delete
    TimeoutError after 30s
```

If the runner crashes before producing parseable output, the digest falls back
to the last 20 lines of the log so you can see what happened.

## Notes

- For pytest, `--tb=line` is added if the user did not pass any `--tb` flag,
  to keep tracebacks compact.
- For jest / vitest, no flag injection is done; if you want JSON output, pass
  `--reporters=json` yourself and the parser will pick it up.
- For go test, the parser auto-adds `-json` if not already present so it can
  parse structured events.
- Logs accumulate in `.claude/test-logs/`. The `.claude/` folder should be in
  the project's `.gitignore`.

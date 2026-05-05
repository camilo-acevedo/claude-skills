# test-failures-only

Part of the [claude-skills](../README.md) collection.

> 🚧 **Planned, not yet implemented.**

A planned [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that runs a test suite and returns **only the failures** with condensed tracebacks. If everything passes, it returns a single line: `OK (174/174 in 2.1s)`.

Supports `pytest` (Python) and `jest` / `vitest` (JS/TS) out of the box; falls back to parsing exit codes for unknown runners.

Implementation notes:

- For pytest: `pytest --tb=line -q` parsing, or `pytest-json-report` for cleaner output.
- For jest/vitest: `--reporters=json` + filter to `numFailedTests > 0`.
- Full output saved to `.claude/test-logs/<hash>.log` so Claude can request it on demand.

> **Estimated savings:** a verbose 200-test suite output is ~15K tokens; the digest is ~500.

Tracking issue: TBD.

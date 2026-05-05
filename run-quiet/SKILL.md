---
name: run-quiet
description: |
  Wrap a verbose command (pytest, npm run build, terraform plan, etc.).
  The full output is saved to a log file; only the exit code, the matched
  error/warning lines, and the last few lines are returned. Read the log
  on demand if more context is needed. Use instead of running verbose
  commands directly when their output is large or noisy.
---

# run-quiet

## When to invoke

Invoke `run-quiet` when ANY of these apply:

- The command's output is likely to be over ~200 lines (build tools, test
  suites, terraform plan, infrastructure scans, package install logs, etc.).
- You only need to know whether the command succeeded and, if not, why.
- The command is verbose by design (`-v`, `--verbose`) but you want a digest.

Do NOT invoke when:

- The command is interactive (asks for input).
- The output IS the answer the user wants (e.g. `cat`, `git show`, `jq`).
- The command is short and you need every line (e.g. `git status --porcelain`).

## How to invoke

The script wraps a single command. Pass the command as a list of arguments
after `--`:

```bash
python <skill-dir>/scripts/run.py [flags] -- <command> [args...]
```

`<skill-dir>` is typically `~/.claude/skills/run-quiet/`.

Examples:

```bash
python <skill-dir>/scripts/run.py -- pytest -v
python <skill-dir>/scripts/run.py -- npm run build
python <skill-dir>/scripts/run.py --shell -- "pytest -v 2>&1 | tee out.txt"
```

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--root <path>` | cwd | Directory to run in; logs are written under `<root>/.claude/run-logs/`. |
| `--max-lines N` | `30` | Cap on matched-error lines shown in the digest. |
| `--tail N` | `10` | Lines from the end of the output to always include. |
| `--head N` | `0` | Lines from the start to always include (helpful for build banners). |
| `--shell` | off | Run via the system shell (allows pipes, redirection, env interpolation). |
| `--no-trim` | off | Skip the digest; print the full output (useful when the digest hides what you need). |
| `--timeout N` | none | Kill the command after N seconds. |
| `--quiet` | off | Suppress the leading `$ <cmd>` line. |

## What you get back

A short report on stdout. Example for a failing pytest run:

```
$ pytest -v
exit: 1 (in 4.21s)
log:  .claude/run-logs/abc123.log (1842 lines)

errors (3):
  tests/test_users.py::test_create FAILED
    AssertionError: expected 200, got 500
  tests/test_users.py::test_update FAILED
    KeyError: 'user_id'
  tests/test_admin.py::test_delete FAILED
    TimeoutError after 30s

tail (10):
  ============================== short test summary info ==============================
  FAILED tests/test_users.py::test_create
  FAILED tests/test_users.py::test_update
  FAILED tests/test_admin.py::test_delete
  ============================== 3 failed, 174 passed in 4.21s ==============================
```

If the command exits 0 with no errors detected, the digest collapses:

```
$ npm run build
exit: 0 (in 12.30s)  •  log: .claude/run-logs/def456.log (542 lines)
clean — last line: "✓ Compiled successfully"
```

If you need the full output, read the log file at the path shown.

## Notes

- Logs accumulate in `.claude/run-logs/`. Add `.claude/run-logs/` to your
  project's `.gitignore` (or just `.claude/`).
- The digest looks for generic patterns (error / failed / panic / traceback)
  plus a few framework-specific ones (pytest `FAILED`, jest `FAIL`, Go
  `--- FAIL:`). False negatives are possible — if the digest looks too
  clean for a failing exit code, fall back to `--no-trim` or read the log.
- On Windows, prefer the explicit argument form (without `--shell`) when
  possible. With `--shell`, the platform default shell is used (`cmd` on
  Windows, `/bin/sh` on Unix).

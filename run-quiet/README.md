# run-quiet

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that wraps verbose commands (`pytest`, `npm run build`, `terraform plan`, etc.). The wrapper:

1. Runs the command, streaming the full stdout+stderr to a log file under `<root>/.claude/run-logs/`.
2. Returns to Claude only: exit code + matched error lines + last few lines + path to the log.
3. If the command exits 0 with no errors detected, the digest collapses to two lines.

Claude reads the log on demand only when the digest doesn't tell the full story.

> **Estimated savings:** a verbose 1000-line build / test output (~15K tokens) becomes a ~500-token digest. Multi-thousand-line logs become near-constant cost.

## How it works

This skill is **100% Markdown — no Python, no external scripts**. The [`SKILL.md`](SKILL.md) tells Claude how to run the command with stdout+stderr redirected to a log, then how to use `grep`, `head`, `tail`, and `wc` to extract the digest pieces in parallel.

## Requirements

- A POSIX shell or PowerShell (Claude Code's built-in Bash tool ships with both on Windows).
- That's it — no Python, no Node, no other runtimes.

## Installation

See the [top-level README](../README.md#installation).

```bash
./install/install.sh run-quiet         # macOS / Linux
```

```powershell
.\install\install.ps1 run-quiet        # Windows
```

## Usage

Inside any Claude Code session:

```
/run-quiet pytest -v
/run-quiet npm run build
/run-quiet timeout=120s -- terraform plan
```

These are free-form arguments — Claude reads them as natural language and maps them to the defaults documented in `SKILL.md`. You can also just say "run pytest quietly" or "build the project and don't dump all the output".

### Supported arguments (Claude maps these from natural language)

| Argument | Default | Purpose |
|----------|---------|---------|
| `root=<path>` | cwd / repo root | Working directory; logs go under `<root>/.claude/run-logs/`. |
| `max=N` | `30` | Cap on matched-error lines shown. |
| `tail=N` | `10` | Lines from the end always included. |
| `head=N` | `0` | Lines from the start always included. |
| `timeout=Ns` | none | Kill the command after N seconds. |
| `no_trim=true` | off | Skip the digest, print the full output. |

## Output examples

**Failing pytest:**

```
$ pytest -v
exit: 1 (in 4.21s)
log:  .claude/run-logs/20260514-185500-abc123.log (1842 lines)

errors (3):
  FAILED tests/test_users.py::test_create
  FAILED tests/test_users.py::test_update
  FAILED tests/test_admin.py::test_delete

tail (10):
  ============================== short test summary info ==============================
  FAILED tests/test_users.py::test_create
  FAILED tests/test_users.py::test_update
  FAILED tests/test_admin.py::test_delete
  ============================== 3 failed, 174 passed in 4.21s ==============================
```

**Clean build:**

```
$ npm run build
exit: 0 (in 12.30s)  •  log: .claude/run-logs/20260514-185530-def456.log (542 lines)
clean — last line: "✓ Compiled successfully"
```

## Notes

- Logs accumulate under `.claude/run-logs/`. The `.claude/` folder should be in your project's `.gitignore`.
- Pattern detection is heuristic — false negatives are possible. If the digest looks too clean for a non-zero exit code, fall back to `no_trim=true` or read the log directly.
- For commands that produce ANSI color codes, the digest strips the escape sequences before scanning. The raw log preserves them.

## License

MIT — inherited from the [parent repo](../LICENSE).

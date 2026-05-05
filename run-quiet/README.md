# run-quiet

Part of the [claude-skills](../README.md) collection.

> 🚧 **Planned, not yet implemented.**

A planned [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that wraps verbose commands (`pytest`, `npm run build`, `terraform plan`, etc.). The wrapper:

1. Runs the command, capturing full stdout/stderr.
2. Saves the full log to a temp file (e.g. `.claude/run-logs/<hash>.log`).
3. Returns to Claude only: exit code + the most relevant lines (errors, warnings, summary) + the log path.

If Claude needs the full output it reads the log file on demand instead of paying the token cost up front.

Tracking issue: TBD.

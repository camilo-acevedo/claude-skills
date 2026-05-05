# session-handoff

Part of the [claude-skills](../README.md) collection.

> 🚧 **Planned, not yet implemented.**

A planned [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that lets you save and restore task context between sessions, on your terms — instead of relying on `/compact` to pick what to keep.

Two commands:

- `/save-context` — writes a structured Markdown file (`.claude/handoff/<timestamp>.md`) capturing: current task, decisions made, open questions, files touched, next steps.
- `/resume-context` — reads the latest handoff at the start of the next session and seeds Claude with it.

> **Estimated savings:** avoids paying for a full conversation re-load and gives you control over what state survives session boundaries.

Design considerations (why this is harder than the others):

- What exactly should `/save-context` capture by default vs by prompt?
- How to invalidate stale handoffs (file changed since save)?
- How to merge multiple handoffs if you run several in parallel?

Tracking issue: TBD.

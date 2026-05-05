# diff-summary

Part of the [claude-skills](../README.md) collection.

> 🚧 **Planned, not yet implemented.**

A planned [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that produces a categorized summary of large diffs (typical use: PR review, big refactor). Instead of streaming a 5000-line `git diff`, the skill returns:

- Total files changed, insertions, deletions.
- Top 5 files by lines changed.
- Categories: tests / src / configs / docs / generated.
- A sample of 3 representative hunks.
- Path to the full diff so Claude can request specific sections on demand.

> **Estimated savings:** ~80% in code review of large changesets.

Tracking issue: TBD.

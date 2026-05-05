# log-extract

Part of the [claude-skills](../README.md) collection.

> 🚧 **Planned, not yet implemented.**

A planned [Claude Code](https://docs.claude.com/en/docs/claude-code) skill for working with large log files (production logs, Sentry exports, debug traces). Instead of having Claude read the full file, the skill extracts only:

- Lines matching error / warning / panic patterns (or a user-supplied pattern).
- N lines of surrounding context per hit.
- Deduplicated stack traces (collapse repeated frames into a single entry with a count).

Usage:

```
/log-extract <path> [pattern]
```

Implementation: ripgrep + a small Python deduplication layer.

> **Estimated savings:** a 50K-line log can collapse into a 100-line response.

Tracking issue: TBD.

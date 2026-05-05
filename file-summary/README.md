# file-summary

Part of the [claude-skills](../README.md) collection.

> 🚧 **Planned, not yet implemented.**

A planned [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that caches per-file summaries (purpose, exports, key line ranges) under `.claude/summaries/` so repeated reads of large files cost ~200 tokens instead of 2000+.

The first time Claude touches a file the skill generates a summary and stores it; subsequent reads pull the summary unless the file's hash or mtime changed.

Tracking issue: TBD.

# answer-cache

Part of the [claude-skills](../README.md) collection.

> 🚧 **Planned, not yet implemented.**

A planned [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that caches Q&A about a codebase. The first time someone asks "where is the auth middleware?", Claude searches and stores the answer; the next time the same question is asked, the skill returns the cached answer instead of re-exploring.

Storage: `.claude/answers/<question-hash>.md`.

Design considerations (why this is the hardest of the bunch):

- **Invalidation:** an answer becomes stale when the underlying code changes. Need a way to tie cache entries to source files (and bust them when those files change).
- **Question matching:** literal hashing is brittle ("auth middleware location" vs "where is auth middleware?"). May need lightweight semantic matching.
- **Trust boundary:** stale answers that look fresh are worse than no cache at all.

> **Estimated savings:** avoids repeated exploration of the same concept across sessions and across teammates.

Tracking issue: TBD.

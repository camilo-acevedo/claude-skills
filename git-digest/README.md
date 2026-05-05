# git-digest

Part of the [claude-skills](../README.md) collection.

> 🚧 **Planned, not yet implemented.**

A planned [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that bundles several `git` queries into a single digested report so Claude doesn't burn 4–5 separate tool calls (`git status`, `git log`, `git diff --stat`, `git branch -vv`, …) every time it needs context on the working tree.

A single `/git-digest` invocation returns:

- Current branch + ahead/behind tracking info.
- List of modified / staged / untracked files (compact format).
- Last 5 commits (one-line each).
- Diff stats (files changed, insertions/deletions).

> **Estimated savings:** ~60% of tokens normally spent on git state exploration; 4–5 tool calls collapse into 1.

Tracking issue: TBD.

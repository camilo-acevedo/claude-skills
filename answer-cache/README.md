# answer-cache

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that caches Q&A about a codebase keyed by a normalized question + linked source files. The first time a question is asked, Claude researches it; afterwards the cache returns the answer instantly — but if any of the linked files' SHA-256 has changed, the entry is reported as **stale** and Claude re-researches.

> **Estimated savings:** avoids repeated exploration of the same concept across sessions and across teammates.

> ⚠ **Wrong cached answers are worse than no cache.** When in doubt about a hit, re-verify against the actual files before responding.

## How it works

This skill is **100% Markdown — no Python, no external scripts**. The [`SKILL.md`](SKILL.md) tells Claude how to compute a question hash, hash linked files (`sha256sum` on Git Bash / Linux / macOS, `Get-FileHash` on PowerShell), and read/write a single Markdown file with YAML frontmatter per cache entry.

## Requirements

- A POSIX shell with `sha256sum`, or PowerShell with `Get-FileHash` (Claude Code's built-in Bash tool ships with both on Windows).
- That's it — no Python, no Node, no other runtimes.

## Installation

See the [top-level README](../README.md#installation).

```bash
./install/install.sh answer-cache       # macOS / Linux
```

```powershell
.\install\install.ps1 answer-cache      # Windows
```

## Usage

Inside any Claude Code session:

```
/answer-cache ask "where is the auth middleware?"
/answer-cache save "where is the auth middleware?" answer="src/api/middleware/auth.py" files="src/api/middleware/auth.py,src/api/__init__.py"
/answer-cache list
/answer-cache forget "where is the auth middleware?"
```

These are free-form arguments — Claude reads them as natural language.

## How `ask` reports

| Outcome | Meaning |
|---------|---------|
| hit (fresh) | All linked files unchanged. Use the printed answer. |
| stale | At least one linked file changed. Re-research. |
| miss | No entry for this question. Research from scratch. |

## Question matching (v1)

Exact match after normalization:
- lowercased
- punctuation stripped
- whitespace collapsed

`"Where is the auth middleware?"` and `"where is the auth middleware"` collide.
`"location of auth middleware"` does NOT — the underlying question hash is different.

## Storage

```
<repo>/.claude/answers/
└── <slug>-<qhash8>.md    # one file per cached answer (YAML frontmatter + Markdown body)
```

Frontmatter records the original question, normalized form, timestamp, and the linked files with their SHA-256 hashes at save time.

The `.claude/` folder should be in `.gitignore`.

## Suggested workflow for Claude

1. User asks "where is X?" or similar.
2. Claude calls `ask "X"`. If hit → answer immediately.
3. If miss/stale → Claude does the research, then calls `save "X" answer="..." files="<comma-list>"` with every file consulted during research.
4. Next time anyone asks "X", the cache hits.

## License

MIT — inherited from the [parent repo](../LICENSE).

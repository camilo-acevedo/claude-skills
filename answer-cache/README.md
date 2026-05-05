# answer-cache

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that caches Q&A about a codebase keyed by a normalized question + linked source files. The first time a question is asked, Claude researches it; afterwards the cache returns the answer instantly — but if any of the linked files' SHA-256 has changed, the entry is reported as **stale** and Claude re-researches.

> **Estimated savings:** avoids repeated exploration of the same concept across sessions and across teammates.

> ⚠ **Wrong cached answers are worse than no cache.** When in doubt about a hit, re-verify against the actual files before responding.

## Requirements

- Python 3.8+ (standard library only).

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
/answer-cache save "where is the auth middleware?" --answer "src/api/middleware/auth.py" --files src/api/middleware/auth.py,src/api/__init__.py
/answer-cache list
/answer-cache forget "where is the auth middleware?"
```

For long answer bodies, pipe via stdin:

```bash
python ~/.claude/skills/answer-cache/scripts/cache.py save "<question>" --from-stdin --files a.py,b.py < answer.md
```

## How `ask` reports

| Outcome | Exit code | Meaning |
|---------|-----------|---------|
| hit (fresh) | 0 | All linked files unchanged. Use the printed answer. |
| stale | 2 | At least one linked file changed. Re-research. |
| miss | 1 | No entry for this question. Research from scratch. |

Use the exit code to decide whether to skip exploration.

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
├── index.json                    # all entries metadata
└── <16-char-question-hash>.md    # one file per cached answer
```

The `.claude/` folder should be in `.gitignore`.

## Suggested workflow for Claude

1. User asks "where is X?" or similar.
2. Claude calls `ask "X"`. If hit → answer immediately.
3. If miss/stale → Claude does the research, then calls `save "X" --answer "..." --files <list>` with every file consulted during research.
4. Next time anyone asks "X", the cache hits.

## License

MIT — inherited from the [parent repo](../LICENSE).

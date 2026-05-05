---
name: answer-cache
description: |
  Cache Q&A about the codebase keyed by a normalized question + linked
  source files. The first time a question is asked, research it, then
  save the answer with the files it depends on. Future asks return the
  cached answer instantly — but if any linked file's sha256 has changed,
  the entry is reported as stale and you re-research. Use to avoid
  re-exploring the same concept across sessions.
---

# answer-cache

## When to invoke

Four operations:

### `ask`
Invoke at the start of any "where is …?" / "how does … work?" / "what calls …?"
question, **before** doing any Glob/Grep/Read of your own. If the cache has a
fresh answer, you save the entire research roundtrip.

### `save`
Invoke immediately after you've answered a question via research. Pass the
files you actually consulted — the cache uses them as the freshness key.

### `list`
Invoke when the user asks "what have we cached?" or to audit the cache.

### `forget`
Invoke when the user says a cached answer is wrong, or to manually invalidate.

## How to invoke

```bash
python <skill-dir>/scripts/cache.py ask    "<question>"                                                   [--root .]
python <skill-dir>/scripts/cache.py save   "<question>" --answer "<text>" --files a.py,b.py              [--root .]
python <skill-dir>/scripts/cache.py list                                                                  [--root .] [--limit N]
python <skill-dir>/scripts/cache.py forget "<question>"                                                  [--root .]
```

`<skill-dir>` is typically `~/.claude/skills/answer-cache/`.

For long answer bodies, pipe via stdin:

```bash
python <skill-dir>/scripts/cache.py save "<question>" --from-stdin --files a.py,b.py < answer.md
```

## Behavior of `ask`

| Outcome | Exit code | What you should do |
|---------|-----------|-------------------|
| **hit (fresh)** | 0 | Use the printed answer, no further research. |
| **stale** | 2 | Re-research; the printed answer is still shown for reference. After re-researching, call `save` with the same question to overwrite. |
| **miss** | 1 | Research from scratch, then call `save`. |

Staleness is detected by comparing each linked file's current sha256 against
the one recorded at save time. New files matching the question are NOT detected
automatically — that requires re-research.

## Question matching

v1 matches questions **exactly** after normalization:
- lowercased
- punctuation stripped
- whitespace collapsed

So `"Where is the auth middleware?"` and `"where is the auth middleware"`
collide; but `"location of auth middleware"` does not. Keep wording stable
for things you ask repeatedly.

## What you get back

`ask` (hit):

```markdown
# answer-cache: hit (saved 2026-05-04T18:00:00Z, 2 hours ago)

The auth middleware lives in `src/api/middleware/auth.py`, registered in
`src/api/__init__.py:42`. It validates JWTs via `verify_jwt` from
`src/auth/jwt.py:12`.
```

`ask` (stale):

```
answer-cache: STALE (1/3 linked files changed: src/api/middleware/auth.py)

(prior answer follows, treat as outdated:)
…
```

`ask` (miss):

```
answer-cache: miss for "where is auth middleware"
```

`save`:

```
answer-cache: saved (3 files linked: src/api/middleware/auth.py, src/auth/jwt.py, src/api/__init__.py)
```

`list`:

```
.claude/answers/  (4 entries)
- where is auth middleware                                  3 files (saved 2h ago)
- how does pagination work                                  2 files (saved 1d ago)
- where do we configure the database url                    1 file  (saved 3d ago)
- what jobs run on the worker container                     5 files (saved 1w ago)
```

## Notes

- Entries live under `<repo>/.claude/answers/`. The `.claude/` folder should
  be in `.gitignore`.
- Wrong cached answers are worse than no cache at all — when in doubt about
  a hit, re-verify against the actual files before responding to the user.
- This v1 has no semantic matching; if you need to vary phrasing, store the
  same answer under both questions (call `save` twice).

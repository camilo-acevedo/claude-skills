---
name: log-extract
description: |
  Extract relevant lines from a large log file: error / warning / panic /
  traceback patterns plus N lines of surrounding context, with deduplicated
  stack traces. Returns a compact summary instead of streaming the whole
  log into Claude's context. Use for production logs, Sentry exports,
  test output captured to disk, debug traces, etc.
---

# log-extract

A **Markdown-only** skill — no Python, no scripts. You (Claude) extract the
relevant lines from a log file using `grep -nC`, `head`, `tail`, and `wc`
via the Bash tool, then deduplicate and render.

## When to invoke

Invoke `log-extract` when ANY of these apply:

- The user points you at a log file and asks "what's wrong?" or "find the
  error".
- You're about to `cat` / `Read` a log file larger than ~500 lines.
- You need to find specific events in a log without paying for the whole
  file.

Do NOT invoke when:

- The log is small (<200 lines) — just read it.
- The user wants a specific exact section (use `Read` with line offsets).
- The file is structured data (JSON / CSV) — use the right parser instead.

## Defaults

| Setting | Default | Override with |
|---------|---------|---------------|
| Context lines around each match | 2 | `context=N` |
| Max hit groups shown | 30 | `max=N` |
| Head lines | 0 | `head=N` |
| Tail lines | 5 | `tail=N` |
| Deduplicate | on | `nodedup=true` |
| Pattern (extended regex, case-insensitive) | `(error\|errno\|exception\|traceback\|failed\|failure\|panic\|fatal\|warn(ing)?)` | `pattern="<regex>"` |

## How to run

Run these in a **single parallel Bash batch** against the log path `<LOG>`:

| Command | Yields |
|---------|--------|
| `wc -l "<LOG>"` | Total line count. |
| `head -n <head_n> "<LOG>"` | Head lines (skip if `head_n` is 0). |
| `tail -n <tail_n> "<LOG>"` | Tail lines. |
| `grep -niE -C <context> "<pattern>" "<LOG>" \| head -n <(max+10)*(2*context+1)>` | Candidate hits with context. |

The `grep -C` output uses `--` as a group separator and lines like
`123:<line text>` for matched lines, `124-<line text>` for context. Parse
the output into groups split on `--`.

### Deduplication

For each hit group, build a **normalized signature** by collapsing the
matched lines only (ignore context lines for the signature):

1. Strip leading timestamps. Common formats to drop:
   - `YYYY-MM-DD HH:MM:SS(.fff)?`
   - `[YYYY/MM/DD HH:MM:SS]`
   - ISO 8601 with timezone
   - Bare `HH:MM:SS`
2. Strip ANSI escapes: `s/\x1B\[[0-9;]*[a-zA-Z]//g`
3. Replace numbers with `N` (matches PIDs, ports, addresses, line numbers).
4. Lowercase.

Group hits whose normalized signature is identical. Record:
- `count` (number of occurrences),
- `first_time` and `last_time` (parsed timestamps if any),
- one representative hit group (the first occurrence, with its full context).

If `nodedup=true`, skip step 4-5 above and treat every hit as its own group.

Cap the visible groups at `max` (default 30). Sum the rest into a
`… (+N more hit groups)` line.

## Output format

```
log-extract: <path> (<total_lines> lines, <hits> hits → <unique_groups> unique)

head (<N>):
  <line>
  …

hits:

[×<count> — first at <first_time>, last at <last_time>]
  <context line>
  <matched line>
  <context line>

[×<count> at <single_time>]
  <context>
  <matched>
  <context>

… (+<extra> more hit groups)

tail (<N>):
  <line>
  …
```

- Omit `head` if `head_n=0` or no lines.
- Omit `hits:` body entirely if there are no matches; instead print a single
  line `no matches for pattern "<pattern>"`.
- If a group has only one occurrence, use `[×1 at <time>]` (or just `[×1]`
  if no timestamp could be parsed).

## Notes

- The default pattern is broad on purpose. Pass a tighter `pattern=` when
  the user knows what they're looking for (e.g. `pattern="TimeoutError"`).
- For very large logs (multi-GB), `grep` streams the file — no memory
  concerns. The Bash tool may truncate stdout, so use the
  `\| head -n <K>` cap shown above to keep output bounded.
- For non-UTF-8 logs, add `LC_ALL=C` before `grep` to avoid locale-related
  slowdowns and decoding errors.
- This skill never modifies the log file.

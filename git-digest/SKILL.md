---
name: git-digest
description: |
  Bundle several git commands (status, log, diff --stat, branch -vv, stash list)
  into a single Markdown digest. Invoke instead of running 4–5 separate git
  commands when you need to understand the working-tree state, recent commits,
  and how the branch relates to its upstream.
---

# git-digest

A **Markdown-only** skill — no Python, no external scripts. You (Claude) run the
git commands listed below in parallel via the Bash tool, then format the results
into the digest layout at the bottom of this file.

## When to invoke

Invoke `git-digest` when ANY of these apply:

- You're starting work on an unfamiliar branch and need a quick orientation.
- The user asks "what's going on in this repo?" / "what's left on this branch?" / "what changed lately?".
- You're about to run more than two of: `git status`, `git log`, `git diff --stat`, `git branch -vv`, `git stash list`.

Do NOT invoke when:

- You only need ONE specific piece of git state (just run that one command).
- You're inside a non-git directory.
- The user is asking about a specific commit or file history (use `git log <path>` directly).

## How to run it

Run the commands below from the repo root. They are all read-only and independent,
so issue them as **parallel Bash tool calls in a single message**.

### Required commands

Run all of these in parallel (one Bash call per command):

| # | Command | Purpose |
|---|---------|---------|
| 1 | `git rev-parse --show-toplevel` | Confirm we are inside a git repo + get the repo name (last path segment). |
| 2 | `git symbolic-ref --quiet --short HEAD` | Current branch name. Empty + non-zero exit ⇒ detached HEAD. |
| 3 | `git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}'` | Tracked upstream (empty / error if none). |
| 4 | `git rev-list --left-right --count '@{upstream}'...HEAD` | Two numbers: `<behind> <ahead>` vs upstream. Skip if step 3 was empty. |
| 5 | `git symbolic-ref --quiet --short refs/remotes/origin/HEAD` | Default branch (e.g. `origin/main`). Strip the `origin/` prefix. |
| 6 | `git status --porcelain=v1 --untracked-files=normal` | Working-tree state. |
| 7 | `git log -5 --pretty=format:'- %h (%ar) %s — %an'` | Last 5 commits (adjust `-5` if user asks for more). |
| 8 | `git diff --shortstat <ref>...HEAD` | Diff stats vs `<ref>` (see "Choosing the diff ref" below). |
| 9 | `git diff --numstat <ref>...HEAD` | Per-file insertions/deletions vs the same ref. Sort by `(insertions + deletions)` desc, take top 10. |
| 10 | `git stash list` | Stash entries (empty output ⇒ no stashes). |

Steps 8 and 9 depend on knowing `<ref>` (which comes from step 3 or step 5), so
run them in a **second batch** after the first parallel batch returns.

### Choosing the diff ref

Pick the first that resolves:

1. The user's explicit `--against <ref>` argument, if any.
2. The upstream from step 3 (e.g. `origin/feature/foo`).
3. `origin/<default-branch>` from step 5 (e.g. `origin/main`).
4. `HEAD~10` as last resort.

Verify the chosen ref exists before diffing: `git rev-parse --verify --quiet <ref>`.
If it fails, fall back to the next option.

### Short-circuit: pristine repo

If the working tree is clean **AND** the branch has an upstream **AND** ahead = behind = 0,
emit only this one-liner and stop:

```markdown
# git-digest — <repo-name>

clean working tree on `<branch>`, up to date with `<upstream>`.
```

## Output format

Print exactly one Markdown document to the user (do not include the commands you
ran). Use the following sections, in this order, and omit sections whose data
collection failed.

```markdown
# git-digest — <repo-name>

## Branch
- Current: <branch>            # or "(detached <short-sha>)" if detached
- Tracking: <upstream> (<rel>) # rel = "ahead N", "behind N", "ahead N, behind N", or "in sync"
                               # if no upstream: "- Tracking: (no upstream)"
- Default: <default-branch>    # omit if same as current, or unknown

## Working tree (<S> staged, <M> modified, <U> untracked[, <C> conflicted])
```
<porcelain output, one line per entry>
```

## Recent commits (last N)
<lines from `git log` step 7, already formatted as "- <sha> (<ago>) <subject> — <author>">

## Diff vs <ref>
- <shortstat output, e.g. "4 files changed, 87 insertions(+), 12 deletions(-)">
- Top files:
  - <path>  +<ins> / -<del>
  - …
  - … (<extra> more)   # only if more than 10 files

## Stash
<one line "(empty)" OR "- " + each stash entry>
```

### Counting staged / modified / untracked / conflicted from porcelain

For each line of `git status --porcelain=v1`:

- `??` ⇒ untracked.
- Two non-space chars from `{A, D, U}` (e.g. `AA`, `DU`, `UU`) ⇒ conflicted.
- Otherwise: first char non-space ⇒ staged; second char non-space ⇒ modified.

A single file can count as both staged AND modified (e.g. `MM`). Show the
porcelain lines verbatim inside a fenced block.

## Notes

- If `git` is not on `PATH` or the cwd is not inside a git repo, report that
  in one line and stop.
- Detached HEAD: skip the upstream / ahead-behind line.
- Submodules and other worktrees are not inspected.
- Output is always plain Markdown — safe to keep in context as-is.

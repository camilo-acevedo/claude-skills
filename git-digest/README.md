# git-digest

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that bundles several `git` queries into a single Markdown report so Claude doesn't burn 4–5 separate tool calls (`git status`, `git log`, `git diff --stat`, `git branch -vv`, `git stash list`) every time it needs context on the working tree.

A single invocation returns:

- Current branch + ahead/behind tracking info + default branch.
- Working-tree state (modified / staged / untracked / conflicted) with the porcelain listing.
- Last N commits (one line each).
- Diff stats vs the upstream (or vs a custom ref).
- Stash list.

If the working tree is clean and the branch is in sync with its upstream, the digest collapses to a single line.

> **Estimated savings:** 4–5 git tool calls collapse into 1. Typical session saves ~60% of the tokens spent on git state exploration.

## Requirements

- Python 3.8+ (standard library only — no third-party packages).
- `git` available on `PATH`.

## Installation

See the [top-level README](../README.md#installation) for install options.

```bash
./install/install.sh git-digest         # macOS / Linux
```

```powershell
.\install\install.ps1 git-digest        # Windows
```

## Usage

Inside any Claude Code session:

```
/git-digest
```

You can also run the script directly:

```bash
python ~/.claude/skills/git-digest/scripts/digest.py
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--root <path>` | `.` | Repo to inspect (walks up to find `.git`). |
| `--commits N` | `5` | Number of recent commits to list. |
| `--against <ref>` | upstream (or `HEAD~10`) | Ref to diff against in the diffstat section. |
| `--no-diff` | off | Skip the diffstat section entirely (faster on huge ranges). |
| `--quiet` | off | Suppress trailing performance hints. |

## Output example

```markdown
# git-digest — myproject

## Branch
- Current: feature/auth-rewrite
- Tracking: origin/feature/auth-rewrite (ahead 2, in sync)
- Default: main

## Working tree (1 staged, 3 modified, 1 untracked)
```
M  src/api/auth.py
M  src/api/users.py
A  tests/test_users.py
?? notes.md
```

## Recent commits (last 5)
- abc1234 (2 hours ago) feat: add user create endpoint — Camilo
- def5678 (1 day ago) refactor: extract validation       — Camilo
…

## Diff vs origin/main
- 4 files changed, 87 insertions(+), 12 deletions(-)
- Top files:
  - src/api/users.py        +45 / -3
  - tests/test_users.py     +30 / -0
  - src/api/auth.py         +10 / -8
  - src/__init__.py         +2 / -1

## Stash
(empty)
```

When everything is clean and up to date:

```markdown
# git-digest — myproject

clean working tree on `main`, up to date with `origin/main`.
```

## Limitations

- Detached HEAD: reported but no upstream comparison.
- Submodules: not inspected (a future flag could add `--recurse-submodules`).
- Worktrees: only the active worktree is inspected.

## License

MIT — inherited from the [parent repo](../LICENSE).

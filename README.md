# claude-skills

A collection of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills focused on **saving tokens** during real engineering work — by preventing Claude from re-exploring the same codebase, re-reading the same files, and re-running the same verbose commands every conversation.

**All skills are now 100% Markdown — no Python, no Node, no extra runtimes.** Each `SKILL.md` is a recipe Claude follows using its built-in Bash / Read / Write / Grep / Glob tools.

## Skills in this repo

| Skill | What it does |
|-------|--------------|
| [codemap](codemap/) | One `CODEMAP.md` (tree + per-file purpose + exported symbols) so Claude reads one map instead of doing 20+ Glob/Grep/Read calls. |
| [run-quiet](run-quiet/) | Wraps verbose commands (`pytest`, `npm run build`, `terraform plan`); returns exit code + relevant lines, full output saved to a log. |
| [git-digest](git-digest/) | Bundles `git status` + `log` + `diff --stat` + `branch -vv` + `stash list` into a single digested report. 4–5 calls collapse into 1. |
| [test-failures-only](test-failures-only/) | Runs the test suite and returns only failures with condensed tracebacks; if all green, returns one line. |
| [file-summary](file-summary/) | Per-file summary cache under `.claude/summaries/`. Repeated reads of large files cost ~200 tokens instead of 2000+. |
| [diff-summary](diff-summary/) | Categorized summary of large diffs for PR review (top files, categories, sample hunks + path to full diff). |
| [log-extract](log-extract/) | Extracts errors + N lines of context from large log files; deduplicates repeated stack traces. |
| [api-contract](api-contract/) | Distills OpenAPI 3.x specs into a compact `CONTRACT.md` (endpoints, methods, key types, auth). |
| [session-handoff](session-handoff/) | `save` / `list` / `resume` to persist task state across sessions in `.claude/handoff/`. |
| [answer-cache](answer-cache/) | Caches Q&A about the codebase under `.claude/answers/` with file-based invalidation. |

Each skill is self-contained inside its own folder (`SKILL.md` + a folder-level `README.md`).

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed.
- `git` available on `PATH` (used by `git-digest`, `diff-summary`, `codemap`, `session-handoff`).
- A POSIX shell with `grep`, `sed`, `head`, `tail`, `wc`, `sha256sum` — OR PowerShell with `Get-FileHash`. Claude Code's built-in Bash tool ships with both on Windows.

No Python, Node, or other language runtimes are required.

## Installation

Clone the repo anywhere, then install one or more skills into your Claude Code skills directory (`~/.claude/skills/`).

### 1. Clone the repo

```bash
git clone https://github.com/camilo-acevedo/claude-skills.git
cd claude-skills
```

```powershell
git clone https://github.com/camilo-acevedo/claude-skills.git
cd claude-skills
```

### 2. Run the install script

Install **every** available skill:

```bash
./install/install.sh                 # macOS / Linux
```

```powershell
.\install\install.ps1                # Windows
```

Or install a **single** skill (e.g. `codemap`):

```bash
./install/install.sh codemap
```

```powershell
.\install\install.ps1 codemap
```

The script copies the skill folder into `~/.claude/skills/<skill-name>/`. Re-running it updates an existing installation in place.

### 3. Verify

Open a **new** Claude Code session (skills are discovered at session start, so any session that was already open won't see the skill yet) and type:

```
/codemap
```

Claude should enumerate the repo and write `CODEMAP.md` to your repo root.

### Updating after a `git pull`

```bash
cd path/to/claude-skills
git pull
./install/install.sh codemap         # macOS / Linux
```

```powershell
cd path\to\claude-skills
git pull
.\install\install.ps1 codemap        # Windows
```

### Optional: install via symlink (auto-updates on `git pull`)

Pass `--symlink` (Unix) or `-Symlink` (Windows) so the installed skill points back to the cloned repo and changes propagate without re-running the install script.

```bash
./install/install.sh codemap --symlink
```

```powershell
.\install\install.ps1 codemap -Symlink
```

> **Windows note:** creating symlinks requires either an Administrator shell or **Developer Mode** enabled (`Settings → System → For developers → Developer Mode = On`). If you don't enable it, the script will fail — fall back to the regular copy install.

### Manual install (no scripts)

Just copy any skill folder into `~/.claude/skills/`:

```bash
cp -r codemap ~/.claude/skills/codemap
```

```powershell
Copy-Item -Recurse codemap $env:USERPROFILE\.claude\skills\codemap
```

## Uninstall

```bash
rm -rf ~/.claude/skills/codemap ~/.claude/skills/file-summary ~/.claude/skills/run-quiet
```

```powershell
Remove-Item -Recurse -Force `
  $env:USERPROFILE\.claude\skills\codemap, `
  $env:USERPROFILE\.claude\skills\file-summary, `
  $env:USERPROFILE\.claude\skills\run-quiet
```

## Contributing

Each skill lives in its own folder and ships with a `SKILL.md` (Claude-facing recipe) and a `README.md` (human-facing docs). Open a PR or an issue.

## License

MIT — see [LICENSE](LICENSE).

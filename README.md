# claude-skills

A collection of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills focused on **saving tokens** during real engineering work — by preventing Claude from re-exploring the same codebase, re-reading the same files, and re-running the same verbose commands every conversation.

## Skills in this repo

| Skill | Status | What it does |
|-------|--------|--------------|
| [codemap](codemap/) | ✅ available | Generates a single `CODEMAP.md` (file tree + per-file purpose + exported symbols) so Claude reads one map instead of doing 20+ Glob/Grep/Read calls. |
| [file-summary](file-summary/) | 🚧 planned | Caches per-file summaries (purpose, exports, key line ranges) under `.claude/summaries/` so repeated reads of large files cost ~200 tokens instead of 2000+. |
| [run-quiet](run-quiet/) | 🚧 planned | Wraps verbose commands (`pytest`, `npm run build`, `terraform plan`) — runs them, saves the full output to a log, returns only exit code + relevant lines. |

Each skill is self-contained inside its own folder (`SKILL.md` + `scripts/` + a folder-level `README.md`).

## Requirements

- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed.
- Python 3.8 or later for skills that use Python scripts (`codemap`, `file-summary`). No third-party packages required.

## Installation

Clone the repo anywhere, then install one or more skills into your Claude Code skills directory (`~/.claude/skills/`).

### Install everything

```bash
git clone https://github.com/<your-user>/claude-skills.git
cd claude-skills
./install/install.sh                 # macOS / Linux
```

```powershell
git clone https://github.com/<your-user>/claude-skills.git
cd claude-skills
.\install\install.ps1                # Windows
```

### Install a specific skill

```bash
./install/install.sh codemap
```

```powershell
.\install\install.ps1 codemap
```

Re-running the script updates an existing installation in place. Pass `--symlink` (Unix) or `-Symlink` (Windows) to symlink instead of copying so future `git pull` updates propagate automatically.

### Manual install (no scripts)

Copy or symlink any skill folder into `~/.claude/skills/`:

```bash
cp -r codemap ~/.claude/skills/codemap
```

```powershell
Copy-Item -Recurse codemap $env:USERPROFILE\.claude\skills\codemap
```

## Verifying the install

Open a Claude Code session and ask:

```
/codemap
```

Claude should pick up the skill and run the generator.

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

Each skill lives in its own folder and ships with a `SKILL.md` (Claude-facing instructions) and a `README.md` (human-facing docs). Open a PR or an issue.

## License

MIT — see [LICENSE](LICENSE).

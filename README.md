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

Claude should run the generator and write `CODEMAP.md` to your repo root.

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

Each skill lives in its own folder and ships with a `SKILL.md` (Claude-facing instructions) and a `README.md` (human-facing docs). Open a PR or an issue.

## License

MIT — see [LICENSE](LICENSE).

# codemap

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that generates a single `CODEMAP.md` snapshot of your repository so Claude can read it once instead of running dozens of `Glob` / `Grep` / `Read` calls every conversation.

The map contains:

- A filtered file tree (respects `.gitignore`, skips `node_modules`, `.venv`, build artifacts, etc.).
- A one-line purpose for each source file (from docstrings or leading comments).
- Top-level exported symbols (functions, classes, public constants) with their signatures.

Supports symbol extraction for **Python**, **TypeScript / JavaScript** (incl. `.tsx` / `.jsx`), and **Go**. Other source files appear in the tree only.

> Token savings: in repos with 100+ files, replaces ~10–30 exploration tool calls per session with a single `Read CODEMAP.md`.

## Requirements

- Python 3.8 or later. No third-party packages required (uses only the standard library).
- [Claude Code](https://docs.claude.com/en/docs/claude-code) installed.

## Installation

See the [top-level README](../README.md#installation) for install options.

The shortest path:

```bash
# from the repo root
./install/install.sh codemap
```

```powershell
.\install\install.ps1 codemap
```

Or copy the folder manually into `~/.claude/skills/codemap/`.

## Usage

Inside any Claude Code session:

```
/codemap
```

Claude will run the generator, write `CODEMAP.md` to the repo root, and read it.

You can also run the generator manually:

```bash
python ~/.claude/skills/codemap/scripts/generate.py
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--root <path>` | `.` | Index only a subtree (useful in monorepos). |
| `--refresh` | off | Ignore cache, re-parse every file. |
| `--max-symbols N` | `30` | Truncate per-file symbol lists. |
| `--include-tests` | off | Put test files in the main tree instead of a separate section. |
| `--output <path>` | `CODEMAP.md` | Write the map somewhere else. |
| `--quiet` | off | Suppress stdout summary. |

## Output format

```markdown
# Codemap — myproject

Generated: 2026-05-04T15:23:01Z
Files indexed: 142  •  Languages: Python (89), TS (41), Go (12)

## Tree

src/
├── api/
│   ├── auth.py            — JWT validation + middleware
│   ├── users.py           — CRUD endpoints for /users
│   └── __init__.py        — router aggregation
└── domain/
    └── user.py            — User entity + value objects

## Symbols

### src/api/auth.py
- `def verify_jwt(token: str) -> Claims`
- `class AuthMiddleware`
- `JWT_ALGO: str`
```

## Cache

The first run parses every source file. Subsequent runs reuse cached entries for files whose `mtime` and `sha256` have not changed — typical re-generations on a 1000-file repo finish in well under a second.

The cache lives at `<repo>/.claude/codemap-cache.json`. Delete it to force a full rebuild, or pass `--refresh`.

Both `CODEMAP.md` and `.claude/codemap-cache.json` are derived artifacts — add them to your project's `.gitignore`.

## Limitations

- TypeScript / JavaScript parsing uses regex (no full AST). Re-exports through barrel files and dynamic exports may be missed. A future version may switch to tree-sitter.
- Go parsing uses regex over `func` / `type` declarations; build tags are ignored.
- Repos larger than 5000 files abort with a suggestion to use `--root <subdir>`.

## License

MIT — inherited from the [parent repo](../LICENSE).

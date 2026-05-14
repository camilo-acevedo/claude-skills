# codemap

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that generates a single `CODEMAP.md` snapshot of your repository so Claude can read it once instead of running dozens of `Glob` / `Grep` / `Read` calls every conversation.

The map contains:

- A filtered file tree (uses `git ls-files`, so it respects `.gitignore` and skips `node_modules`, `.venv`, build artifacts, etc. automatically).
- A one-line purpose for each source file (from docstrings or leading comments).
- Top-level exported symbols (functions, classes, public constants) with their line numbers.

Supports symbol extraction for **Python**, **TypeScript / JavaScript** (incl. `.tsx` / `.jsx`), and **Go**. Other source files appear in the tree only.

> Token savings: in repos with 100+ files, replaces ~10–30 exploration tool calls per session with a single `Read CODEMAP.md`.

## How it works

This skill is **100% Markdown — no Python, no external scripts**. The [`SKILL.md`](SKILL.md) tells Claude how to enumerate files with `git ls-files` and extract per-language top-level symbols with parallel `grep` calls.

### Trade-off vs the old Python parser

The grep-based recipe is faster to install and works anywhere, but is **slightly less precise** than the old AST-based extractor:

- Multi-line declarations may produce false positives/negatives.
- Decorators changing visibility (`@private`) are not understood.
- Re-exports through barrel files / dynamic exports may be missed.

For navigation purposes this is fine — the map is a hint, not gospel. Fall back to `Grep` for the exact location of a symbol.

## Requirements

- `git` available on `PATH` (used for `git ls-files`).
- A POSIX shell with `grep` (Claude Code's built-in Bash tool on all platforms).
- That's it — no Python, no Node, no other runtimes.

## Installation

See the [top-level README](../README.md#installation) for install options.

```bash
./install/install.sh codemap            # macOS / Linux
```

```powershell
.\install\install.ps1 codemap           # Windows
```

## Usage

Inside any Claude Code session:

```
/codemap
/codemap root=services/api
/codemap includetests=true max=50
```

Claude will enumerate files, extract symbols, write `CODEMAP.md` to the repo root, and read it.

### Supported arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `root=<path>` | repo root | Index only a subtree (useful in monorepos). |
| `max=N` | `30` | Cap per-file symbol lists. |
| `includetests=true` | off | Put test files in the main `## Files` section instead of a separate group. |

## Output format

```markdown
# CODEMAP

_Generated: 2026-05-14T15:23:01Z_

## Tree

repo-name/
├── src/
│   ├── api/
│   │   ├── auth.py
│   │   ├── users.py
│   │   └── __init__.py
│   └── domain/
│       └── user.py
└── tests/
    └── test_users.py

## Files

### src/api/auth.py
_JWT validation + middleware_
- L12 `class AuthMiddleware:`
- L34 `def verify_jwt(token):`
- L60 `JWT_ALGORITHM = "HS256"`

### src/api/users.py
_CRUD endpoints for /users_
- L8  `class UserCreate(BaseModel):`
- L20 `def create_user(payload):`
```

## Limitations

- TypeScript / JavaScript parsing uses regex — re-exports through barrel files and dynamic exports may be missed.
- Go parsing uses regex over `func` / `type` declarations; build tags are ignored.
- Repos larger than 5000 files abort with a suggestion to use `root=<subdir>`.
- No cache layer in the Markdown version — regen is a full rebuild every time. Parallel `grep` makes it fast.

## License

MIT — inherited from the [parent repo](../LICENSE).

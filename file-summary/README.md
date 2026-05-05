# file-summary

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that produces or recalls a per-file summary (purpose, exported symbols with line ranges, notable sections). The summary is cached under `<repo>/.claude/summaries/` keyed by file hash, so repeated reads of the same file cost ~200 tokens instead of the full contents.

Sister skill of [`codemap`](../codemap/) — codemap is the bird's-eye view of the whole repo; file-summary is the per-file deep dive.

> **Estimated savings:** 70-90% on large files consulted repeatedly across sessions.

## Requirements

- Python 3.8+ (standard library only).

## Installation

See the [top-level README](../README.md#installation).

```bash
./install/install.sh file-summary       # macOS / Linux
```

```powershell
.\install\install.ps1 file-summary      # Windows
```

## Usage

Inside any Claude Code session:

```
/file-summary src/api/users.py
```

Or run the script directly:

```bash
python ~/.claude/skills/file-summary/scripts/summarize.py src/api/users.py
python ~/.claude/skills/file-summary/scripts/summarize.py src/api/users.py --refresh
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `path` (positional) | required | File to summarize. |
| `--root <path>` | nearest `.git` ancestor or file's dir | Where to put `.claude/summaries/`. |
| `--refresh` | off | Ignore cache, regenerate. |
| `--max-symbols N` | `40` | Cap on listed symbols per file. |
| `--no-cache` | off | Compute and print without writing the cache. |

## Languages with structured parsing

| Language | Parser |
|----------|--------|
| Python (`.py`) | `ast` (functions, classes, methods, annotated public constants, imports). |
| TypeScript / JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`) | regex over `export …` and `import … from …`. |
| Go (`.go`) | regex over `func` / `type` / `var` / `const` (exported only). |
| Other | generic line filter (`def`, `class`, `function`, `interface`, `fn`, `public`, `export`, `module`, `impl`). |

## Output example

```markdown
# src/api/users.py — CRUD endpoints for /users

312 lines • python • cached: hit (sha 7f3a8b1d)

## Imports
- fastapi (APIRouter, Depends)
- sqlalchemy.orm (Session)
- ..domain.user (User)

## Exports
- `def list_users(session: Session) -> list[User]`  L24-32
- `def create_user(payload: CreateUserDTO) -> User`  L35-58
- `class UserRouter`  L60-145
  - `.add_user`  L70-90
  - `.delete_user`  L92-110
- `USER_SCHEMA: dict`  L18

## Notable sections
- L1-22: imports / module setup
- L24-58: list_users / create_user
- L60-145: class UserRouter
- L147-312: trailing helpers / private code
```

## Cache

`<root>/.claude/summaries/<sha8>-<filename>.md`

The cache key is the full SHA-256 (the 8-char prefix is just for readable filenames). Stale entries are not deleted; pass `--refresh` to overwrite, or wipe the directory.

## License

MIT — inherited from the [parent repo](../LICENSE).

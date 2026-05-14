# file-summary

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that produces or recalls a per-file summary (purpose, exported symbols with line numbers, head/tail). The summary is cached under `<repo>/.claude/summaries/` keyed by file SHA-256, so repeated reads of the same file cost ~200 tokens instead of the full contents.

Sister skill of [`codemap`](../codemap/) — codemap is the bird's-eye view of the whole repo; file-summary is the per-file deep dive.

> **Estimated savings:** 70-90% on large files consulted repeatedly across sessions.

## How it works

This skill is **100% Markdown — no Python, no external scripts**. The [`SKILL.md`](SKILL.md) tells Claude how to compute the file's SHA-256 (`sha256sum` on Bash, `Get-FileHash` on PowerShell), check the cache, and if it's a miss, gather per-language symbols with parallel `grep` calls.

### Trade-off vs the old Python parser

The grep-based recipe is faster to install and works anywhere, but is **slightly less precise** than the old `ast`-based extractor for Python:

- Multi-line declarations, decorators, and dynamic exports may be missed.
- Symbol entries record only the start line — no end-line ranges.

For navigation purposes this is fine. Fall back to a direct `Read` when you need exact bodies.

## Requirements

- A POSIX shell with `grep`, `sha256sum`, `head`, `tail`, `wc`, OR PowerShell with `Get-FileHash` (Claude Code's built-in Bash tool ships with both on Windows).
- That's it — no Python, no Node, no other runtimes.

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
/file-summary src/api/users.py refresh=true
/file-summary big_module.py max=60
```

These are free-form arguments — Claude reads them as natural language.

### Supported arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `path` (first positional) | required | File to summarize. |
| `root=<path>` | nearest `.git` ancestor or file's dir | Where to put `.claude/summaries/`. |
| `refresh=true` | off | Ignore cache, regenerate. |
| `max=N` | `40` | Cap on listed symbols. |
| `nocache=true` | off | Compute and print without writing the cache. |

## Languages with symbol extraction

| Language | Patterns |
|----------|---------|
| Python (`.py`) | `^(class\|def\|async def) <Name>`, top-level `^[A-Z_]+\s*=`, imports. |
| TypeScript / JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`) | `^export …`, `import …`. |
| Go (`.go`) | exported `func` / `type` / `var` / `const` + `import` block. |
| Other | generic line filter on `def`, `class`, `function`, `interface`, `fn`, `public`, `export`. |

## Output example

```markdown
# src/api/users.py — CRUD endpoints for /users

312 lines • Python

## Imports
- fastapi (APIRouter, Depends)
- sqlalchemy.orm (Session)
- ..domain.user (User)

## Exports
- L24  def list_users(session: Session) -> list[User]
- L35  def create_user(payload: CreateUserDTO) -> User
- L60  class UserRouter:
- L18  USER_SCHEMA = {

## Head (first 10 lines)
…

## Tail (last 5 lines)
…
```

## Cache

`<root>/.claude/summaries/<sha8>-<filename>.md`

The cache key is the full SHA-256 (the 8-char prefix is just for readable filenames; the frontmatter stores the full digest). Stale entries are not deleted; pass `refresh=true` to overwrite, or wipe the directory.

## License

MIT — inherited from the [parent repo](../LICENSE).

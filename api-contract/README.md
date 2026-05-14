# api-contract

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that distills an OpenAPI 3.x spec (JSON or YAML) into a compact `CONTRACT.md`:

- Endpoints grouped by tag, with HTTP method + path + brief description.
- Request body / success response schema names.
- Auth scheme summary.
- Schemas summarized to one line each (top-level shape).

Claude reads the contract once instead of paging through a multi-MB spec file.

> **Estimated savings:** 95%+ in projects with large specs (where the raw schema is several MB).

## How it works

This skill is **100% Markdown — no Python, no external scripts**. The [`SKILL.md`](SKILL.md) tells Claude how to read the spec (directly for small files, section-by-section with `grep` + `Read` offsets for large ones), parse it in-context, and render `CONTRACT.md`.

## Requirements

- A POSIX shell with `grep` and `wc` (Claude Code's built-in Bash tool on all platforms).
- That's it — no Python, no YAML library, no JSON parser, no other runtimes.

## Installation

See the [top-level README](../README.md#installation).

```bash
./install/install.sh api-contract       # macOS / Linux
```

```powershell
.\install\install.ps1 api-contract      # Windows
```

## Usage

Inside any Claude Code session:

```
/api-contract docs/openapi.json
/api-contract api/swagger.yaml output=CONTRACT.md
/api-contract spec.json tag=users
```

These are free-form arguments — Claude reads them as natural language.

### Supported arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `path` (first positional) | required | Path to OpenAPI 3.x spec (`.json`, `.yaml`, `.yml`). |
| `output=<path>` | `CONTRACT.md` at repo root | Where to write the distilled contract. |
| `tag=<name>` | none | Filter endpoints whose tag contains this (case-insensitive). |
| `maxschemas=N` | `40` | Cap on schemas in the Schemas section. |
| `noschemas=true` | off | Skip the Schemas section. |

## Output example

```markdown
# API contract — petstore (v1.0.0)

Servers: https://api.petstore.example
Base URL: /v1

## Auth
- bearerJwt (http, bearer, JWT)
- apiKey (apiKey, header: X-API-Key)

## Endpoints (12)

### users
- GET    /users               — List users
- POST   /users               — Create user            (body: CreateUserDTO → 201 User)
- GET    /users/{id}          — Get user               (→ 200 User)

### pets
- GET    /pets                — List pets              (query: limit, offset)
- POST   /pets                — Create pet             (body: CreatePet → 201 Pet)

## Schemas (24)
- User              { id: int, email: string, role: enum(admin, user) }
- Pet               { id: int, name: string (required), owner_id: int }
- CreatePet         { name: string (required), owner_id: int }
```

## Limitations

- v1 supports OpenAPI 3.x. Swagger 2.0 specs partially work (the recipe falls back to `definitions` if `components.schemas` is missing).
- GraphQL SDL is not supported.
- Deeply nested schemas show only their top-level shape; schema names are preserved so you can drill down by reading the spec section directly.

## License

MIT — inherited from the [parent repo](../LICENSE).

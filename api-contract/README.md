# api-contract

Part of the [claude-skills](../README.md) collection.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that distills an OpenAPI 3.x spec (JSON or YAML) into a compact `CONTRACT.md`:

- Endpoints grouped by tag, with HTTP method + path + brief description.
- Request body / success response schema names.
- Auth scheme summary.
- Schemas summarized to one line each (top-level shape).

Claude reads the contract once instead of paging through a multi-MB spec file.

> **Estimated savings:** 95%+ in projects with large specs (where the raw schema is several MB).

## Requirements

- Python 3.8+ (standard library only for JSON specs).
- `pyyaml` if you want to feed YAML specs (`pip install pyyaml`). JSON-only otherwise.

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
```

Or run the script directly:

```bash
python ~/.claude/skills/api-contract/scripts/distill.py docs/openapi.json
python ~/.claude/skills/api-contract/scripts/distill.py spec.yaml --output CONTRACT.md
python ~/.claude/skills/api-contract/scripts/distill.py spec.json --tag users
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `path` (positional) | required | Path to OpenAPI 3.x spec (`.json`, `.yaml`, `.yml`). |
| `--output <path>` | stdout | Write the contract to a file. |
| `--tag <name>` | none | Filter endpoints whose tag contains this (case-insensitive). |
| `--max-schemas N` | `40` | Cap on schemas in the Schemas section. |
| `--no-schemas` | off | Skip the Schemas section. |

## Output example

```markdown
# API contract — petstore (1.0.0)

## Servers
- https://api.petstore.example  — Production

## Auth
- bearerJwt: http  (bearer, format=JWT)
- apiKey: apiKey  (in=header, name=X-API-Key)

## Endpoints (12)

### users
- `GET    /users`  — List users
- `POST   /users`  — Create user  _(body: CreateUserDTO; → 201 User)_
- `GET    /users/{id}`  — Get user  _(→ 200 User)_

### pets
- `GET    /pets`  — List pets  _(query: limit, offset)_
- `POST   /pets`  — Create pet  _(body: CreatePet; → 201 Pet)_

## Schemas (24)
- `User`  { id: integer, email: string, role: enum(admin, user) }
- `Pet`  { id: integer, name: string (required), owner_id: integer }
- `CreatePet`  { name: string (required), owner_id: integer }
```

## Limitations

- v1 supports OpenAPI 3.x. Swagger 2.0 specs partially work (the script falls back to `definitions` if `components.schemas` is missing).
- GraphQL SDL is not supported (planned for a future version).
- Deeply nested schemas show only their top-level shape; `$ref` names are preserved so you can drill down by reading the spec section.

## License

MIT — inherited from the [parent repo](../LICENSE).

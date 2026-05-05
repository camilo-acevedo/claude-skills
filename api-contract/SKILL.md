---
name: api-contract
description: |
  Distill an OpenAPI 3.x spec (JSON or YAML) into a compact CONTRACT.md
  with endpoints, methods, brief descriptions, schema references, and
  auth scheme summary. Read once instead of paging through a multi-MB
  spec file. Use when you need to understand or work against an API
  whose spec is too large for direct reading.
---

# api-contract

## When to invoke

Invoke `api-contract` when ANY of these apply:

- The user points you at an OpenAPI / Swagger spec file (`openapi.json`,
  `swagger.yaml`, …) and asks about endpoints / shapes / auth.
- You're about to read a spec file > 1000 lines.
- You need to call an API documented by a spec and want to know which
  endpoints exist before drilling into one.

Do NOT invoke when:

- The spec is small (< 200 lines) — just read it.
- The user wants details of a specific endpoint already in context.
- The input is GraphQL SDL — only OpenAPI is supported in v1.

## How to invoke

```bash
python <skill-dir>/scripts/distill.py <path/to/openapi.json|.yaml> [flags]
```

`<skill-dir>` is typically `~/.claude/skills/api-contract/`.

Examples:

```bash
python <skill-dir>/scripts/distill.py docs/openapi.json
python <skill-dir>/scripts/distill.py api/swagger.yaml --output CONTRACT.md
python <skill-dir>/scripts/distill.py spec.json --tag users
```

## Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `path` (positional) | required | Path to an OpenAPI 3.x JSON or YAML spec. |
| `--output <path>` | stdout | Write the contract to a file instead of stdout. |
| `--tag <name>` | none | Filter endpoints whose tag matches (substring, case-insensitive). |
| `--max-schemas N` | `40` | Cap on schemas shown in the Schemas section. |
| `--no-schemas` | off | Skip the Schemas section entirely. |
| `--quiet` | off | Suppress trailing performance hints. |

YAML support requires the `pyyaml` package. JSON specs need no extra deps.

## What you get back

```markdown
# API contract — petstore (v1.0.0)

Servers: https://api.petstore.example
Base URL: /v1

## Auth
- bearer (JWT, header: Authorization)
- apiKey (header: X-API-Key)

## Endpoints (12)

### users
- GET    /users                 — List users
- POST   /users                 — Create user            (body: CreateUserDTO)
- GET    /users/{id}            — Get user
- PATCH  /users/{id}            — Update user            (body: UpdatePartial)
- DELETE /users/{id}            — Delete user

### pets
- GET    /pets                  — List pets              (query: limit, offset)
- POST   /pets                  — Create pet             (body: CreatePet → 201 Pet)
…

## Schemas (24)
- User              { id: int, email: str, role: enum }
- Pet               { id: int, name: str, owner_id: int }
- CreatePet         { name: str (required), owner_id: int }
…
```

## Notes

- v1 is OpenAPI 3.x only. Swagger 2.0 specs may load but field paths differ
  (the script tries both `paths`+`components` and `paths`+`definitions`).
- Schemas are summarized to one line each: object key types are inlined,
  required fields are marked `(required)`. For deeply nested schemas only
  the top-level shape is shown.
- For specs > 5 MB the script may take a few seconds; the result is small
  and cacheable in your project (write to `CONTRACT.md` and commit it).

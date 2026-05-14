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

A **Markdown-only** skill — no Python, no scripts. You (Claude) read the
OpenAPI spec with the Read tool (or extract sections via `grep` when the
spec is too large), parse it in-context, and write `CONTRACT.md`.

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

## How to run

### Step 1 — measure the spec

```bash
wc -l "<path>"
```

- If under ~1500 lines: use the Read tool to read the whole file.
- Otherwise: use `grep` + Read with offsets to extract only the sections
  you need (see Step 2 below).

### Step 2 — extract the sections you need

For both JSON and YAML specs, you only need four top-level sections:

| Section | YAML key | JSON key |
|---------|----------|----------|
| Metadata | `info:` | `"info":` |
| Servers | `servers:` | `"servers":` |
| Endpoints | `paths:` | `"paths":` |
| Schemas | `components.schemas:` or `definitions:` (Swagger 2) | `"components"."schemas"` or `"definitions"` |
| Auth | `components.securitySchemes:` or `securityDefinitions:` (Swagger 2) | same |

For huge specs, locate the line ranges of these sections with:

```bash
grep -nE '^(info|servers|paths|components|definitions|securityDefinitions):' "<path>"
```

(JSON: look for top-level keys at indent 2 — `grep -nE '^\s{2}"(info|servers|paths|components|definitions)"\s*:' "<path>"`.)

Then use the Read tool with `offset` and `limit` to read each section
individually.

### Step 3 — parse and summarize

#### Endpoints

For each path in `paths`:
- For each HTTP method (`get`, `post`, `put`, `patch`, `delete`, `head`, `options`):
  - Extract `summary` (first line) or `description` (first sentence) as the
    one-line description.
  - Extract `tags` (first tag is used for grouping).
  - Extract request body schema name if present (`requestBody.content.*.schema.$ref` →
    last segment after `/`).
  - Extract `parameters` of type `query` (list the names, comma-separated).
  - Extract success response status + schema name if present
    (`responses.2xx.content.*.schema.$ref` → last segment).

Group endpoints by tag (or `(untagged)`).

#### Schemas

For each entry in `components.schemas` (or `definitions`):
- If `type: object` with `properties`, summarize as
  `{ key1: <type>, key2: <type>, … }`. Mark required keys with `(required)`.
- If `type: array`, summarize as `<item-type>[]`.
- If `enum`, summarize as `enum (<comma-list>)`.
- If `$ref` only, summarize as `→ <target>`.
- Cap at the first ~5 keys; append `…` if more.

#### Auth

For each entry in `securitySchemes`:
- Print `<name>` + `<type>` + key transport (header / query / cookie) +
  scheme/format if relevant.

### Step 4 — render `CONTRACT.md`

```markdown
# API contract — <title> (v<version>)

Servers: <comma-list of server URLs>
Base URL: <basePath if Swagger 2, else first server.url path>

## Auth
- <name> (<type>, header: <Authorization|X-API-Key|…>)
- …

## Endpoints (<total>)

### <tag>
- <METHOD> <path>            — <one-line summary>             (<body: SchemaName, query: a, b, → 200 ResponseSchema>)
- …

(Repeat per tag, alphabetized.)

## Schemas (<total>)
- <Name>            <inlined shape>
- …
```

By default, write to `<repo-root>/CONTRACT.md` (use `output=<path>` to
override). If the file already exists, overwrite it.

## Supported arguments

| Argument | Default | Purpose |
|----------|---------|---------|
| `path` (first positional) | required | Path to an OpenAPI 3.x JSON or YAML spec. |
| `output=<path>` | `CONTRACT.md` at repo root | Where to write the distilled contract. |
| `tag=<name>` | none | Filter endpoints whose tag contains `<name>` (case-insensitive). |
| `maxschemas=N` | `40` | Cap on schemas in the Schemas section. |
| `noschemas=true` | off | Skip the Schemas section entirely. |

## Notes

- v1 supports OpenAPI 3.x and Swagger 2.0 (the section keys differ, but the
  shapes are similar enough). GraphQL SDL is out of scope.
- For YAML specs, you read them with the Read tool the same as JSON — no
  parser library is needed because YAML keys are line-oriented and shallow
  enough for visual parsing.
- Schemas with deep nesting are summarized to top-level shape only. Drill
  into the spec directly when you need full detail on one.
- The result is small and stable — commit `CONTRACT.md` to the repo so
  future sessions skip the distill step.

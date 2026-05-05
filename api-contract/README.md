# api-contract

Part of the [claude-skills](../README.md) collection.

> 🚧 **Planned, not yet implemented.**

A planned [Claude Code](https://docs.claude.com/en/docs/claude-code) skill that distills large API specs (OpenAPI / Swagger / GraphQL) into a compact `CONTRACT.md`:

- Endpoint list with HTTP method + path + brief description.
- Top-level types referenced (request/response shapes).
- Auth scheme summary.

Claude reads the contract once instead of paging through a multi-MB spec file.

Usage:

```
/api-contract path/to/openapi.json
```

Supported inputs (planned): OpenAPI 3.x JSON/YAML, GraphQL SDL.

> **Estimated savings:** 95%+ in projects with large specs (anything where the raw schema is several MB).

Tracking issue: TBD.

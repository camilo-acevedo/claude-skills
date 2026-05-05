"""api-contract entrypoint.

Read an OpenAPI 3.x spec (JSON, or YAML if pyyaml is installed) and emit a
compact CONTRACT.md: endpoints grouped by tag, schema summaries, auth list.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_MAX_SCHEMAS = 40
SUPPORTED_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    args = _parse_args(argv)
    spec_path = Path(args.path).expanduser()
    if not spec_path.exists():
        print(f"api-contract: error: file not found: {spec_path}", file=sys.stderr)
        return 2

    spec = _load_spec(spec_path)
    if spec is None:
        return 3

    contract = _render(spec, tag_filter=args.tag, max_schemas=args.max_schemas, include_schemas=not args.no_schemas)

    if args.output:
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(contract, encoding="utf-8")
        if not args.quiet:
            try:
                rel = out_path.relative_to(Path.cwd())
            except ValueError:
                rel = out_path
            print(f"api-contract: wrote {rel}")
    else:
        sys.stdout.write(contract)
    return 0


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="api-contract")
    parser.add_argument("path")
    parser.add_argument("--output", default=None)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--max-schemas", type=int, default=DEFAULT_MAX_SCHEMAS)
    parser.add_argument("--no-schemas", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def _load_spec(path: Path) -> Optional[Dict[str, Any]]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore[import-not-found,import-untyped]
        except ImportError:
            print(
                "api-contract: error: YAML spec requires `pyyaml` (`pip install pyyaml`).",
                file=sys.stderr,
            )
            return None
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:  # type: ignore[attr-defined]
            print(f"api-contract: error: YAML parse failed: {exc}", file=sys.stderr)
            return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"api-contract: error: JSON parse failed: {exc}", file=sys.stderr)
        return None


# ---------- rendering ----------


def _render(
    spec: Dict[str, Any],
    tag_filter: Optional[str],
    max_schemas: int,
    include_schemas: bool,
) -> str:
    info = spec.get("info") or {}
    title = info.get("title") or "API"
    version = info.get("version") or ""
    servers = spec.get("servers") or []
    paths = spec.get("paths") or {}

    parts: List[str] = []
    header = f"# API contract — {title}"
    if version:
        header += f" ({version})"
    parts.append(header)
    parts.append("")

    if servers:
        parts.append("## Servers")
        for srv in servers:
            url = srv.get("url", "")
            description = srv.get("description")
            line = f"- {url}"
            if description:
                line += f"  — {description}"
            parts.append(line)
        parts.append("")

    auth_lines = _render_auth(spec)
    if auth_lines:
        parts.append("## Auth")
        parts.extend(auth_lines)
        parts.append("")

    endpoints, total = _collect_endpoints(paths, tag_filter)
    parts.append(f"## Endpoints ({total}{f', filtered by tag={tag_filter!r}' if tag_filter else ''})")
    if not endpoints:
        parts.append("(no endpoints)")
    else:
        for tag, methods in sorted(endpoints.items()):
            parts.append("")
            parts.append(f"### {tag}")
            for line in methods:
                parts.append(line)
    parts.append("")

    if include_schemas:
        schemas_section = _render_schemas(spec, max_schemas)
        if schemas_section:
            parts.extend(schemas_section)

    return "\n".join(parts).rstrip() + "\n"


def _render_auth(spec: Dict[str, Any]) -> List[str]:
    components = spec.get("components") or {}
    schemes = components.get("securitySchemes") or {}
    if not schemes:
        # Swagger 2.0
        schemes = spec.get("securityDefinitions") or {}
    out: List[str] = []
    for name, scheme in schemes.items():
        kind = scheme.get("type", "?")
        description = scheme.get("description") or ""
        bits: List[str] = []
        if kind == "http":
            bits.append(scheme.get("scheme", "http"))
            if scheme.get("bearerFormat"):
                bits.append(f"format={scheme['bearerFormat']}")
        elif kind == "apiKey":
            bits.append(f"in={scheme.get('in', '?')}")
            bits.append(f"name={scheme.get('name', '?')}")
        elif kind == "oauth2":
            flows = scheme.get("flows") or {}
            bits.append("flows=" + ",".join(flows.keys()))
        line = f"- {name}: {kind}"
        if bits:
            line += f"  ({', '.join(bits)})"
        if description:
            line += f"  — {description}"
        out.append(line)
    return out


def _collect_endpoints(
    paths: Dict[str, Any],
    tag_filter: Optional[str],
) -> Tuple[Dict[str, List[str]], int]:
    grouped: Dict[str, List[str]] = defaultdict(list)
    total = 0
    needle = tag_filter.lower() if tag_filter else None
    for url, methods_obj in paths.items():
        if not isinstance(methods_obj, dict):
            continue
        common_params = methods_obj.get("parameters") or []
        for method in SUPPORTED_METHODS:
            op = methods_obj.get(method)
            if not isinstance(op, dict):
                continue
            tags = op.get("tags") or ["(untagged)"]
            if needle and not any(needle in t.lower() for t in tags):
                continue
            summary = (op.get("summary") or "").strip()
            if not summary:
                desc = (op.get("description") or "").strip()
                summary = desc.splitlines()[0] if desc else ""
            params = (op.get("parameters") or []) + common_params
            query = [p["name"] for p in params if p.get("in") == "query"]
            body_ref = _request_body_ref(op)
            response_ref = _success_response_ref(op)
            line = f"- `{method.upper():6s} {url}`"
            if summary:
                line += f"  — {summary}"
            extras: List[str] = []
            if query:
                extras.append("query: " + ", ".join(query[:6]) + (", …" if len(query) > 6 else ""))
            if body_ref:
                extras.append(f"body: {body_ref}")
            if response_ref:
                extras.append(f"→ {response_ref}")
            if extras:
                line += f"  _({'; '.join(extras)})_"
            primary_tag = tags[0]
            grouped[primary_tag].append(line)
            total += 1
    return grouped, total


def _request_body_ref(op: Dict[str, Any]) -> Optional[str]:
    body = op.get("requestBody") or {}
    content = body.get("content") or {}
    for media in ("application/json", *content.keys()):
        if media not in content:
            continue
        schema = content[media].get("schema") or {}
        return _schema_ref(schema) or "object"
    return None


def _success_response_ref(op: Dict[str, Any]) -> Optional[str]:
    responses = op.get("responses") or {}
    for code in ("200", "201", "204", "default"):
        resp = responses.get(code)
        if not isinstance(resp, dict):
            continue
        content = resp.get("content") or {}
        for media in ("application/json", *content.keys()):
            if media not in content:
                continue
            schema = content[media].get("schema") or {}
            ref = _schema_ref(schema)
            if ref:
                return f"{code} {ref}"
    return None


def _schema_ref(schema: Dict[str, Any]) -> Optional[str]:
    if not isinstance(schema, dict):
        return None
    ref = schema.get("$ref")
    if ref:
        return ref.rsplit("/", 1)[-1]
    if schema.get("type") == "array":
        items = schema.get("items") or {}
        item_ref = _schema_ref(items)
        return f"{item_ref}[]" if item_ref else "array"
    return None


def _render_schemas(spec: Dict[str, Any], max_schemas: int) -> List[str]:
    components = spec.get("components") or {}
    schemas = components.get("schemas") or spec.get("definitions") or {}
    if not schemas:
        return []
    parts: List[str] = []
    parts.append(f"## Schemas ({len(schemas)})")
    listed = list(schemas.items())[:max_schemas]
    for name, schema in listed:
        parts.append(f"- `{name}`  {_summarize_schema(schema)}")
    if len(schemas) > max_schemas:
        parts.append(f"- _… ({len(schemas) - max_schemas} more — see spec)_")
    return parts


def _summarize_schema(schema: Any, depth: int = 0) -> str:
    if not isinstance(schema, dict):
        return ""
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if schema.get("type") == "array":
        return _summarize_schema(schema.get("items") or {}, depth + 1) + "[]"
    if schema.get("enum"):
        values = schema["enum"][:5]
        suffix = "" if len(schema["enum"]) <= 5 else ", …"
        return f"enum({', '.join(map(str, values))}{suffix})"
    if schema.get("type") and schema["type"] != "object":
        return schema["type"]
    properties = schema.get("properties") or {}
    if not properties:
        return "object"
    required = set(schema.get("required") or [])
    if depth > 0:
        return f"object ({len(properties)} fields)"
    bits: List[str] = []
    for prop, sub in list(properties.items())[:6]:
        marker = " (required)" if prop in required else ""
        bits.append(f"{prop}: {_summarize_schema(sub, depth + 1)}{marker}")
    suffix = ""
    if len(properties) > 6:
        suffix = f", +{len(properties) - 6} more"
    return "{ " + ", ".join(bits) + suffix + " }"


if __name__ == "__main__":
    raise SystemExit(main())

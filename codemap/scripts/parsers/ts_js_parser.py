"""Extract module purpose and exported top-level symbols from TS / JS via regex.

This is intentionally regex-based to avoid a tree-sitter dependency. It catches
the common cases (named exports, default export, re-exports) but will miss
exotic patterns like dynamic exports or unusual barrel files.
"""

import re
from typing import List, Optional

from .base import FileSummary, Symbol


_LEADING_BLOCK_COMMENT = re.compile(r"\A\s*/\*\*?(?P<body>.*?)\*/", re.DOTALL)
_LEADING_LINE_COMMENT = re.compile(r"\A(?:\s*//[^\n]*\n)+")

_EXPORT_PATTERNS = [
    # export function foo(args) [: ReturnType]
    (
        re.compile(
            r"^export\s+(?:async\s+)?function\*?\s+(?P<name>[A-Za-z_$][\w$]*)\s*"
            r"(?P<args>\([^)]*\))(?P<ret>\s*:\s*[^\n{]+)?",
            re.MULTILINE,
        ),
        "function",
    ),
    # export class Foo [extends Bar]
    (
        re.compile(
            r"^export\s+(?:abstract\s+)?class\s+(?P<name>[A-Za-z_$][\w$]*)"
            r"(?P<rest>(?:\s+extends\s+[^\s{<]+)?(?:\s+implements\s+[^\n{]+)?)",
            re.MULTILINE,
        ),
        "class",
    ),
    # export interface Foo
    (
        re.compile(
            r"^export\s+interface\s+(?P<name>[A-Za-z_$][\w$]*)",
            re.MULTILINE,
        ),
        "type",
    ),
    # export type Foo = ...
    (
        re.compile(
            r"^export\s+type\s+(?P<name>[A-Za-z_$][\w$]*)",
            re.MULTILINE,
        ),
        "type",
    ),
    # export enum Foo
    (
        re.compile(
            r"^export\s+(?:const\s+)?enum\s+(?P<name>[A-Za-z_$][\w$]*)",
            re.MULTILINE,
        ),
        "type",
    ),
    # export const foo = ... or export const foo: Type = ...
    (
        re.compile(
            r"^export\s+(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)"
            r"(?P<type>\s*:\s*[^=;\n]+)?",
            re.MULTILINE,
        ),
        "constant",
    ),
]

_DEFAULT_FUNCTION = re.compile(
    r"^export\s+default\s+(?:async\s+)?function\*?\s*(?P<name>[A-Za-z_$][\w$]*)?"
    r"\s*(?P<args>\([^)]*\))",
    re.MULTILINE,
)
_DEFAULT_CLASS = re.compile(
    r"^export\s+default\s+(?:abstract\s+)?class\s*(?P<name>[A-Za-z_$][\w$]*)?",
    re.MULTILINE,
)


def parse_ts_js(source: str) -> FileSummary:
    purpose = _extract_leading_comment(source)
    seen = set()
    symbols: List[Symbol] = []

    for pattern, kind in _EXPORT_PATTERNS:
        for match in pattern.finditer(source):
            name = match.group("name")
            if name in seen:
                continue
            seen.add(name)
            symbols.append(Symbol(_format_match(match, kind), kind))

    for match in _DEFAULT_FUNCTION.finditer(source):
        name = match.group("name") or "default"
        key = f"default::{name}"
        if key in seen:
            continue
        seen.add(key)
        args = match.group("args") or "()"
        symbols.append(Symbol(f"export default function {name}{args}", "function"))

    for match in _DEFAULT_CLASS.finditer(source):
        name = match.group("name") or "default"
        key = f"default-class::{name}"
        if key in seen:
            continue
        seen.add(key)
        symbols.append(Symbol(f"export default class {name}", "class"))

    return FileSummary(purpose=purpose, symbols=symbols)


def _format_match(match: re.Match, kind: str) -> str:
    name = match.group("name")
    if kind == "function":
        args = match.group("args") or "()"
        ret = (match.group("ret") or "").rstrip()
        return f"function {name}{args}{ret}".strip()
    if kind == "class":
        rest = (match.group("rest") or "").strip()
        return f"class {name} {rest}".strip()
    if kind == "type":
        return f"{_type_keyword(match)} {name}"
    if kind == "constant":
        type_ann = (match.group("type") or "").strip()
        return f"const {name}{type_ann}" if type_ann else f"const {name}"
    return name


def _type_keyword(match: re.Match) -> str:
    raw = match.group(0)
    for kw in ("interface", "type", "enum"):
        if re.search(rf"\b{kw}\b", raw):
            return kw
    return "type"


def _extract_leading_comment(source: str) -> Optional[str]:
    block = _LEADING_BLOCK_COMMENT.match(source)
    if block:
        body = block.group("body")
        for raw in body.splitlines():
            cleaned = raw.strip().lstrip("*").strip()
            if cleaned and not cleaned.startswith("@"):
                return cleaned
    line = _LEADING_LINE_COMMENT.match(source)
    if line:
        for raw in line.group(0).splitlines():
            cleaned = raw.strip().lstrip("/").strip()
            if cleaned:
                return cleaned
    return None

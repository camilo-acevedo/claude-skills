"""Extract package purpose and exported top-level symbols from Go via regex.

Avoids depending on the `go` toolchain so the skill works in repos where Go is
not installed. Exported identifiers in Go start with an uppercase letter.
"""

import re
from typing import List, Optional

from .base import FileSummary, Symbol


_PACKAGE_DOC = re.compile(
    r"(?P<doc>(?:^//[^\n]*\n)+)\s*package\s+\w+",
    re.MULTILINE,
)
_PACKAGE_LINE = re.compile(r"^package\s+\w+", re.MULTILINE)

_FUNC = re.compile(
    r"^func\s+(?:\((?P<receiver>[^)]+)\)\s+)?(?P<name>[A-Z]\w*)\s*"
    r"(?P<args>\([^)]*\))(?P<ret>(?:\s*\([^)]*\)|\s+[^\s{]+)?)",
    re.MULTILINE,
)
_TYPE = re.compile(
    r"^type\s+(?P<name>[A-Z]\w*)\s+(?P<kind>struct|interface|[^\s{]+)",
    re.MULTILINE,
)
_VAR_OR_CONST = re.compile(
    r"^(?P<keyword>var|const)\s+(?P<name>[A-Z]\w*)(?P<rest>\s+[^\n=]+)?(?:\s*=\s*(?P<val>[^\n]+))?",
    re.MULTILINE,
)


def parse_go(source: str) -> FileSummary:
    if not _PACKAGE_LINE.search(source):
        return FileSummary(parse_error="missing package declaration")

    purpose = _extract_package_doc(source)
    seen = set()
    symbols: List[Symbol] = []

    for match in _FUNC.finditer(source):
        name = match.group("name")
        receiver = match.group("receiver")
        # Methods (with receiver) are listed too — they belong to the type.
        key = f"func::{receiver or ''}::{name}"
        if key in seen:
            continue
        seen.add(key)
        args = match.group("args") or "()"
        ret = (match.group("ret") or "").strip()
        prefix = f"func ({receiver}) " if receiver else "func "
        sig = f"{prefix}{name}{args}"
        if ret:
            sig += f" {ret}"
        symbols.append(Symbol(sig.strip(), "function"))

    for match in _TYPE.finditer(source):
        name = match.group("name")
        if name in seen:
            continue
        seen.add(name)
        kind_word = match.group("kind").strip()
        symbols.append(Symbol(f"type {name} {kind_word}", "type"))

    for match in _VAR_OR_CONST.finditer(source):
        name = match.group("name")
        key = f"vc::{name}"
        if key in seen:
            continue
        seen.add(key)
        keyword = match.group("keyword")
        symbols.append(Symbol(f"{keyword} {name}", "constant"))

    return FileSummary(purpose=purpose, symbols=symbols)


def _extract_package_doc(source: str) -> Optional[str]:
    match = _PACKAGE_DOC.search(source)
    if not match:
        return None
    for raw in match.group("doc").splitlines():
        cleaned = raw.strip().lstrip("/").strip()
        if cleaned:
            return cleaned
    return None

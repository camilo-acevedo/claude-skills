"""file-summary entrypoint.

Produce or recall a per-file summary (purpose, exports with line ranges,
notable sections). Cached under <root>/.claude/summaries/ keyed by file
hash — repeat reads are O(read summary) instead of O(read file).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

CACHE_DIR_REL = ".claude/summaries"
DEFAULT_MAX_SYMBOLS = 40

LANG_BY_EXT = {
    ".py": "python",
    ".ts": "ts",
    ".tsx": "ts",
    ".js": "js",
    ".jsx": "js",
    ".mjs": "js",
    ".cjs": "js",
    ".go": "go",
}


@dataclass
class Symbol:
    signature: str
    line_start: int
    line_end: int
    children: List["Symbol"] = field(default_factory=list)


@dataclass
class FileBreakdown:
    purpose: Optional[str]
    language: str
    line_count: int
    imports: List[str] = field(default_factory=list)
    symbols: List[Symbol] = field(default_factory=list)
    sections: List[Tuple[int, int, str]] = field(default_factory=list)
    parse_error: Optional[str] = None


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    args = _parse_args(argv)
    file_path = Path(args.path).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        print(f"file-summary: error: file not found: {file_path}", file=sys.stderr)
        return 2

    project_root = _project_root(args.root, file_path)
    file_hash = _hash_file(file_path)
    cache_path = _cache_path(project_root, file_path, file_hash)

    if not args.refresh and cache_path.exists():
        cached = cache_path.read_text(encoding="utf-8", errors="replace")
        if file_hash[:8] in cached:
            sys.stdout.write(cached.replace("cached: miss", "cached: hit", 1))
            return 0

    text = file_path.read_text(encoding="utf-8", errors="replace")
    breakdown = _analyze(text, file_path)
    rendered = _render(file_path, project_root, breakdown, file_hash, args.max_symbols, cached_hit=False)

    if not args.no_cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(rendered, encoding="utf-8")

    sys.stdout.write(rendered)
    return 0


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="file-summary")
    parser.add_argument("path")
    parser.add_argument("--root", default=None)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--max-symbols", type=int, default=DEFAULT_MAX_SYMBOLS)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def _project_root(arg: Optional[str], file_path: Path) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    for candidate in [file_path.parent, *file_path.parent.parents]:
        if (candidate / ".git").exists():
            return candidate
    return file_path.parent


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _cache_path(root: Path, file_path: Path, file_hash: str) -> Path:
    short = file_hash[:8]
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", file_path.name)
    return root / CACHE_DIR_REL / f"{short}-{safe_name}.md"


# ---------- analyzers ----------


def _analyze(text: str, file_path: Path) -> FileBreakdown:
    lang = LANG_BY_EXT.get(file_path.suffix.lower(), "generic")
    line_count = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
    if lang == "python":
        return _analyze_python(text, line_count)
    if lang in ("ts", "js"):
        return _analyze_ts_js(text, line_count, lang)
    if lang == "go":
        return _analyze_go(text, line_count)
    return _analyze_generic(text, line_count)


def _analyze_python(text: str, line_count: int) -> FileBreakdown:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return FileBreakdown(
            purpose=None,
            language="python",
            line_count=line_count,
            parse_error=f"SyntaxError: {exc.msg} (line {exc.lineno})",
        )

    purpose = _first_line(ast.get_docstring(tree))
    imports: List[str] = []
    symbols: List[Symbol] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = ("." * (node.level or 0)) + (node.module or "")
            names = ", ".join((a.asname or a.name) for a in node.names)
            imports.append(f"{mod} ({names})" if names else mod)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                symbols.append(Symbol(
                    signature=_format_python_function(node),
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno) or node.lineno,
                ))
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                children: List[Symbol] = []
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and not sub.name.startswith("_"):
                        children.append(Symbol(
                            signature=f".{sub.name}",
                            line_start=sub.lineno,
                            line_end=getattr(sub, "end_lineno", sub.lineno) or sub.lineno,
                        ))
                symbols.append(Symbol(
                    signature=f"class {node.name}",
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno) or node.lineno,
                    children=children,
                ))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if not name.startswith("_") and (name.isupper() or any(c.isupper() for c in name)):
                annotation = _safe_unparse(node.annotation) or "Any"
                symbols.append(Symbol(
                    signature=f"{name}: {annotation}",
                    line_start=node.lineno,
                    line_end=getattr(node, "end_lineno", node.lineno) or node.lineno,
                ))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    symbols.append(Symbol(
                        signature=target.id,
                        line_start=node.lineno,
                        line_end=getattr(node, "end_lineno", node.lineno) or node.lineno,
                    ))

    sections = _detect_sections(symbols, line_count)
    return FileBreakdown(
        purpose=purpose,
        language="python",
        line_count=line_count,
        imports=imports[:20],
        symbols=symbols,
        sections=sections,
    )


def _format_python_function(node) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    args = _safe_unparse(node.args) or ""
    returns = _safe_unparse(node.returns) if node.returns else None
    sig = f"{prefix} {node.name}({args})"
    if returns:
        sig += f" -> {returns}"
    return sig


def _safe_unparse(node) -> Optional[str]:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _first_line(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s
    return None


_TS_EXPORT = re.compile(
    r"^export\s+(?:default\s+)?(?:async\s+)?"
    r"(?P<kind>function\*?|class|interface|type|enum|const|let|var)"
    r"\s+(?P<name>[A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
_TS_IMPORT = re.compile(r"^import\s+(?:.+?\s+from\s+)?['\"](?P<src>[^'\"]+)['\"]", re.MULTILINE)


def _analyze_ts_js(text: str, line_count: int, lang: str) -> FileBreakdown:
    purpose = _leading_block_comment(text)
    imports: List[str] = []
    seen_imports = set()
    for m in _TS_IMPORT.finditer(text):
        src = m.group("src")
        if src not in seen_imports:
            seen_imports.add(src)
            imports.append(src)
    symbols: List[Symbol] = []
    seen_names = set()
    for m in _TS_EXPORT.finditer(text):
        name = m.group("name")
        if name in seen_names:
            continue
        seen_names.add(name)
        kind = m.group("kind")
        line = text.count("\n", 0, m.start()) + 1
        symbols.append(Symbol(signature=f"{kind} {name}", line_start=line, line_end=line))
    sections = _detect_sections(symbols, line_count)
    return FileBreakdown(
        purpose=purpose,
        language=lang,
        line_count=line_count,
        imports=imports[:20],
        symbols=symbols,
        sections=sections,
    )


_GO_FUNC = re.compile(r"^func\s+(?:\([^)]+\)\s+)?(?P<name>[A-Z]\w*)", re.MULTILINE)
_GO_TYPE = re.compile(r"^type\s+(?P<name>[A-Z]\w*)\s+(?P<kind>[^\s{]+)", re.MULTILINE)
_GO_VAR = re.compile(r"^(?P<keyword>var|const)\s+(?P<name>[A-Z]\w*)", re.MULTILINE)
_GO_PACKAGE_DOC = re.compile(r"((?:^//[^\n]*\n)+)\s*package\s+\w+", re.MULTILINE)


def _analyze_go(text: str, line_count: int) -> FileBreakdown:
    purpose = None
    pkg = _GO_PACKAGE_DOC.search(text)
    if pkg:
        for line in pkg.group(1).splitlines():
            cleaned = line.strip().lstrip("/").strip()
            if cleaned:
                purpose = cleaned
                break
    symbols: List[Symbol] = []
    for m in _GO_FUNC.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        symbols.append(Symbol(f"func {m.group('name')}", line, line))
    for m in _GO_TYPE.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        symbols.append(Symbol(f"type {m.group('name')} {m.group('kind').strip()}", line, line))
    for m in _GO_VAR.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        symbols.append(Symbol(f"{m.group('keyword')} {m.group('name')}", line, line))
    return FileBreakdown(
        purpose=purpose,
        language="go",
        line_count=line_count,
        symbols=symbols,
        sections=_detect_sections(symbols, line_count),
    )


_GENERIC_DECL = re.compile(
    r"^\s*(?:def|class|function|interface|fn|public|export|module|impl)\b.*",
    re.MULTILINE,
)


def _analyze_generic(text: str, line_count: int) -> FileBreakdown:
    symbols: List[Symbol] = []
    for m in _GENERIC_DECL.finditer(text):
        snippet = m.group(0).strip()[:120]
        line = text.count("\n", 0, m.start()) + 1
        symbols.append(Symbol(snippet, line, line))
    return FileBreakdown(
        purpose=None,
        language="generic",
        line_count=line_count,
        symbols=symbols[:80],
    )


def _detect_sections(symbols: List[Symbol], line_count: int) -> List[Tuple[int, int, str]]:
    if not symbols:
        return []
    sections: List[Tuple[int, int, str]] = []
    first_symbol_line = symbols[0].line_start
    if first_symbol_line > 1:
        sections.append((1, first_symbol_line - 1, "imports / module setup"))
    for i, sym in enumerate(symbols):
        end = symbols[i + 1].line_start - 1 if i + 1 < len(symbols) else min(line_count, sym.line_end)
        sections.append((sym.line_start, end, sym.signature))
    last_sym_end = symbols[-1].line_end
    if last_sym_end < line_count:
        sections.append((last_sym_end + 1, line_count, "trailing helpers / private code"))
    # Collapse to at most 5 representative sections.
    if len(sections) > 5:
        head, tail = sections[0], sections[-1]
        middle = sections[1:-1]
        if len(middle) > 3:
            step = len(middle) // 3
            picked = [middle[0], middle[len(middle) // 2], middle[-1]]
            sections = [head, *picked, tail]
        else:
            sections = [head, *middle, tail]
    return sections


def _leading_block_comment(text: str) -> Optional[str]:
    m = re.match(r"\A\s*/\*\*?(?P<body>.*?)\*/", text, re.DOTALL)
    if m:
        for line in m.group("body").splitlines():
            cleaned = line.strip().lstrip("*").strip()
            if cleaned and not cleaned.startswith("@"):
                return cleaned
    m = re.match(r"\A(?:\s*//[^\n]*\n)+", text)
    if m:
        for line in m.group(0).splitlines():
            cleaned = line.strip().lstrip("/").strip()
            if cleaned:
                return cleaned
    return None


# ---------- renderer ----------


def _render(
    file_path: Path,
    root: Path,
    b: FileBreakdown,
    file_hash: str,
    max_symbols: int,
    cached_hit: bool,
) -> str:
    try:
        rel = file_path.relative_to(root).as_posix()
    except ValueError:
        rel = str(file_path)

    purpose_suffix = f" — {b.purpose}" if b.purpose else ""
    parts: List[str] = []
    parts.append(f"# {rel}{purpose_suffix}\n")
    parts.append(f"{b.line_count} lines • {b.language} • cached: {'hit' if cached_hit else 'miss'} (sha {file_hash[:8]})")
    if b.parse_error:
        parts.append("")
        parts.append(f"⚠ parse error: {b.parse_error}")

    if b.imports:
        parts.append("")
        parts.append("## Imports")
        for imp in b.imports:
            parts.append(f"- {imp}")

    if b.symbols:
        parts.append("")
        parts.append("## Exports")
        listed = b.symbols[:max_symbols]
        for sym in listed:
            range_str = f"L{sym.line_start}" if sym.line_start == sym.line_end else f"L{sym.line_start}-{sym.line_end}"
            parts.append(f"- `{sym.signature}`  {range_str}")
            for child in sym.children[:8]:
                child_range = f"L{child.line_start}" if child.line_start == child.line_end else f"L{child.line_start}-{child.line_end}"
                parts.append(f"  - `{child.signature}`  {child_range}")
            if len(sym.children) > 8:
                parts.append(f"  - _… ({len(sym.children) - 8} more methods)_")
        if len(b.symbols) > max_symbols:
            parts.append(f"- _… ({len(b.symbols) - max_symbols} more symbols)_")

    if b.sections:
        parts.append("")
        parts.append("## Notable sections")
        for start, end, label in b.sections:
            parts.append(f"- L{start}-{end}: {label}")

    return "\n".join(parts).rstrip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

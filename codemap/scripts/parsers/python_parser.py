"""Extract module purpose and top-level symbols from Python source via ast."""

import ast
from typing import List, Optional

from .base import FileSummary, Symbol


def parse_python(source: str) -> FileSummary:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return FileSummary(parse_error=f"SyntaxError: {exc.msg} (line {exc.lineno})")

    purpose = _first_line(ast.get_docstring(tree))
    symbols: List[Symbol] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                symbols.append(Symbol(_format_function(node), "function"))
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                symbols.append(Symbol(_format_class(node), "class"))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and _is_public_constant(target.id):
                    symbols.append(Symbol(_format_constant(target.id, node.value), "constant"))
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and _is_public_constant(node.target.id):
                annotation = _safe_unparse(node.annotation) or "Any"
                symbols.append(Symbol(f"{node.target.id}: {annotation}", "constant"))

    return FileSummary(purpose=purpose, symbols=symbols)


def _format_function(node) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    rendered = _safe_unparse(node.args)
    args = rendered if rendered is not None else "..."
    returns = _safe_unparse(node.returns) if node.returns else None
    sig = f"{prefix} {node.name}({args})"
    if returns:
        sig += f" -> {returns}"
    return sig


def _format_class(node: ast.ClassDef) -> str:
    bases: List[str] = []
    for base in node.bases:
        rendered = _safe_unparse(base)
        if rendered:
            bases.append(rendered)
    return f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"


def _format_constant(name: str, value) -> str:
    rendered = _safe_unparse(value)
    if rendered and len(rendered) <= 40:
        return f"{name} = {rendered}"
    return name


def _is_public_constant(name: str) -> bool:
    if name.startswith("_"):
        return False
    return name.isupper() or any(c.isupper() for c in name)


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
        stripped = line.strip()
        if stripped:
            return stripped
    return None

from .base import FileSummary, Symbol
from .python_parser import parse_python
from .ts_js_parser import parse_ts_js
from .go_parser import parse_go

EXTENSION_PARSERS = {
    ".py": parse_python,
    ".ts": parse_ts_js,
    ".tsx": parse_ts_js,
    ".js": parse_ts_js,
    ".jsx": parse_ts_js,
    ".mjs": parse_ts_js,
    ".cjs": parse_ts_js,
    ".go": parse_go,
}


def parser_for(extension: str):
    return EXTENSION_PARSERS.get(extension.lower())


__all__ = [
    "FileSummary",
    "Symbol",
    "parse_python",
    "parse_ts_js",
    "parse_go",
    "parser_for",
    "EXTENSION_PARSERS",
]

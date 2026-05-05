"""codemap generator entrypoint.

Run from a project root (or any subdirectory) to produce CODEMAP.md.
See SKILL.md and the project README for usage details.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple

# Allow `python scripts/generate.py` invocation by adding the parent dir to sys.path.
_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from scripts.cache import (  # noqa: E402
    CachedEntry,
    entry_is_fresh,
    load_cache,
    make_entry,
    save_cache,
)
from scripts.parsers import EXTENSION_PARSERS, parser_for  # noqa: E402
from scripts.parsers.base import FileSummary  # noqa: E402
from scripts.tree import (  # noqa: E402
    filter_tree,
    render_tree,
    split_tests,
    walk,
)

MAX_FILES = 5000
DEFAULT_MAX_SYMBOLS = 30

LANGUAGE_LABELS = {
    ".py": "Python",
    ".ts": "TS",
    ".tsx": "TS",
    ".js": "JS",
    ".jsx": "JS",
    ".mjs": "JS",
    ".cjs": "JS",
    ".go": "Go",
}


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.root).resolve()

    if not repo_root.exists() or not repo_root.is_dir():
        print(f"codemap: error: root {repo_root} is not a directory", file=sys.stderr)
        return 2

    project_root = _find_project_root(repo_root)

    started = time.perf_counter()
    tree, files = walk(repo_root)

    if len(files) > MAX_FILES:
        print(
            f"codemap: error: {len(files)} files indexed exceeds limit of {MAX_FILES}.\n"
            f"  Re-run with --root <subdir> to scope the map.",
            file=sys.stderr,
        )
        return 3

    cache = load_cache(project_root)
    new_cache: Dict[str, CachedEntry] = {}
    summaries: Dict[str, FileSummary] = {}
    reused = 0
    reparsed = 0

    for file_path in files:
        rel = file_path.relative_to(repo_root).as_posix()
        ext = file_path.suffix.lower()
        parser = parser_for(ext)
        if parser is None:
            continue

        cached = cache.get(rel)
        if cached and not args.refresh and entry_is_fresh(cached, file_path):
            new_cache[rel] = cached
            summaries[rel] = cached.to_summary()
            reused += 1
            continue

        summary = _safe_parse(parser, file_path)
        entry = make_entry(file_path, summary)
        if entry is not None:
            new_cache[rel] = entry
        summaries[rel] = summary
        reparsed += 1

    save_cache(project_root, new_cache)

    main_files, test_files = split_tests(files, repo_root)
    if args.include_tests:
        main_files = main_files + test_files
        test_files = []

    output_path = _resolve_output_path(args.output, repo_root)
    content = _render_codemap(
        repo_root=repo_root,
        tree=tree,
        main_files=main_files,
        test_files=test_files,
        summaries=summaries,
        max_symbols=args.max_symbols,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    _maybe_suggest_gitignore(project_root, output_path)

    elapsed = time.perf_counter() - started
    if not args.quiet:
        symbol_files = sum(1 for s in summaries.values() if s.symbols)
        try:
            display_path = output_path.relative_to(repo_root)
        except ValueError:
            display_path = output_path
        print(
            f"codemap: wrote {display_path} "
            f"({len(files)} files, {symbol_files} with symbols, {elapsed:.2f}s)"
        )
        print(f"cache: {reused} reused, {reparsed} reparsed")

    return 0


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="codemap",
        description="Generate CODEMAP.md for the current repository.",
    )
    parser.add_argument("--root", default=".", help="Root directory to index (default: cwd).")
    parser.add_argument("--refresh", action="store_true", help="Ignore cache and reparse all files.")
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=DEFAULT_MAX_SYMBOLS,
        help=f"Truncate per-file symbol lists (default: {DEFAULT_MAX_SYMBOLS}).",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test files in the main tree (default: separate section).",
    )
    parser.add_argument(
        "--output",
        default="CODEMAP.md",
        help="Output path, relative to --root (default: CODEMAP.md).",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout summary.")
    return parser.parse_args(argv)


def _safe_parse(parser, file_path: Path) -> FileSummary:
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return FileSummary(parse_error=f"read error: {exc}")
    try:
        return parser(text)
    except Exception as exc:  # parser bugs should never crash the run
        return FileSummary(parse_error=f"{type(exc).__name__}: {exc}")


def _resolve_output_path(output: str, root: Path) -> Path:
    candidate = Path(output)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _find_project_root(start: Path) -> Path:
    """Treat the user-provided root as the project boundary.

    We don't walk up looking for a parent .git — when the user passes --root
    they're telling us where the project lives, and the cache should stay
    inside that scope (otherwise cwd choice could leak caches across repos
    or, in tests, across sibling fixtures).
    """
    return start


def _humanize_filename(name: str) -> str:
    stem = Path(name).stem
    cleaned = stem.replace("_", " ").replace("-", " ").strip()
    return cleaned or stem


def _build_purposes(
    files: List[Path],
    repo_root: Path,
    summaries: Dict[str, FileSummary],
) -> Dict[str, str]:
    purposes: Dict[str, str] = {}
    for f in files:
        rel = f.relative_to(repo_root).as_posix()
        summary = summaries.get(rel)
        if summary and summary.parse_error:
            purposes[rel] = "(parse error)"
        elif summary and summary.purpose:
            purposes[rel] = summary.purpose
        elif parser_for(f.suffix.lower()) is not None:
            purposes[rel] = _humanize_filename(f.name)
    return purposes


def _render_codemap(
    repo_root: Path,
    tree,
    main_files: List[Path],
    test_files: List[Path],
    summaries: Dict[str, FileSummary],
    max_symbols: int,
) -> str:
    lang_counter = Counter()
    for f in main_files + test_files:
        label = LANGUAGE_LABELS.get(f.suffix.lower())
        if label:
            lang_counter[label] += 1

    total = len(main_files) + len(test_files)
    project_name = repo_root.name or str(repo_root)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    parts: List[str] = []
    parts.append(f"# Codemap — {project_name}\n")
    languages = "  •  ".join(f"{lang} ({count})" for lang, count in lang_counter.most_common()) or "n/a"
    parts.append(f"Generated: {timestamp}")
    parts.append(f"Files indexed: {total}  •  Languages: {languages}")
    parts.append("")

    main_purposes = _build_purposes(main_files, repo_root, summaries)
    main_paths = {f.relative_to(repo_root).as_posix() for f in main_files}
    main_tree = filter_tree(tree, main_paths) or tree
    parts.append("## Tree\n")
    parts.append("```")
    parts.append(render_tree(main_tree, main_purposes))
    parts.append("```")
    parts.append("")

    if test_files:
        test_purposes = _build_purposes(test_files, repo_root, summaries)
        test_paths = {f.relative_to(repo_root).as_posix() for f in test_files}
        test_tree = filter_tree(tree, test_paths)
        if test_tree is not None:
            parts.append("## Tests\n")
            parts.append("```")
            parts.append(render_tree(test_tree, test_purposes))
            parts.append("```")
            parts.append("")

    parts.append("## Symbols\n")
    rendered_any = False
    for f in sorted(main_files + test_files, key=lambda p: p.relative_to(repo_root).as_posix()):
        rel = f.relative_to(repo_root).as_posix()
        summary = summaries.get(rel)
        if not summary or not summary.symbols:
            continue
        rendered_any = True
        parts.append(f"### {rel}")
        listed = summary.symbols[:max_symbols]
        for sym in listed:
            parts.append(f"- `{sym.signature}`")
        if len(summary.symbols) > max_symbols:
            parts.append(f"- _... ({len(summary.symbols) - max_symbols} more)_")
        parts.append("")
    if not rendered_any:
        parts.append("_No exported symbols extracted._\n")

    return "\n".join(parts).rstrip() + "\n"


def _maybe_suggest_gitignore(project_root: Path, output_path: Path) -> None:
    gi_path = project_root / ".gitignore"
    if not gi_path.exists():
        return
    try:
        text = gi_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    needed = []
    if "CODEMAP.md" not in text:
        needed.append("CODEMAP.md")
    if ".claude/codemap-cache.json" not in text:
        needed.append(".claude/codemap-cache.json")
    if needed:
        joined = ", ".join(needed)
        print(
            f"codemap: hint: consider adding the following to .gitignore: {joined}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    raise SystemExit(main())

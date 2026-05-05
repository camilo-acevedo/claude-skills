"""log-extract entrypoint.

Extract relevant lines (errors / warnings / panics by default, or a custom
regex) from a large log file. Hits are reported with surrounding context and
deduplicated by their normalized message so that one event repeated 1000
times collapses to one group.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_PATTERN = (
    r"(?ix)"
    r"\b(?:error|errno|exception|traceback|failed|failure|panic|fatal)\b"
    r"|\bWARN(?:ING)?\b"
)

DEFAULT_CONTEXT = 2
DEFAULT_MAX_HITS = 30
DEFAULT_TAIL = 5

# Patterns used to normalize a line so that timestamp / pid / address / line
# numbers do not prevent deduplication.
NORMALIZERS = [
    re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"),  # ISO timestamp
    re.compile(r"\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b"),  # bare time
    re.compile(r"\b0x[0-9a-fA-F]+\b"),  # hex address
    re.compile(r"\bpid[:= ]\d+\b", re.IGNORECASE),
    re.compile(r":\d+:\d+\b"),  # line:col
    re.compile(r"\b\d{4,}\b"),  # large numbers (counters, ports, ids)
]


def main(argv: Optional[List[str]] = None) -> int:
    # Make stdout safe on Windows cp1252.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    args = _parse_args(argv)
    log_path = Path(args.path).expanduser()
    if not log_path.exists() or not log_path.is_file():
        print(f"log-extract: error: file not found: {log_path}", file=sys.stderr)
        return 2

    try:
        pattern = re.compile(args.pattern)
    except re.error as exc:
        print(f"log-extract: error: invalid regex: {exc}", file=sys.stderr)
        return 2

    lines = _read_lines(log_path)
    head = lines[: args.head] if args.head > 0 else []
    tail = lines[-args.tail :] if args.tail > 0 else []

    hits = _find_hits(lines, pattern, context=args.context)
    groups = _dedup(hits) if not args.no_dedup else [(1, h, [h.first_line]) for h in hits]

    print(_render(
        log_path=log_path,
        total_lines=len(lines),
        total_hits=len(hits),
        groups=groups,
        head=head,
        tail=tail,
        max_hits=args.max_hits,
    ))
    return 0


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="log-extract")
    parser.add_argument("path")
    parser.add_argument("pattern", nargs="?", default=DEFAULT_PATTERN)
    parser.add_argument("--context", type=int, default=DEFAULT_CONTEXT)
    parser.add_argument("--max-hits", type=int, default=DEFAULT_MAX_HITS)
    parser.add_argument("--no-dedup", action="store_true")
    parser.add_argument("--head", type=int, default=0)
    parser.add_argument("--tail", type=int, default=DEFAULT_TAIL)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def _read_lines(path: Path) -> List[str]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return [line.rstrip("\n").rstrip("\r") for line in f]
    except OSError as exc:
        print(f"log-extract: error: cannot read {path}: {exc}", file=sys.stderr)
        return []


class Hit:
    __slots__ = ("center", "context_lines", "first_line")

    def __init__(self, center: int, context_lines: List[str], first_line: int):
        self.center = center
        self.context_lines = context_lines
        self.first_line = first_line


def _find_hits(lines: List[str], pattern: re.Pattern, context: int) -> List[Hit]:
    hits: List[Hit] = []
    for idx, line in enumerate(lines):
        if pattern.search(line):
            start = max(0, idx - context)
            end = min(len(lines), idx + context + 1)
            hits.append(Hit(center=idx, context_lines=lines[start:end], first_line=start + 1))
    return hits


def _normalize(line: str) -> str:
    out = line
    for pattern in NORMALIZERS:
        out = pattern.sub("∎", out)
    return out.strip()


def _dedup(hits: List[Hit]) -> List[Tuple[int, Hit, List[int]]]:
    """Group hits whose normalized center line matches; preserve insertion order."""
    grouped: OrderedDict = OrderedDict()
    for hit in hits:
        center_line = hit.context_lines[hit.center - hit.first_line + 1] if False else hit.context_lines[len(hit.context_lines) // 2]
        key = _normalize(center_line)
        if key in grouped:
            count, first_hit, lines_list = grouped[key]
            grouped[key] = (count + 1, first_hit, lines_list + [hit.first_line])
        else:
            grouped[key] = (1, hit, [hit.first_line])
    return [(c, h, lines) for c, h, lines in grouped.values()]


def _render(
    log_path: Path,
    total_lines: int,
    total_hits: int,
    groups: List[Tuple[int, Hit, List[int]]],
    head: List[str],
    tail: List[str],
    max_hits: int,
) -> str:
    parts: List[str] = []
    parts.append(
        f"log-extract: {log_path} ({total_lines} lines, {total_hits} hits → {len(groups)} unique)"
    )

    if head:
        parts.append("")
        parts.append(f"head ({len(head)}):")
        for line in head:
            parts.append(f"  {line}")

    if not groups:
        parts.append("")
        parts.append("no matches.")
    else:
        parts.append("")
        parts.append("hits:")
        for count, hit, line_numbers in groups[:max_hits]:
            parts.append("")
            if count > 1:
                first_ln = line_numbers[0]
                last_ln = line_numbers[-1]
                parts.append(f"[×{count} — first at line {first_ln}, last at line {last_ln}]")
            else:
                parts.append(f"[line {hit.first_line}]")
            for line in hit.context_lines:
                parts.append(f"  {line}")
        if len(groups) > max_hits:
            parts.append("")
            parts.append(f"… (+{len(groups) - max_hits} more hit groups)")

    if tail:
        parts.append("")
        parts.append(f"tail ({len(tail)}):")
        for line in tail:
            parts.append(f"  {line}")

    return "\n".join(parts).rstrip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

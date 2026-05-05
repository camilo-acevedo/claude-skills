"""session-handoff entrypoint.

Save / list / resume task context across Claude Code sessions. Files are
written to <root>/.claude/handoff/ with a structured frontmatter + body.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

HANDOFF_DIR_REL = ".claude/handoff"
DEFAULT_LIMIT = 10


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    parser = argparse.ArgumentParser(prog="session-handoff")
    sub = parser.add_subparsers(dest="cmd", required=True)

    save = sub.add_parser("save", help="Write a new handoff.")
    save.add_argument("--root", default=".")
    save.add_argument("--name", default=None)
    save.add_argument("--task", default="")
    save.add_argument("--decisions", default="")
    save.add_argument("--open", dest="open_questions", default="")
    save.add_argument("--files", default="")
    save.add_argument("--next", dest="next_steps", default="")
    save.add_argument("--notes", default="")
    save.add_argument("--from-stdin", action="store_true")

    list_cmd = sub.add_parser("list", help="List recent handoffs.")
    list_cmd.add_argument("--root", default=".")
    list_cmd.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    resume = sub.add_parser("resume", help="Print the latest (or a named) handoff.")
    resume.add_argument("--root", default=".")
    resume.add_argument("--name", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "save":
        return _save(args)
    if args.cmd == "list":
        return _list(args)
    if args.cmd == "resume":
        return _resume(args)
    return 2


# ---------- save ----------


def _save(args: argparse.Namespace) -> int:
    root = _project_root(args.root)
    handoff_dir = root / HANDOFF_DIR_REL
    handoff_dir.mkdir(parents=True, exist_ok=True)

    branch = _git_branch(root) or "(no branch)"
    timestamp = datetime.now(timezone.utc)

    if args.from_stdin:
        body = sys.stdin.read().strip()
        slug_source = args.name or args.task or "handoff"
    else:
        body = _build_body(args, branch=branch)
        slug_source = args.name or args.task or "handoff"

    slug = _slugify(slug_source) or "handoff"
    filename = f"{timestamp.strftime('%Y%m%d-%H%M%S')}-{slug}.md"
    path = handoff_dir / filename

    frontmatter = (
        "---\n"
        f"saved_at: {timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        f"branch: {branch}\n"
        f"slug: {slug}\n"
        "---\n\n"
    )
    path.write_text(frontmatter + body.rstrip() + "\n", encoding="utf-8")

    rel = _safe_rel(path, root)
    print(f"session-handoff: wrote {rel}")
    return 0


def _build_body(args: argparse.Namespace, branch: str) -> str:
    title = args.task.strip() or args.name or "session handoff"
    sections: List[str] = [f"# Handoff: {title}\n"]

    def add_section(heading: str, content: str) -> None:
        if not content.strip():
            return
        sections.append(f"## {heading}")
        sections.append(content.strip())
        sections.append("")

    add_section("Current task", args.task)
    add_section("Decisions made", args.decisions)
    add_section("Open questions", args.open_questions)
    if args.files.strip():
        files_block = "\n".join(f"- {f.strip()}" for f in args.files.split(",") if f.strip())
        add_section("Files touched", files_block)
    add_section("Next steps", args.next_steps)
    add_section("Notes", args.notes)

    if len(sections) == 1:  # only the title
        sections.append("_(empty handoff — no fields supplied)_")

    return "\n".join(sections)


# ---------- list ----------


def _list(args: argparse.Namespace) -> int:
    root = _project_root(args.root)
    files = _list_handoffs(root, args.limit)
    if not files:
        print("session-handoff: no handoffs found.")
        return 0
    handoff_dir = root / HANDOFF_DIR_REL
    print(f"{_safe_rel(handoff_dir, root)}/")
    now = time.time()
    for path in files:
        meta = _read_meta(path)
        age = _humanize_age(now - path.stat().st_mtime)
        branch = meta.branch or "(no branch)"
        print(f"  {path.name}   on {branch} ({age})")
    return 0


# ---------- resume ----------


def _resume(args: argparse.Namespace) -> int:
    root = _project_root(args.root)
    handoff_dir = root / HANDOFF_DIR_REL
    if args.name:
        match = _find_named(handoff_dir, args.name)
        if match is None:
            print(f"session-handoff: error: no handoff matches name {args.name!r}", file=sys.stderr)
            return 3
        path = match
    else:
        files = _list_handoffs(root, limit=1)
        if not files:
            print("session-handoff: error: no handoffs to resume.", file=sys.stderr)
            return 3
        path = files[0]

    meta = _read_meta(path)
    age = _humanize_age(time.time() - path.stat().st_mtime)
    print(f"# resuming {path.name} (saved {meta.saved_at or '?'} on {meta.branch or '?'}, {age})\n")
    body = _strip_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    sys.stdout.write(body)
    if not body.endswith("\n"):
        sys.stdout.write("\n")
    return 0


# ---------- helpers ----------


@dataclass
class HandoffMeta:
    saved_at: Optional[str] = None
    branch: Optional[str] = None
    slug: Optional[str] = None


def _list_handoffs(root: Path, limit: int) -> List[Path]:
    handoff_dir = root / HANDOFF_DIR_REL
    if not handoff_dir.exists():
        return []
    files = sorted(
        (p for p in handoff_dir.iterdir() if p.is_file() and p.suffix.lower() == ".md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[: max(1, limit)]


def _find_named(handoff_dir: Path, name: str) -> Optional[Path]:
    if not handoff_dir.exists():
        return None
    candidates = [p for p in handoff_dir.iterdir() if p.is_file() and name in p.name]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _read_meta(path: Path) -> HandoffMeta:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return HandoffMeta()
    meta = HandoffMeta()
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end]
            for line in block.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key == "saved_at":
                    meta.saved_at = value
                elif key == "branch":
                    meta.branch = value
                elif key == "slug":
                    meta.slug = value
    return meta


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4 :].lstrip("\n")


def _project_root(arg: str) -> Path:
    base = Path(arg).resolve()
    for candidate in [base, *base.parents]:
        if (candidate / ".git").exists():
            return candidate
    return base


def _git_branch(root: Path) -> Optional[str]:
    if shutil.which("git") is None:
        return None
    try:
        result = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:60]


def _humanize_age(seconds: float) -> str:
    seconds = max(0.0, seconds)
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    return f"{int(seconds // 86400)}d ago"


def _safe_rel(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _ignored(_unused: Iterable[str]) -> None:  # placeholder for future use
    return None


if __name__ == "__main__":
    raise SystemExit(main())

"""answer-cache entrypoint.

Cache Q&A about the codebase keyed by a normalized question and a list of
linked source files. Linked files' sha256 are recorded at save time; if any
change, the entry is reported as stale on next ask.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

CACHE_DIR_REL = ".claude/answers"
INDEX_FILE = "index.json"
INDEX_VERSION = 1
DEFAULT_LIMIT = 20


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    parser = argparse.ArgumentParser(prog="answer-cache")
    sub = parser.add_subparsers(dest="cmd", required=True)

    ask = sub.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--root", default=".")

    save = sub.add_parser("save")
    save.add_argument("question")
    save.add_argument("--answer", default=None)
    save.add_argument("--files", default="")
    save.add_argument("--from-stdin", action="store_true")
    save.add_argument("--root", default=".")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--root", default=".")
    list_cmd.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    forget = sub.add_parser("forget")
    forget.add_argument("question")
    forget.add_argument("--root", default=".")

    args = parser.parse_args(argv)
    if args.cmd == "ask":
        return _ask(args)
    if args.cmd == "save":
        return _save(args)
    if args.cmd == "list":
        return _list(args)
    if args.cmd == "forget":
        return _forget(args)
    return 2


# ---------- ask ----------


def _ask(args: argparse.Namespace) -> int:
    root = _project_root(args.root)
    index = _load_index(root)
    qhash = _hash_question(args.question)
    entry = index.entries.get(qhash)
    if entry is None:
        print(f"answer-cache: miss for {args.question!r}")
        return 1

    answer = _load_answer(root, qhash)
    if answer is None:
        print(f"answer-cache: error: index has entry but answer file is missing for {args.question!r}", file=sys.stderr)
        return 4

    stale_files = _stale_files(root, entry)
    age = _humanize_age(time.time() - entry.saved_at_epoch)

    if stale_files:
        names = ", ".join(stale_files[:5]) + (" …" if len(stale_files) > 5 else "")
        print(f"answer-cache: STALE ({len(stale_files)}/{len(entry.files)} linked files changed: {names})")
        print()
        print("(prior answer follows, treat as outdated:)")
        print(answer)
        return 2

    print(f"# answer-cache: hit (saved {entry.saved_at_iso}, {age})")
    print()
    print(answer.rstrip())
    return 0


# ---------- save ----------


def _save(args: argparse.Namespace) -> int:
    root = _project_root(args.root)
    if args.from_stdin:
        body = sys.stdin.read().strip()
    else:
        body = (args.answer or "").strip()
    if not body:
        print("answer-cache: error: empty answer (pass --answer or --from-stdin with content)", file=sys.stderr)
        return 2

    files: List[Dict[str, str]] = []
    for raw in args.files.split(","):
        path_str = raw.strip()
        if not path_str:
            continue
        file_path = (root / path_str).resolve() if not os.path.isabs(path_str) else Path(path_str)
        if not file_path.exists() or not file_path.is_file():
            print(f"answer-cache: warning: linked file not found, skipping: {path_str}", file=sys.stderr)
            continue
        try:
            rel = file_path.relative_to(root).as_posix()
        except ValueError:
            rel = str(file_path)
        files.append({"path": rel, "sha256": _hash_file(file_path)})

    qhash = _hash_question(args.question)
    now = datetime.now(timezone.utc)
    entry = AnswerEntry(
        question=args.question.strip(),
        saved_at_iso=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        saved_at_epoch=now.timestamp(),
        files=files,
    )

    index = _load_index(root)
    index.entries[qhash] = entry
    _save_index(root, index)
    _save_answer(root, qhash, body)

    if files:
        names = ", ".join(f["path"] for f in files[:6])
        more = f", +{len(files) - 6} more" if len(files) > 6 else ""
        print(f"answer-cache: saved ({len(files)} files linked: {names}{more})")
    else:
        print("answer-cache: saved (no files linked — entry will never go stale automatically)")
    return 0


# ---------- list ----------


def _list(args: argparse.Namespace) -> int:
    root = _project_root(args.root)
    index = _load_index(root)
    if not index.entries:
        print("answer-cache: empty.")
        return 0
    cache_dir = root / CACHE_DIR_REL
    print(f"{_safe_rel(cache_dir, root)}/  ({len(index.entries)} entries)")
    items = sorted(index.entries.values(), key=lambda e: e.saved_at_epoch, reverse=True)[: args.limit]
    width = min(60, max(len(e.question) for e in items))
    for entry in items:
        age = _humanize_age(time.time() - entry.saved_at_epoch)
        question = entry.question
        if len(question) > 60:
            question = question[:57] + "…"
        print(f"- {question:<{width}}  {len(entry.files)} file{'s' if len(entry.files) != 1 else ''}  (saved {age})")
    return 0


# ---------- forget ----------


def _forget(args: argparse.Namespace) -> int:
    root = _project_root(args.root)
    qhash = _hash_question(args.question)
    index = _load_index(root)
    if qhash not in index.entries:
        print(f"answer-cache: no entry for {args.question!r}")
        return 1
    del index.entries[qhash]
    _save_index(root, index)
    answer_path = root / CACHE_DIR_REL / f"{qhash}.md"
    if answer_path.exists():
        answer_path.unlink()
    print(f"answer-cache: forgot {args.question!r}")
    return 0


# ---------- index / answer files ----------


@dataclass
class AnswerEntry:
    question: str
    saved_at_iso: str
    saved_at_epoch: float
    files: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class Index:
    entries: Dict[str, AnswerEntry] = field(default_factory=dict)


def _index_path(root: Path) -> Path:
    return root / CACHE_DIR_REL / INDEX_FILE


def _load_index(root: Path) -> Index:
    path = _index_path(root)
    if not path.exists():
        return Index()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Index()
    if raw.get("version") != INDEX_VERSION:
        return Index()
    out = Index()
    for qhash, data in (raw.get("entries") or {}).items():
        try:
            out.entries[qhash] = AnswerEntry(
                question=data["question"],
                saved_at_iso=data["saved_at_iso"],
                saved_at_epoch=float(data["saved_at_epoch"]),
                files=data.get("files", []),
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _save_index(root: Path, index: Index) -> None:
    path = _index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "version": INDEX_VERSION,
        "entries": {
            qhash: {
                "question": e.question,
                "saved_at_iso": e.saved_at_iso,
                "saved_at_epoch": e.saved_at_epoch,
                "files": e.files,
            }
            for qhash, e in index.entries.items()
        },
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _save_answer(root: Path, qhash: str, body: str) -> None:
    path = root / CACHE_DIR_REL / f"{qhash}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.rstrip() + "\n", encoding="utf-8")


def _load_answer(root: Path, qhash: str) -> Optional[str]:
    path = root / CACHE_DIR_REL / f"{qhash}.md"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ---------- helpers ----------


def _project_root(arg: str) -> Path:
    base = Path(arg).resolve()
    for candidate in [base, *base.parents]:
        if (candidate / ".git").exists():
            return candidate
    return base


def _hash_question(text: str) -> str:
    normalized = _normalize_question(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _normalize_question(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _stale_files(root: Path, entry: AnswerEntry) -> List[str]:
    stale: List[str] = []
    for record in entry.files:
        path = root / record["path"]
        if not path.exists():
            stale.append(record["path"])
            continue
        try:
            current = _hash_file(path)
        except OSError:
            stale.append(record["path"])
            continue
        if current != record["sha256"]:
            stale.append(record["path"])
    return stale


def _humanize_age(seconds: float) -> str:
    seconds = max(0.0, seconds)
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h ago"
    if seconds < 604800:
        return f"{int(seconds // 86400)}d ago"
    return f"{int(seconds // 604800)}w ago"


def _safe_rel(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())

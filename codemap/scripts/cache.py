"""Per-project cache for codemap parse results.

Stored at <repo>/.claude/codemap-cache.json. Entries are invalidated when a
file's sha256 or mtime changes.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .parsers.base import FileSummary, Symbol

CACHE_VERSION = 1
CACHE_RELATIVE_PATH = ".claude/codemap-cache.json"


@dataclass
class CachedEntry:
    sha256: str
    mtime: float
    size: int
    purpose: Optional[str] = None
    symbols: List[Dict[str, str]] = field(default_factory=list)
    parse_error: Optional[str] = None

    def to_summary(self) -> FileSummary:
        return FileSummary(
            purpose=self.purpose,
            symbols=[Symbol(s["signature"], s["kind"]) for s in self.symbols],
            parse_error=self.parse_error,
        )


def cache_path(repo_root: Path) -> Path:
    return repo_root / CACHE_RELATIVE_PATH


def load_cache(repo_root: Path) -> Dict[str, CachedEntry]:
    path = cache_path(repo_root)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if raw.get("version") != CACHE_VERSION:
        return {}
    out: Dict[str, CachedEntry] = {}
    for rel, entry in raw.get("files", {}).items():
        try:
            out[rel] = CachedEntry(
                sha256=entry["sha256"],
                mtime=entry["mtime"],
                size=entry["size"],
                purpose=entry.get("purpose"),
                symbols=entry.get("symbols", []),
                parse_error=entry.get("parse_error"),
            )
        except (KeyError, TypeError):
            continue
    return out


def save_cache(repo_root: Path, entries: Dict[str, CachedEntry]) -> None:
    path = cache_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CACHE_VERSION,
        "files": {rel: asdict(entry) for rel, entry in sorted(entries.items())},
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def stat_signature(file_path: Path) -> Optional[tuple]:
    try:
        st = file_path.stat()
        return (st.st_mtime, st.st_size)
    except OSError:
        return None


def hash_file(file_path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def make_entry(file_path: Path, summary: FileSummary) -> Optional[CachedEntry]:
    try:
        st = file_path.stat()
    except OSError:
        return None
    sha = hash_file(file_path)
    if sha is None:
        return None
    return CachedEntry(
        sha256=sha,
        mtime=st.st_mtime,
        size=st.st_size,
        purpose=summary.purpose,
        symbols=[{"signature": s.signature, "kind": s.kind} for s in summary.symbols],
        parse_error=summary.parse_error,
    )


def entry_is_fresh(entry: CachedEntry, file_path: Path) -> bool:
    """Cheap mtime+size check; falls back to sha256 only when mtime mismatches."""
    sig = stat_signature(file_path)
    if sig is None:
        return False
    mtime, size = sig
    if size != entry.size:
        return False
    if abs(mtime - entry.mtime) < 1e-6:
        return True
    sha = hash_file(file_path)
    return sha == entry.sha256

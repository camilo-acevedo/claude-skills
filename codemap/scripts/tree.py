"""Build a filtered file tree honoring .gitignore and built-in skip rules."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Tuple

DEFAULT_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".claude",  # local tool state (incl. our own cache)
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    "out",
    "target",
    ".next",
    ".nuxt",
    ".turbo",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".idea",
    ".vscode",
    "coverage",
    ".gradle",
    ".terraform",
    "vendor",
    "bin",
    "obj",
}

# File names that should never appear in the tree (own derived artifact, lock files Claude doesn't need to navigate).
DEFAULT_SKIP_FILES = {
    "CODEMAP.md",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    "go.sum",
    "uv.lock",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".mp3", ".mp4", ".mov", ".avi", ".webm", ".wav", ".flac",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".class", ".jar", ".pyc", ".pyo", ".so", ".dll", ".dylib", ".o",
    ".db", ".sqlite", ".sqlite3",
}


@dataclass
class GitignoreRule:
    pattern: str
    negate: bool
    dir_only: bool
    anchored: bool


@dataclass
class TreeNode:
    name: str
    path: PurePosixPath
    is_dir: bool
    children: List["TreeNode"] = field(default_factory=list)


def load_gitignore(root: Path) -> List[GitignoreRule]:
    rules: List[GitignoreRule] = []
    gi = root / ".gitignore"
    if not gi.exists():
        return rules
    try:
        text = gi.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return rules
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        negate = line.startswith("!")
        if negate:
            line = line[1:]
        dir_only = line.endswith("/")
        if dir_only:
            line = line[:-1]
        anchored = line.startswith("/")
        if anchored:
            line = line[1:]
        rules.append(GitignoreRule(pattern=line, negate=negate, dir_only=dir_only, anchored=anchored))
    return rules


def gitignore_matches(rules: List[GitignoreRule], rel_posix: str, is_dir: bool) -> bool:
    """Return True if the path is ignored by gitignore rules."""
    matched = False
    for rule in rules:
        if rule.dir_only and not is_dir:
            continue
        if _rule_matches(rule, rel_posix):
            matched = not rule.negate
    return matched


def _rule_matches(rule: GitignoreRule, rel_posix: str) -> bool:
    pattern = rule.pattern
    if rule.anchored:
        return _fnmatch_path(rel_posix, pattern)
    # unanchored: match the pattern against any path suffix segment-by-segment
    if "/" in pattern:
        return _fnmatch_path(rel_posix, pattern) or _fnmatch_path(rel_posix, "**/" + pattern)
    parts = rel_posix.split("/")
    return any(fnmatch.fnmatchcase(p, pattern) for p in parts)


def _fnmatch_path(path: str, pattern: str) -> bool:
    if "**" not in pattern:
        return fnmatch.fnmatchcase(path, pattern)
    # Translate ** manually: ** matches zero or more path segments
    regex_parts = []
    for piece in pattern.split("/"):
        if piece == "**":
            regex_parts.append(".*")
        else:
            regex_parts.append(fnmatch.translate(piece).rstrip("\\Z").lstrip("(?s:").rstrip(")"))
    import re
    regex = "^" + "/".join(regex_parts) + "$"
    try:
        return re.match(regex, path) is not None
    except re.error:
        return False


def walk(
    root: Path,
    extra_skip_dirs: Optional[Iterable[str]] = None,
    follow_symlinks: bool = False,
) -> Tuple[TreeNode, List[Path]]:
    """Walk `root` and return (tree, list of file paths)."""
    rules = load_gitignore(root)
    skip_dirs = set(DEFAULT_SKIP_DIRS)
    if extra_skip_dirs:
        skip_dirs.update(extra_skip_dirs)

    seen_real: set = set()
    files: List[Path] = []
    root_node = TreeNode(name=root.name or str(root), path=PurePosixPath("."), is_dir=True)

    def recurse(directory: Path, node: TreeNode):
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except (PermissionError, OSError):
            return

        for entry in entries:
            name = entry.name
            try:
                is_dir = entry.is_dir()
            except OSError:
                continue

            rel = entry.relative_to(root).as_posix()

            if is_dir and name in skip_dirs:
                continue
            if not is_dir and name in DEFAULT_SKIP_FILES:
                continue
            if not is_dir and entry.suffix.lower() in BINARY_EXTENSIONS:
                continue
            if gitignore_matches(rules, rel, is_dir):
                continue

            if not follow_symlinks and entry.is_symlink():
                continue
            try:
                real = entry.resolve()
            except OSError:
                continue
            if real in seen_real:
                continue
            seen_real.add(real)

            child = TreeNode(name=name, path=PurePosixPath(rel), is_dir=is_dir)
            node.children.append(child)
            if is_dir:
                recurse(entry, child)
            else:
                files.append(entry)

    recurse(root, root_node)
    return root_node, files


def render_tree(node: TreeNode, purposes: Dict[str, str], include_root: bool = True) -> str:
    """Render the tree as a string with optional one-line purpose per file."""
    lines: List[str] = []

    if include_root:
        lines.append(f"{node.name}/")

    def recurse(current: TreeNode, prefix: str):
        children = current.children
        for index, child in enumerate(children):
            last = index == len(children) - 1
            connector = "└── " if last else "├── "
            line = prefix + connector + (child.name + "/" if child.is_dir else child.name)
            purpose = purposes.get(str(child.path)) if not child.is_dir else None
            if purpose:
                pad = max(2, 32 - len(connector) - len(child.name) - len(prefix))
                line = f"{line}{' ' * pad}— {purpose}"
            lines.append(line)
            if child.is_dir:
                extension = "    " if last else "│   "
                recurse(child, prefix + extension)

    recurse(node, "")
    return "\n".join(lines)


def split_tests(files: Iterable[Path], root: Path) -> Tuple[List[Path], List[Path]]:
    """Return (non_test_files, test_files)."""
    non_test: List[Path] = []
    tests: List[Path] = []
    for f in files:
        rel = f.relative_to(root).as_posix().lower()
        name = f.name.lower()
        is_test = (
            "/test" in "/" + rel
            or "/tests/" in "/" + rel
            or name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith(".test.ts")
            or name.endswith(".test.js")
            or name.endswith(".spec.ts")
            or name.endswith(".spec.js")
            or name.endswith("_test.go")
        )
        (tests if is_test else non_test).append(f)
    return non_test, tests


def filter_tree(node: TreeNode, allowed_paths: set) -> Optional[TreeNode]:
    """Return a copy of `node` with only branches that lead to a file in `allowed_paths`."""
    if not node.is_dir:
        return node if str(node.path) in allowed_paths else None
    new_children = []
    for child in node.children:
        kept = filter_tree(child, allowed_paths)
        if kept is not None:
            new_children.append(kept)
    if not new_children and node.path != PurePosixPath("."):
        return None
    new_node = TreeNode(name=node.name, path=node.path, is_dir=True, children=new_children)
    return new_node

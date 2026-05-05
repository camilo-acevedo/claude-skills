"""diff-summary entrypoint.

Produce a categorized Markdown summary of a git diff. By default the diff is
computed between HEAD and the tracked upstream (or origin/main if no upstream
is configured). The output is intended to be read once instead of streaming
the full diff into Claude's context.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Optional, Tuple

CATEGORY_RULES = [
    ("generated", re.compile(r"(?:^|/)(?:package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Cargo\.lock|go\.sum|uv\.lock)$")),
    ("tests", re.compile(r"(?:^|/)(?:tests?|spec|__tests__)/|(?:\.|_)(?:test|spec)\.(?:py|ts|tsx|js|jsx|go|rs)$")),
    ("docs", re.compile(r"\.(?:md|rst|adoc|txt)$|(?:^|/)docs?/")),
    ("config", re.compile(
        r"\.(?:json|ya?ml|toml|ini|cfg|env|gitignore|dockerfile|tf|tfvars)$"
        r"|(?:^|/)(?:Dockerfile|Makefile|tsconfig\.json|package\.json|pyproject\.toml|requirements\.txt)$"
    )),
    ("ci", re.compile(r"(?:^|/)\.(?:github|gitlab|circleci|drone)/|(?:^|/)\.gitlab-ci\.yml$")),
    ("src", re.compile(r".+")),
]

MAX_FILES_TABLE = 1000


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    repo = Path(args.root).resolve()

    if shutil.which("git") is None:
        print("diff-summary: error: 'git' not found in PATH", file=sys.stderr)
        return 4

    repo = _find_repo(repo)
    if repo is None:
        print(f"diff-summary: error: not a git repository: {args.root}", file=sys.stderr)
        return 2

    if args.staged:
        diff_args = ["diff", "--cached"]
        comparison_label = "staged vs HEAD"
        full_command = "git diff --cached"
    else:
        ref = args.against or _default_against(repo)
        if ref is None:
            print("diff-summary: error: no upstream configured and origin/main not present; pass --against <ref>.", file=sys.stderr)
            return 3
        if not _ref_exists(repo, ref):
            print(f"diff-summary: error: ref does not exist: {ref}", file=sys.stderr)
            return 3
        diff_args = ["diff", f"{ref}...HEAD"]
        comparison_label = f"HEAD vs {ref}"
        full_command = f"git diff {ref}...HEAD"

    files = _collect_numstat(repo, diff_args)
    if not files:
        print(f"# diff-summary — {repo.name or str(repo)}\n\nNo changes ({comparison_label}).")
        return 0

    insertions = sum(f[0] for f in files)
    deletions = sum(f[1] for f in files)
    by_category = _categorize(files)

    print(_render(
        repo_name=repo.name or str(repo),
        comparison=comparison_label,
        files=files,
        insertions=insertions,
        deletions=deletions,
        by_category=by_category,
        samples=_collect_samples(repo, diff_args, files, args.samples),
        top=args.top,
        full_command=full_command,
    ))
    return 0


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="diff-summary")
    parser.add_argument("--root", default=".")
    parser.add_argument("--against", default=None)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def _git(repo: Path, *args: str) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return 127, "", str(exc)
    return result.returncode, result.stdout, result.stderr


def _find_repo(start: Path) -> Optional[Path]:
    for current in [start, *start.parents]:
        if (current / ".git").exists():
            return current
    return None


def _default_against(repo: Path) -> Optional[str]:
    code, up, _ = _git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if code == 0 and up.strip():
        return up.strip()
    code, _, _ = _git(repo, "rev-parse", "--verify", "--quiet", "origin/main")
    if code == 0:
        return "origin/main"
    code, _, _ = _git(repo, "rev-parse", "--verify", "--quiet", "main")
    if code == 0:
        return "main"
    return None


def _ref_exists(repo: Path, ref: str) -> bool:
    code, _, _ = _git(repo, "rev-parse", "--verify", "--quiet", ref)
    return code == 0


def _collect_numstat(repo: Path, diff_args: List[str]) -> List[Tuple[int, int, str]]:
    code, out, _ = _git(repo, *diff_args, "--numstat")
    if code != 0:
        return []
    files: List[Tuple[int, int, str]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        ins_raw, del_raw, path = parts[0], parts[1], parts[2]
        try:
            ins = int(ins_raw) if ins_raw != "-" else 0
            dels = int(del_raw) if del_raw != "-" else 0
        except ValueError:
            ins, dels = 0, 0
        files.append((ins, dels, path))
    return files


def _categorize(files: List[Tuple[int, int, str]]) -> "dict[str, list[Tuple[int, int, str]]]":
    by_category: dict = defaultdict(list)
    for ins, dels, path in files:
        cat = _category_for(path)
        by_category[cat].append((ins, dels, path))
    return by_category


def _category_for(path: str) -> str:
    for name, pattern in CATEGORY_RULES:
        if pattern.search(path):
            return name
    return "src"


def _collect_samples(
    repo: Path,
    diff_args: List[str],
    files: List[Tuple[int, int, str]],
    samples: int,
) -> List[Tuple[str, str]]:
    if samples <= 0:
        return []
    # Pick non-generated files with the most changes.
    candidates = [
        (ins + dels, path)
        for ins, dels, path in files
        if _category_for(path) != "generated"
    ]
    candidates.sort(reverse=True)
    chosen_paths = [p for _, p in candidates[:samples]]
    out: List[Tuple[str, str]] = []
    for path in chosen_paths:
        code, body, _ = _git(repo, *diff_args, "--", path)
        if code != 0:
            continue
        snippet = _first_hunk(body, max_lines=20)
        if snippet:
            out.append((path, snippet))
    return out


def _first_hunk(diff_body: str, max_lines: int) -> str:
    lines = diff_body.splitlines()
    started = False
    out: List[str] = []
    for line in lines:
        if line.startswith("@@"):
            if started:
                break
            started = True
        if started:
            out.append(line)
            if len(out) >= max_lines:
                break
    return "\n".join(out)


def _render(
    repo_name: str,
    comparison: str,
    files: List[Tuple[int, int, str]],
    insertions: int,
    deletions: int,
    by_category: "dict[str, list[Tuple[int, int, str]]]",
    samples: List[Tuple[str, str]],
    top: int,
    full_command: str,
) -> str:
    parts: List[str] = []
    parts.append(f"# diff-summary — {repo_name}\n")
    parts.append(f"_{comparison}_")
    parts.append("")

    parts.append("## Stats")
    parts.append(f"- {len(files)} files changed, {insertions} insertions(+), {deletions} deletions(-)")
    parts.append(f"- Net: {insertions - deletions:+} lines")
    parts.append("")

    parts.append("## Categories")
    for name in ["src", "tests", "config", "docs", "ci", "generated"]:
        bucket = by_category.get(name, [])
        if not bucket:
            continue
        ins = sum(f[0] for f in bucket)
        dels = sum(f[1] for f in bucket)
        parts.append(f"- {name}: {len(bucket)} file{'s' if len(bucket) != 1 else ''}  (+{ins} / -{dels})")
    parts.append("")

    if len(files) > MAX_FILES_TABLE:
        parts.append(f"## Top files (showing {top}; full list omitted — {len(files)} total)")
    else:
        parts.append(f"## Top files (by total LOC changed, top {top})")
    sorted_files = sorted(files, key=lambda t: t[0] + t[1], reverse=True)[:top]
    parts.append("| File | + | - |")
    parts.append("|------|---|---|")
    for ins, dels, path in sorted_files:
        parts.append(f"| `{path}` | {ins} | {dels} |")
    parts.append("")

    if samples:
        parts.append(f"## Sample hunks ({len(samples)})")
        for path, body in samples:
            parts.append(f"### `{path}` (first hunk)")
            parts.append("```diff")
            parts.append(body)
            parts.append("```")
        parts.append("")

    parts.append("## Full diff")
    parts.append(f"`{full_command}`")
    return "\n".join(parts).rstrip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())

"""git-digest entrypoint.

Bundle several git queries into a single Markdown report so Claude does not
need to spawn 4-5 separate tool calls (status / log / diff --stat / branch /
stash) every time it wants context on the repo state.

Run from a git working tree (or pass --root). Output goes to stdout.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_COMMITS = 5
FALLBACK_DIFF_REF = "HEAD~10"


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    repo = Path(args.root).resolve()

    if shutil.which("git") is None:
        print("git-digest: error: 'git' not found in PATH", file=sys.stderr)
        return 4

    if not (repo / ".git").exists():
        # Walk up — the user may have invoked from a subdirectory.
        for candidate in [repo, *repo.parents]:
            if (candidate / ".git").exists():
                repo = candidate
                break
        else:
            print(f"git-digest: error: not a git repository: {args.root}", file=sys.stderr)
            return 2

    branch_info = _branch_info(repo)
    status_info = _status_info(repo)

    if _is_pristine(branch_info, status_info):
        print(_pristine_summary(repo, branch_info))
        return 0

    sections: List[str] = []
    sections.append(_render_header(repo))
    sections.append(_render_branch(branch_info))
    sections.append(_render_status(status_info))
    sections.append(_render_commits(repo, args.commits))
    if not args.no_diff:
        diff_section = _render_diff(repo, args.against, branch_info)
        if diff_section:
            sections.append(diff_section)
    sections.append(_render_stash(repo))

    print("\n\n".join(s for s in sections if s).rstrip() + "\n")
    return 0


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="git-digest",
        description="Bundle git status / log / diff --stat / branch -vv into one report.",
    )
    parser.add_argument("--root", default=".", help="Repo to inspect (default: cwd).")
    parser.add_argument(
        "--commits",
        type=int,
        default=DEFAULT_COMMITS,
        help=f"Number of recent commits to list (default: {DEFAULT_COMMITS}).",
    )
    parser.add_argument(
        "--against",
        default=None,
        help="Ref to diff against (default: tracked upstream, falling back to HEAD~10).",
    )
    parser.add_argument(
        "--no-diff",
        action="store_true",
        help="Skip the diffstat section (faster on huge ranges).",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress trailing footers.")
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


def _git_lines(repo: Path, *args: str) -> List[str]:
    code, out, _ = _git(repo, *args)
    if code != 0:
        return []
    return [line for line in out.splitlines() if line.strip() != ""]


# ---------- collectors ----------


class BranchInfo:
    def __init__(self) -> None:
        self.current: Optional[str] = None
        self.upstream: Optional[str] = None
        self.ahead: int = 0
        self.behind: int = 0
        self.default: Optional[str] = None
        self.detached: bool = False


def _branch_info(repo: Path) -> BranchInfo:
    info = BranchInfo()

    code, head, _ = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    if code == 0 and head.strip():
        info.current = head.strip()
    else:
        info.detached = True
        _, sha, _ = _git(repo, "rev-parse", "--short", "HEAD")
        info.current = f"(detached {sha.strip()})" if sha.strip() else "(detached)"

    if not info.detached:
        code, up, _ = _git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        if code == 0 and up.strip():
            info.upstream = up.strip()
            code, counts, _ = _git(repo, "rev-list", "--left-right", "--count", f"{info.upstream}...HEAD")
            if code == 0 and counts.strip():
                parts = counts.split()
                if len(parts) == 2:
                    try:
                        info.behind, info.ahead = int(parts[0]), int(parts[1])
                    except ValueError:
                        pass

    code, default, _ = _git(repo, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if code == 0 and default.strip():
        info.default = default.strip().split("/", 1)[-1]

    return info


class StatusInfo:
    def __init__(self) -> None:
        self.entries: List[str] = []
        self.modified = 0
        self.staged = 0
        self.untracked = 0
        self.conflicted = 0


def _status_info(repo: Path) -> StatusInfo:
    info = StatusInfo()
    lines = _git_lines(repo, "status", "--porcelain=v1", "--untracked-files=normal")
    for line in lines:
        info.entries.append(line)
        if len(line) < 2:
            continue
        x, y = line[0], line[1]
        if x == "?" and y == "?":
            info.untracked += 1
            continue
        if x in "DAU" and y in "DAU" and x != " " and y != " ":
            info.conflicted += 1
            continue
        if x.strip():
            info.staged += 1
        if y.strip():
            info.modified += 1
    return info


def _is_pristine(branch: BranchInfo, status: StatusInfo) -> bool:
    if status.entries:
        return False
    if branch.detached:
        return False
    if branch.upstream is None:
        return False
    return branch.ahead == 0 and branch.behind == 0


# ---------- renderers ----------


def _render_header(repo: Path) -> str:
    return f"# git-digest — {repo.name or str(repo)}"


def _render_branch(branch: BranchInfo) -> str:
    parts = ["## Branch", f"- Current: {branch.current}"]
    if branch.detached:
        parts.append("- (detached HEAD — no upstream tracking)")
    elif branch.upstream:
        rel = []
        if branch.ahead:
            rel.append(f"ahead {branch.ahead}")
        if branch.behind:
            rel.append(f"behind {branch.behind}")
        rel_str = ", ".join(rel) if rel else "in sync"
        parts.append(f"- Tracking: {branch.upstream} ({rel_str})")
    else:
        parts.append("- Tracking: (no upstream)")
    if branch.default and branch.default != branch.current:
        parts.append(f"- Default: {branch.default}")
    return "\n".join(parts)


def _render_status(status: StatusInfo) -> str:
    if not status.entries:
        return "## Working tree\nclean"
    summary_bits = []
    if status.staged:
        summary_bits.append(f"{status.staged} staged")
    if status.modified:
        summary_bits.append(f"{status.modified} modified")
    if status.untracked:
        summary_bits.append(f"{status.untracked} untracked")
    if status.conflicted:
        summary_bits.append(f"{status.conflicted} conflicted")
    summary = ", ".join(summary_bits) or "changes present"
    body = "\n".join(status.entries)
    return f"## Working tree ({summary})\n```\n{body}\n```"


def _render_commits(repo: Path, count: int) -> str:
    fmt = "- %h (%ar) %s — %an"
    lines = _git_lines(repo, "log", f"-{count}", f"--pretty=format:{fmt}")
    if not lines:
        return "## Recent commits\n(no commits)"
    return f"## Recent commits (last {count})\n" + "\n".join(lines)


def _render_diff(repo: Path, against: Optional[str], branch: BranchInfo) -> Optional[str]:
    ref = against or branch.upstream or FALLBACK_DIFF_REF
    code, _, _ = _git(repo, "rev-parse", "--verify", "--quiet", ref)
    if code != 0:
        ref = FALLBACK_DIFF_REF
        code, _, _ = _git(repo, "rev-parse", "--verify", "--quiet", ref)
        if code != 0:
            return None

    code, shortstat, _ = _git(repo, "diff", "--shortstat", f"{ref}...HEAD")
    summary = shortstat.strip() or "no commit-level changes"

    code, numstat, _ = _git(repo, "diff", "--numstat", f"{ref}...HEAD")
    file_lines = []
    if code == 0:
        for raw in numstat.splitlines():
            parts = raw.split("\t")
            if len(parts) < 3:
                continue
            ins, dels, path = parts[0], parts[1], parts[2]
            try:
                key = (int(ins) if ins != "-" else 0) + (int(dels) if dels != "-" else 0)
            except ValueError:
                key = 0
            file_lines.append((key, ins, dels, path))
        file_lines.sort(key=lambda t: t[0], reverse=True)

    body = [f"## Diff vs {ref}", f"- {summary}"]
    if file_lines:
        body.append("- Top files:")
        for _, ins, dels, path in file_lines[:10]:
            body.append(f"  - {path}  +{ins} / -{dels}")
        if len(file_lines) > 10:
            body.append(f"  - … ({len(file_lines) - 10} more)")
    return "\n".join(body)


def _render_stash(repo: Path) -> str:
    lines = _git_lines(repo, "stash", "list")
    if not lines:
        return "## Stash\n(empty)"
    body = "\n".join(f"- {line}" for line in lines)
    return f"## Stash ({len(lines)})\n{body}"


def _pristine_summary(repo: Path, branch: BranchInfo) -> str:
    upstream = branch.upstream or "origin"
    return (
        f"# git-digest — {repo.name or str(repo)}\n\n"
        f"clean working tree on `{branch.current}`, up to date with `{upstream}`.\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())

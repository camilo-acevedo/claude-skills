"""run-quiet entrypoint.

Wrap a verbose command. Stream its output to a log file, and return a short
digest (exit code, matched error lines, tail) on stdout. The full output
stays on disk so Claude can read it on demand.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_MAX_LINES = 30
DEFAULT_TAIL = 10
DEFAULT_HEAD = 0
LOG_DIR = ".claude/run-logs"

# Generic patterns: matched anywhere in a line.
GENERIC_ERROR_PATTERNS = re.compile(
    r"(?ix)"
    r"\b(?:error|errno|exception|traceback|failed|failure|panic|fatal)\b"
    r"|\bWARN(?:ING)?\b"
    r"|^\s*at\s+\S+\(\S+:\d+:\d+\)"  # JS stack frame
)

# Framework-specific signals: each entry contributes a high-confidence match.
FRAMEWORK_PATTERNS = re.compile(
    r"(?x)"
    r"^FAILED\s|^ERROR\s"                  # pytest
    r"|^FAIL\s"                             # jest, mocha
    r"|^---\s+FAIL:"                        # go test
    r"|^\s*●\s"                              # jest assertion bullet
    r"|^E\s{2}"                              # pytest error indent
)

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def main(argv: Optional[List[str]] = None) -> int:
    args, command = _parse_args(argv)
    if not command:
        print("run-quiet: error: no command provided after `--`", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"run-quiet: error: --root does not exist: {root}", file=sys.stderr)
        return 2

    log_dir = root / LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    cmd_display = _display_command(command, args.shell)
    log_path = log_dir / _log_filename(cmd_display)

    started = time.perf_counter()
    exit_code, line_count = _run(command, args.shell, root, log_path, args.timeout)
    elapsed = time.perf_counter() - started

    if not args.quiet:
        print(f"$ {cmd_display}")

    rel_log = _safe_relative(log_path, root)

    if args.no_trim:
        try:
            print(log_path.read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            print(f"run-quiet: warning: could not re-read log: {exc}", file=sys.stderr)
        print(f"\nexit: {exit_code} (in {elapsed:.2f}s)  •  log: {rel_log} ({line_count} lines)")
        return exit_code

    head_lines = _read_head(log_path, args.head)
    tail_lines = _read_tail(log_path, args.tail)
    error_lines = _scan_errors(log_path, max_lines=args.max_lines, exclude_lines=set(head_lines + tail_lines))

    is_clean = exit_code == 0 and not error_lines
    if is_clean and not head_lines:
        last = tail_lines[-1].strip() if tail_lines else ""
        last_part = f' — last line: "{last}"' if last else ""
        print(f"exit: {exit_code} (in {elapsed:.2f}s)  •  log: {rel_log} ({line_count} lines)")
        print(f"clean{last_part}")
        return exit_code

    print(f"exit: {exit_code} (in {elapsed:.2f}s)")
    print(f"log:  {rel_log} ({line_count} lines)")

    if head_lines:
        print(f"\nhead ({len(head_lines)}):")
        for line in head_lines:
            print(f"  {line}")

    if error_lines:
        capped = error_lines[: args.max_lines]
        print(f"\nerrors ({len(error_lines)}{', truncated' if len(error_lines) > args.max_lines else ''}):")
        for line in capped:
            print(f"  {line}")
        if len(error_lines) > args.max_lines:
            print(f"  … (+{len(error_lines) - args.max_lines} more — see log)")

    if tail_lines:
        print(f"\ntail ({len(tail_lines)}):")
        for line in tail_lines:
            print(f"  {line}")

    return exit_code


def _parse_args(argv: Optional[List[str]]) -> Tuple[argparse.Namespace, List[str]]:
    raw = list(sys.argv[1:] if argv is None else argv)
    if "--" in raw:
        idx = raw.index("--")
        own, command = raw[:idx], raw[idx + 1 :]
    else:
        own, command = raw, []

    parser = argparse.ArgumentParser(
        prog="run-quiet",
        description="Run a command, save full output to a log, return a short digest.",
    )
    parser.add_argument("--root", default=".", help="Working directory + log location.")
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("--tail", type=int, default=DEFAULT_TAIL)
    parser.add_argument("--head", type=int, default=DEFAULT_HEAD)
    parser.add_argument("--shell", action="store_true", help="Run via the system shell.")
    parser.add_argument("--no-trim", action="store_true", help="Print the full output.")
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--quiet", action="store_true", help="Suppress the leading '$ <cmd>' line.")

    args = parser.parse_args(own)
    return args, command


def _display_command(command: List[str], shell: bool) -> str:
    if shell:
        return " ".join(command)
    try:
        return shlex.join(command)
    except AttributeError:  # Python < 3.8
        return " ".join(shlex.quote(c) for c in command)


def _log_filename(cmd_display: str) -> str:
    digest = hashlib.sha256(cmd_display.encode("utf-8")).hexdigest()[:12]
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{digest}.log"


def _run(
    command: List[str],
    shell: bool,
    cwd: Path,
    log_path: Path,
    timeout: Optional[float],
) -> Tuple[int, int]:
    """Run the command, stream stdout+stderr to the log file, return (exit, line_count)."""
    line_count = 0
    if shell:
        spawn = subprocess.Popen(
            " ".join(command),
            cwd=str(cwd),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    else:
        spawn = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    deadline = time.monotonic() + timeout if timeout else None

    try:
        with log_path.open("w", encoding="utf-8") as log:
            assert spawn.stdout is not None
            for line in spawn.stdout:
                log.write(line)
                line_count += 1
                if deadline and time.monotonic() > deadline:
                    spawn.kill()
                    log.write(f"\nrun-quiet: killed after {timeout}s timeout\n")
                    break
        spawn.wait()
    except KeyboardInterrupt:
        spawn.kill()
        spawn.wait()
        raise

    return spawn.returncode, line_count


def _read_head(log_path: Path, n: int) -> List[str]:
    if n <= 0:
        return []
    out: List[str] = []
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for _ in range(n):
                line = f.readline()
                if not line:
                    break
                out.append(_strip(line))
    except OSError:
        return []
    return out


def _read_tail(log_path: Path, n: int) -> List[str]:
    if n <= 0:
        return []
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            buf = f.readlines()
    except OSError:
        return []
    return [_strip(line) for line in buf[-n:]]


def _scan_errors(log_path: Path, max_lines: int, exclude_lines: set) -> List[str]:
    out: List[str] = []
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = _strip(raw)
                if not line:
                    continue
                if line in exclude_lines:
                    continue
                if FRAMEWORK_PATTERNS.search(line) or GENERIC_ERROR_PATTERNS.search(line):
                    out.append(line)
                    if len(out) >= max_lines * 4:  # collect a bit beyond the cap so we can report total
                        # avoid runaway scans on multi-MB logs
                        break
    except OSError:
        return []
    return out


def _strip(line: str) -> str:
    return ANSI_ESCAPE.sub("", line.rstrip("\n").rstrip("\r"))


def _safe_relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())

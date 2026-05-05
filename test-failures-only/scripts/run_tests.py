"""test-failures-only entrypoint.

Run a test suite, save full output to a log, and return only the failing
tests (with a short traceback snippet) plus a single-line summary. If
everything passes, return one line.

Supported frameworks (auto-detected from the command):
- pytest (Python)
- jest, vitest (JS/TS)
- go test
- generic fallback (filters lines containing FAIL / ERROR)
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

LOG_DIR = ".claude/test-logs"
DEFAULT_MAX_FAILURES = 20
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


@dataclass
class Failure:
    name: str
    detail: str = ""


@dataclass
class TestResult:
    framework: str
    failures: List[Failure] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    duration: Optional[str] = None
    parsed: bool = False


def main(argv: Optional[List[str]] = None) -> int:
    # On Windows the default console codec is cp1252, which cannot encode the
    # Unicode markers we print (✗, ✓). Switch to UTF-8 with replacement so the
    # output is readable regardless of the console.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass

    args, command = _parse_args(argv)
    if not command:
        print("test-failures-only: error: no command provided after `--`", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"test-failures-only: error: --root does not exist: {root}", file=sys.stderr)
        return 2

    framework = args.framework or _detect_framework(command)
    command = _maybe_inject_flags(command, framework, args.shell)

    log_dir = root / LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{time.strftime('%Y%m%d-%H%M%S')}-{framework}.log"

    cmd_display = " ".join(command) if args.shell else _shlex_join(command)
    if not args.quiet:
        print(f"$ {cmd_display}")

    started = time.perf_counter()
    exit_code = _run(command, args.shell, root, log_path)
    elapsed = time.perf_counter() - started

    rel_log = _safe_relative(log_path, root)
    output = _read_log(log_path)
    result = _parse(output, framework)
    if result.duration is None:
        result.duration = f"{elapsed:.2f}s"

    if exit_code == 0 and result.failed == 0:
        if result.parsed and result.passed:
            print(f"OK — {result.passed} passed in {result.duration}  •  log: {rel_log}")
        else:
            print(f"OK — exit 0 in {result.duration}  •  log: {rel_log}")
        return 0

    summary = _summary_line(result, exit_code)
    print(summary)
    print(f"log: {rel_log}")

    if not result.parsed or not result.failures:
        # Fallback: show last 20 lines of output so the caller can see what crashed.
        tail = output.splitlines()[-20:]
        print("\n(no failures parsed — tail of log:)")
        for line in tail:
            print(f"  {line}")
        return exit_code

    capped = result.failures[: args.max_failures]
    print()
    for fail in capped:
        print(f"✗ {fail.name}")
        if not args.no_trace and fail.detail:
            for detail_line in fail.detail.splitlines():
                print(f"    {detail_line}")
        print()
    if len(result.failures) > args.max_failures:
        print(f"… (+{len(result.failures) - args.max_failures} more failures — see log)")

    return exit_code


def _parse_args(argv: Optional[List[str]]) -> Tuple[argparse.Namespace, List[str]]:
    raw = list(sys.argv[1:] if argv is None else argv)
    if "--" in raw:
        idx = raw.index("--")
        own, command = raw[:idx], raw[idx + 1 :]
    else:
        own, command = raw, []

    parser = argparse.ArgumentParser(
        prog="test-failures-only",
        description="Run a test suite and return only failures with condensed tracebacks.",
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--framework", choices=["pytest", "jest", "vitest", "go", "generic"], default=None)
    parser.add_argument("--max-failures", type=int, default=DEFAULT_MAX_FAILURES)
    parser.add_argument("--no-trace", action="store_true")
    parser.add_argument("--shell", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(own), command


def _detect_framework(command: List[str]) -> str:
    joined = " ".join(command).lower()
    if "pytest" in joined:
        return "pytest"
    if "vitest" in joined:
        return "vitest"
    if "jest" in joined:
        return "jest"
    if re.search(r"\bgo\s+test\b", joined):
        return "go"
    return "generic"


def _maybe_inject_flags(command: List[str], framework: str, shell: bool) -> List[str]:
    if shell:
        return command
    if framework == "pytest":
        if not any(arg.startswith("--tb") for arg in command):
            return command + ["--tb=line"]
    if framework == "go":
        if "-json" not in command and not any(arg.startswith("-json") for arg in command):
            return command + ["-json"]
    return command


def _run(command: List[str], shell: bool, cwd: Path, log_path: Path) -> int:
    try:
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
    except FileNotFoundError as exc:
        log_path.write_text(f"command not found: {exc}\n", encoding="utf-8")
        return 127

    with log_path.open("w", encoding="utf-8") as log:
        assert spawn.stdout is not None
        for line in spawn.stdout:
            log.write(line)
    spawn.wait()
    return spawn.returncode


def _read_log(log_path: Path) -> str:
    try:
        raw = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return ANSI_ESCAPE.sub("", raw)


# ---------- parsers ----------


def _parse(output: str, framework: str) -> TestResult:
    if framework == "pytest":
        return _parse_pytest(output)
    if framework == "jest":
        return _parse_jest(output)
    if framework == "vitest":
        return _parse_vitest(output)
    if framework == "go":
        return _parse_go(output)
    return _parse_generic(output)


_PYTEST_FAILED_LINE = re.compile(r"^FAILED\s+(?P<name>\S+)(?:\s*-\s*(?P<reason>.+))?$", re.MULTILINE)
_PYTEST_ERROR_LINE = re.compile(r"^ERROR\s+(?P<name>\S+)(?:\s*-\s*(?P<reason>.+))?$", re.MULTILINE)
_PYTEST_SUMMARY = re.compile(
    r"=+\s*(?:(?P<failed>\d+)\s+failed,?\s*)?(?:(?P<passed>\d+)\s+passed,?\s*)?(?:(?P<skipped>\d+)\s+skipped,?\s*)?"
    r"(?:[\w\s,]*)?\s+in\s+(?P<duration>[\d.]+s)\s*=+",
    re.IGNORECASE,
)


def _parse_pytest(output: str) -> TestResult:
    result = TestResult(framework="pytest")
    for match in _PYTEST_FAILED_LINE.finditer(output):
        name = match.group("name")
        reason = (match.group("reason") or "").strip()
        result.failures.append(Failure(name=name, detail=reason))
    for match in _PYTEST_ERROR_LINE.finditer(output):
        name = match.group("name")
        reason = (match.group("reason") or "").strip()
        result.failures.append(Failure(name=f"{name} (collection error)", detail=reason))

    summary = _PYTEST_SUMMARY.search(output)
    if summary:
        if summary.group("failed"):
            result.failed = int(summary.group("failed"))
        if summary.group("passed"):
            result.passed = int(summary.group("passed"))
        if summary.group("skipped"):
            result.skipped = int(summary.group("skipped"))
        result.duration = summary.group("duration")
        result.parsed = True

    if not result.failed and result.failures:
        result.failed = len(result.failures)
        result.parsed = True

    return result


_JEST_BULLET = re.compile(r"^\s*●\s+(?P<name>.+?)$", re.MULTILINE)
_JEST_TESTS_LINE = re.compile(
    r"^Tests:\s+(?:(?P<failed>\d+)\s+failed,?\s*)?(?:(?P<passed>\d+)\s+passed,?\s*)?(?:(?P<skipped>\d+)\s+skipped,?\s*)?(?:(?P<total>\d+)\s+total)?",
    re.MULTILINE,
)
_JEST_TIME_LINE = re.compile(r"^Time:\s+(?P<duration>\S+)", re.MULTILINE)


def _parse_jest(output: str) -> TestResult:
    result = TestResult(framework="jest")
    if output.lstrip().startswith("{") and '"testResults"' in output[:5000]:
        return _parse_jest_json(output, result)

    bullets = list(_JEST_BULLET.finditer(output))
    for i, m in enumerate(bullets):
        name = m.group("name").strip()
        start = m.end()
        end = bullets[i + 1].start() if i + 1 < len(bullets) else len(output)
        snippet = output[start:end].strip().splitlines()
        # Take the first non-empty meaningful line as detail.
        detail_lines: List[str] = []
        for line in snippet[:6]:
            if line.strip():
                detail_lines.append(line.strip())
        result.failures.append(Failure(name=name, detail="\n".join(detail_lines)))

    summary = _JEST_TESTS_LINE.search(output)
    if summary:
        if summary.group("failed"):
            result.failed = int(summary.group("failed"))
        if summary.group("passed"):
            result.passed = int(summary.group("passed"))
        if summary.group("skipped"):
            result.skipped = int(summary.group("skipped"))
        result.parsed = True
    time_match = _JEST_TIME_LINE.search(output)
    if time_match:
        result.duration = time_match.group("duration")

    if not result.failed and result.failures:
        result.failed = len(result.failures)
        result.parsed = True

    return result


def _parse_jest_json(output: str, result: TestResult) -> TestResult:
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return result
    result.passed = data.get("numPassedTests", 0)
    result.failed = data.get("numFailedTests", 0)
    result.skipped = data.get("numPendingTests", 0)
    for tr in data.get("testResults", []):
        for assertion in tr.get("assertionResults", []):
            if assertion.get("status") == "failed":
                ancestors = " > ".join(assertion.get("ancestorTitles", []))
                title = assertion.get("title", "?")
                full = f"{tr.get('name', '?')} :: {ancestors} > {title}" if ancestors else f"{tr.get('name', '?')} :: {title}"
                detail = "\n".join(assertion.get("failureMessages", [])[:1]).strip().splitlines()[:5]
                result.failures.append(Failure(name=full, detail="\n".join(detail)))
    result.parsed = True
    return result


_VITEST_FAIL = re.compile(r"^❯?\s*(?:FAIL|×)\s+(?P<name>.+?)$", re.MULTILINE)
_VITEST_TESTS_LINE = re.compile(
    r"^\s*Test Files\s+(?:(?P<files_failed>\d+)\s+failed)?.*$|"
    r"^\s*Tests\s+(?:(?P<failed>\d+)\s+failed[\s,]*)?(?:(?P<passed>\d+)\s+passed)?",
    re.MULTILINE,
)
_VITEST_DURATION = re.compile(r"^\s*Duration\s+(?P<duration>\S+)", re.MULTILINE)


def _parse_vitest(output: str) -> TestResult:
    result = TestResult(framework="vitest")
    for m in _VITEST_FAIL.finditer(output):
        name = m.group("name").strip()
        result.failures.append(Failure(name=name))
    for m in _VITEST_TESTS_LINE.finditer(output):
        if m.group("failed"):
            result.failed = int(m.group("failed"))
        if m.group("passed"):
            result.passed = int(m.group("passed"))
        result.parsed = True
    duration = _VITEST_DURATION.search(output)
    if duration:
        result.duration = duration.group("duration")
    if not result.failed and result.failures:
        result.failed = len(result.failures)
        result.parsed = True
    return result


def _parse_go(output: str) -> TestResult:
    result = TestResult(framework="go")
    failed_tests: dict = {}
    pass_count = 0
    fail_count = 0
    last_action: Optional[str] = None

    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        action = event.get("Action")
        test = event.get("Test")
        pkg = event.get("Package", "")
        if action == "fail" and test:
            key = f"{pkg}::{test}"
            failed_tests.setdefault(key, [])
            fail_count += 1
            last_action = "fail"
        elif action == "pass" and test:
            pass_count += 1
        elif action == "output" and test:
            output_text = event.get("Output", "")
            key = f"{pkg}::{test}"
            if key in failed_tests:
                line_clean = output_text.rstrip()
                if line_clean and "--- FAIL" not in line_clean and "PASS" not in line_clean:
                    failed_tests[key].append(line_clean)

    for name, lines in failed_tests.items():
        detail = "\n".join(lines[-5:]).strip()
        result.failures.append(Failure(name=name, detail=detail))

    result.passed = pass_count
    result.failed = fail_count
    result.parsed = bool(failed_tests) or last_action is not None
    if not result.failed and result.failures:
        result.failed = len(result.failures)
    return result


_GENERIC_FAIL = re.compile(r"^\s*(?:FAIL(?:ED)?|ERROR|×|✗)\s*[:\s].*", re.MULTILINE)


def _parse_generic(output: str) -> TestResult:
    result = TestResult(framework="generic")
    for m in _GENERIC_FAIL.finditer(output):
        line = m.group(0).strip()
        result.failures.append(Failure(name=line))
    if result.failures:
        result.failed = len(result.failures)
        result.parsed = True
    return result


# ---------- helpers ----------


def _summary_line(result: TestResult, exit_code: int) -> str:
    bits = []
    if result.failed:
        bits.append(f"{result.failed} failed")
    if result.passed:
        bits.append(f"{result.passed} passed")
    if result.skipped:
        bits.append(f"{result.skipped} skipped")
    summary = ", ".join(bits) or "no parseable test results"
    duration = result.duration or "unknown duration"
    label = "FAIL" if exit_code != 0 or result.failed else "OK"
    return f"{label} — {summary} in {duration}"


def _shlex_join(command: List[str]) -> str:
    try:
        return shlex.join(command)
    except AttributeError:
        return " ".join(shlex.quote(c) for c in command)


def _safe_relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())

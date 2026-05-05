"""Smoke test: run the generator on each fixture and assert the basics.

Run from the codemap/ directory:

    python tests/smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from scripts.generate import main as generate_main  # noqa: E402

FIXTURES = HERE / "fixtures"


def run_fixture(name: str) -> str:
    fixture = FIXTURES / name
    output = fixture / "CODEMAP.md"
    if output.exists():
        output.unlink()
    cache = fixture / ".claude" / "codemap-cache.json"
    if cache.exists():
        cache.unlink()
    rc = generate_main(["--root", str(fixture), "--quiet"])
    assert rc == 0, f"generate exited {rc} for {name}"
    assert output.exists(), f"CODEMAP.md not produced for {name}"
    return output.read_text(encoding="utf-8")


def assert_contains(haystack: str, needle: str, label: str) -> None:
    if needle not in haystack:
        snippet = haystack[:600].encode("ascii", "replace").decode("ascii")
        raise AssertionError(f"[{label}] expected to find {needle!r}\n--- map start ---\n{snippet}\n...")


def test_tiny_python() -> None:
    text = run_fixture("tiny-python")
    assert_contains(text, "app/main.py", "tiny-python:tree")
    assert_contains(text, "Tiny FastAPI-style app entrypoint", "tiny-python:purpose")
    assert_contains(text, "def start(host: str", "tiny-python:start")
    assert_contains(text, "async def shutdown()", "tiny-python:shutdown")
    assert_contains(text, "class Server", "tiny-python:class")
    assert_contains(text, "API_VERSION", "tiny-python:const")
    assert_contains(text, "DEFAULT_PORT: int", "tiny-python:annconst")
    assert "_internal_helper" not in text, "tiny-python: leaked private helper"
    assert "_PrivateHelper" not in text, "tiny-python: leaked private class"


def test_mixed_stack() -> None:
    text = run_fixture("mixed-stack")
    # Python
    assert_contains(text, "app/__init__.py", "mixed:py-tree")
    assert_contains(text, "Mixed-stack fixture", "mixed:py-purpose")
    assert_contains(text, "def hello(name: str)", "mixed:py-fn")
    # TypeScript
    assert_contains(text, "src/auth.ts", "mixed:ts-tree")
    assert_contains(text, "JWT validation and middleware", "mixed:ts-purpose")
    assert_contains(text, "function verifyJwt", "mixed:ts-fn")
    assert_contains(text, "class AuthMiddleware", "mixed:ts-class")
    assert_contains(text, "interface Claims", "mixed:ts-iface")
    assert_contains(text, "JWT_ALGO", "mixed:ts-const")
    # Go
    assert_contains(text, "cmd/server.go", "mixed:go-tree")
    assert_contains(text, "starts the HTTP listener", "mixed:go-purpose")
    assert_contains(text, "func Start(cfg Config)", "mixed:go-fn")
    assert_contains(text, "type Config struct", "mixed:go-type")
    assert_contains(text, "DefaultPort", "mixed:go-const")


def test_cache_reuse() -> None:
    fixture = FIXTURES / "tiny-python"
    output = fixture / "CODEMAP.md"
    cache = fixture / ".claude" / "codemap-cache.json"
    if output.exists():
        output.unlink()
    if cache.exists():
        cache.unlink()
    # First run populates the cache.
    assert generate_main(["--root", str(fixture), "--quiet"]) == 0
    assert cache.exists(), "cache not written"
    mtime_first = cache.stat().st_mtime
    # Second run should be a no-op for parsing — cache file may be rewritten but contents identical.
    assert generate_main(["--root", str(fixture), "--quiet"]) == 0
    assert cache.exists(), "cache disappeared on second run"
    assert cache.stat().st_mtime >= mtime_first


def main() -> int:
    failed = 0
    for fn in (test_tiny_python, test_mixed_stack, test_cache_reuse):
        name = fn.__name__
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {name}: {exc}")
        except Exception as exc:
            failed += 1
            print(f"ERROR {name}: {type(exc).__name__}: {exc}")
    if failed:
        print(f"\n{failed} test(s) failed")
        return 1
    print("\nAll smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

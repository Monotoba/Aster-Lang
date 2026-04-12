"""Test runner for Aster test files.

Discovers ``test_*.aster`` files under a given path, then runs every
top-level ``fn test_*()`` function in each file.  Functions that return
normally pass; functions that raise ``InterpreterError`` fail.

Usage (CLI)::

    aster test [path]

The default search root is the ``tests/`` subdirectory of the given path
(if it exists), falling back to the path itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from aster_lang.interpreter import FunctionValue, Interpreter, InterpreterError
from aster_lang.module_resolution import ModuleResolutionError
from aster_lang.parser import ParseError, parse_module
from aster_lang.semantic import SemanticAnalyzer


@dataclass
class CaseResult:
    """Result of running a single test function."""

    name: str
    passed: bool
    error: str | None = None


# Public alias kept for tests that import it directly.
TestCaseResult = CaseResult


@dataclass
class FileResult:
    """Results for all test functions in one file."""

    path: Path
    results: list[CaseResult] = field(default_factory=list)
    parse_error: str | None = None

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)


# Public alias kept for tests that import it directly.
TestFileResult = FileResult


@dataclass
class SuiteResult:
    """Aggregated results across all discovered test files."""

    file_results: list[FileResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(f.passed for f in self.file_results)

    @property
    def failed(self) -> int:
        return sum(f.failed for f in self.file_results)

    @property
    def total(self) -> int:
        return sum(f.total for f in self.file_results)

    @property
    def ok(self) -> bool:
        return self.failed == 0 and any(f.total > 0 for f in self.file_results)


# Public alias kept for tests that import it directly.
TestSuiteResult = SuiteResult


def discover_test_files(search_path: Path) -> list[Path]:
    """Return sorted list of ``test_*.aster`` files under *search_path*.

    If *search_path* is a file, return it directly (regardless of name).
    If it is a directory, search recursively for ``test_*.aster`` files,
    preferring ``tests/`` if it exists.
    """
    if search_path.is_file():
        return [search_path]

    root = search_path
    tests_dir = search_path / "tests"
    if tests_dir.is_dir():
        root = tests_dir

    return sorted(root.rglob("test_*.aster"))


def _test_function_names(interpreter: Interpreter) -> list[str]:
    """Return names of all top-level no-arg ``test_*`` functions."""
    names = []
    for name, value in interpreter.current_env.bindings.items():
        if name.startswith("test_") and isinstance(value, FunctionValue) and len(value.params) == 0:
            names.append(name)
    return sorted(names)


def run_test_file(
    path: Path,
    *,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
) -> FileResult:
    """Parse, analyse, and run all ``test_*`` functions in *path*."""
    result = FileResult(path=path)

    source = path.read_text(encoding="utf-8")

    # Parse
    try:
        module = parse_module(source)
    except ParseError as exc:
        result.parse_error = str(exc)
        return result

    # Semantic analysis (soft — warnings don't abort)
    analyzer = SemanticAnalyzer(
        base_dir=path.parent,
        dep_overrides=dep_overrides,
        extra_roots=extra_roots,
        allow_external_imports=True,
    )
    ok = analyzer.analyze(module)
    if not ok:
        result.parse_error = "; ".join(str(e) for e in analyzer.errors)
        return result

    # Load module (register all declarations, do NOT auto-call main)
    interpreter = Interpreter(
        base_dir=path.parent,
        dep_overrides=dep_overrides,
        extra_roots=extra_roots,
    )
    try:
        interpreter.interpret(module, auto_call_main=False)
    except (InterpreterError, ModuleResolutionError) as exc:
        result.parse_error = f"Module load error: {exc}"
        return result

    # Run each test function
    for name in _test_function_names(interpreter):
        try:
            interpreter.call_named_function(name)
            result.results.append(CaseResult(name=name, passed=True))
        except InterpreterError as exc:
            result.results.append(CaseResult(name=name, passed=False, error=str(exc)))

    return result


def run_tests(
    search_path: Path,
    *,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
) -> SuiteResult:
    """Discover and run all test files under *search_path*."""
    suite = SuiteResult()
    for test_file in discover_test_files(search_path):
        file_result = run_test_file(
            test_file,
            dep_overrides=dep_overrides,
            extra_roots=extra_roots,
        )
        suite.file_results.append(file_result)
    return suite


def format_suite_result(suite: SuiteResult) -> str:
    """Format a TestSuiteResult as human-readable text."""
    lines: list[str] = []

    if not suite.file_results:
        return "No test files found."

    for file_result in suite.file_results:
        rel = file_result.path
        if file_result.parse_error:
            lines.append(f"ERROR  {rel}")
            lines.append(f"       {file_result.parse_error}")
            continue
        if file_result.total == 0:
            lines.append(f"  (no tests)  {rel}")
            continue
        for r in file_result.results:
            status = "ok   " if r.passed else "FAIL "
            lines.append(f"  {status} {r.name}")
            if r.error:
                lines.append(f"         {r.error}")

    lines.append("")
    lines.append(
        f"test result: {'ok' if suite.failed == 0 else 'FAILED'}. "
        f"{suite.passed} passed; {suite.failed} failed; "
        f"{len(suite.file_results)} file(s)"
    )
    return "\n".join(lines)

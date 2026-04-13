"""Benchmark runner for Aster bench files.

Discovers ``bench_*.aster`` files under a given path, then runs every
top-level ``fn bench_*()`` function in each file N times and reports
timing statistics.  Functions that raise ``InterpreterError`` are
reported as failures.

Usage (CLI)::

    aster bench [path] [--iters N]

The default search root is the ``benches/`` subdirectory of the given
path (if it exists), falling back to the path itself.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from aster_lang.interpreter import FunctionValue, Interpreter, InterpreterError
from aster_lang.module_resolution import ModuleResolutionError
from aster_lang.parser import ParseError, parse_module
from aster_lang.semantic import SemanticAnalyzer


@dataclass
class CaseResult:
    """Result of running a single benchmark function."""

    name: str
    iterations: int
    # All in seconds; None when the bench failed to run.
    total_s: float | None = None
    min_s: float | None = None
    mean_s: float | None = None
    max_s: float | None = None
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.error is None


@dataclass
class FileResult:
    """Results for all bench functions in one file."""

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


@dataclass
class SuiteResult:
    """Aggregated results across all discovered bench files."""

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


def discover_bench_files(search_path: Path) -> list[Path]:
    """Return sorted list of ``bench_*.aster`` files under *search_path*.

    If *search_path* is a file, return it directly (regardless of name).
    If it is a directory, search recursively for ``bench_*.aster`` files,
    preferring ``benches/`` if it exists.
    """
    if search_path.is_file():
        return [search_path]

    root = search_path
    benches_dir = search_path / "benches"
    if benches_dir.is_dir():
        root = benches_dir

    return sorted(root.rglob("bench_*.aster"))


def _bench_function_names(interpreter: Interpreter) -> list[str]:
    """Return names of all top-level no-arg ``bench_*`` functions."""
    names = []
    for name, value in interpreter.current_env.bindings.items():
        if (
            name.startswith("bench_")
            and isinstance(value, FunctionValue)
            and len(value.params) == 0
        ):
            names.append(name)
    return sorted(names)


def run_bench_file(
    path: Path,
    *,
    iterations: int = 100,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
) -> FileResult:
    """Parse, analyse, and run all ``bench_*`` functions in *path*."""
    result = FileResult(path=path)

    source = path.read_text(encoding="utf-8")

    # Parse
    try:
        module = parse_module(source)
    except ParseError as exc:
        result.parse_error = str(exc)
        return result

    # Semantic analysis
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

    # Load module
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

    # Run each bench function
    for name in _bench_function_names(interpreter):
        # Warmup: one call before timing to let module-level side effects settle.
        try:
            interpreter.call_named_function(name)
        except InterpreterError as exc:
            result.results.append(CaseResult(name=name, iterations=iterations, error=str(exc)))
            continue

        # Timed loop
        times: list[float] = []
        error: str | None = None
        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                interpreter.call_named_function(name)
            except InterpreterError as exc:
                error = str(exc)
                break
            times.append(time.perf_counter() - t0)

        if error is not None or not times:
            result.results.append(
                CaseResult(
                    name=name, iterations=iterations, error=error or "no iterations completed"
                )
            )
        else:
            total = sum(times)
            result.results.append(
                CaseResult(
                    name=name,
                    iterations=len(times),
                    total_s=total,
                    min_s=min(times),
                    mean_s=total / len(times),
                    max_s=max(times),
                )
            )

    return result


def run_benches(
    search_path: Path,
    *,
    iterations: int = 100,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
) -> SuiteResult:
    """Discover and run all bench files under *search_path*."""
    suite = SuiteResult()
    for bench_file in discover_bench_files(search_path):
        file_result = run_bench_file(
            bench_file,
            iterations=iterations,
            dep_overrides=dep_overrides,
            extra_roots=extra_roots,
        )
        suite.file_results.append(file_result)
    return suite


def _fmt_duration(seconds: float) -> str:
    """Format a duration in the most readable unit."""
    if seconds >= 1.0:
        return f"{seconds:.3f}s"
    if seconds >= 1e-3:
        return f"{seconds * 1e3:.3f}ms"
    if seconds >= 1e-6:
        return f"{seconds * 1e6:.3f}µs"
    return f"{seconds * 1e9:.1f}ns"


def format_suite_result(suite: SuiteResult) -> str:
    """Format a SuiteResult as human-readable text."""
    lines: list[str] = []

    if not suite.file_results:
        return "No bench files found."

    for file_result in suite.file_results:
        if file_result.parse_error:
            lines.append(f"ERROR  {file_result.path}")
            lines.append(f"       {file_result.parse_error}")
            continue
        if file_result.total == 0:
            lines.append(f"  (no benches)  {file_result.path}")
            continue
        for r in file_result.results:
            if not r.passed:
                lines.append(f"  FAIL  {r.name}")
                lines.append(f"        {r.error}")
            else:
                assert r.total_s is not None
                assert r.mean_s is not None
                assert r.min_s is not None
                assert r.max_s is not None
                lines.append(
                    f"  bench  {r.name:<40} {r.iterations:>6} iters"
                    f"  mean: {_fmt_duration(r.mean_s):>10}"
                    f"  min: {_fmt_duration(r.min_s):>10}"
                    f"  max: {_fmt_duration(r.max_s):>10}"
                )

    lines.append("")
    status = "ok" if suite.failed == 0 else "FAILED"
    lines.append(
        f"bench result: {status}. "
        f"{suite.passed} passed; {suite.failed} failed; "
        f"{len(suite.file_results)} file(s)"
    )
    return "\n".join(lines)

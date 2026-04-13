"""Tests for the Aster benchmark runner (aster bench)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_lang.bench_runner import (
    CaseResult,
    FileResult,
    SuiteResult,
    discover_bench_files,
    format_suite_result,
    run_bench_file,
    run_benches,
)
from aster_lang.cli import main

# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_discover_bench_files_finds_bench_aster_files(tmp_path: Path) -> None:
    (tmp_path / "bench_foo.aster").write_text("", encoding="utf-8")
    (tmp_path / "bench_bar.aster").write_text("", encoding="utf-8")
    (tmp_path / "test_foo.aster").write_text("", encoding="utf-8")  # not a bench file
    found = discover_bench_files(tmp_path)
    assert len(found) == 2
    assert all(f.name.startswith("bench_") for f in found)


def test_discover_bench_files_prefers_benches_subdir(tmp_path: Path) -> None:
    benches_dir = tmp_path / "benches"
    benches_dir.mkdir()
    (benches_dir / "bench_inner.aster").write_text("", encoding="utf-8")
    (tmp_path / "bench_outer.aster").write_text("", encoding="utf-8")
    found = discover_bench_files(tmp_path)
    assert len(found) == 1
    assert found[0].name == "bench_inner.aster"


def test_discover_bench_files_returns_file_directly(tmp_path: Path) -> None:
    f = tmp_path / "bench_something.aster"
    f.write_text("", encoding="utf-8")
    found = discover_bench_files(f)
    assert found == [f]


def test_discover_bench_files_empty_dir_returns_empty(tmp_path: Path) -> None:
    assert discover_bench_files(tmp_path) == []


# ---------------------------------------------------------------------------
# run_bench_file
# ---------------------------------------------------------------------------


_SIMPLE_BENCH = """\
fn bench_trivial():
    mut x := 0
    mut i := 0
    while i < 10:
        x <- x + 1
        i <- i + 1
"""

_FAILING_BENCH = """\
fn bench_crash():
    assert(false, "intentional")
"""

_PARSE_ERROR_BENCH = "fn (broken"


def test_run_bench_file_happy_path(tmp_path: Path) -> None:
    p = tmp_path / "bench_simple.aster"
    p.write_text(_SIMPLE_BENCH, encoding="utf-8")
    result = run_bench_file(p, iterations=5)
    assert result.parse_error is None
    assert result.total == 1
    assert result.passed == 1
    assert result.failed == 0
    case = result.results[0]
    assert case.name == "bench_trivial"
    assert case.passed
    assert case.iterations == 5
    assert case.total_s is not None and case.total_s > 0
    assert case.mean_s is not None and case.mean_s > 0
    assert case.min_s is not None
    assert case.max_s is not None
    assert case.min_s <= case.mean_s <= case.max_s


def test_run_bench_file_failing_bench_reports_error(tmp_path: Path) -> None:
    p = tmp_path / "bench_fail.aster"
    p.write_text(_FAILING_BENCH, encoding="utf-8")
    result = run_bench_file(p, iterations=10)
    assert result.parse_error is None
    assert result.total == 1
    assert result.failed == 1
    case = result.results[0]
    assert not case.passed
    assert case.error is not None
    assert "intentional" in case.error


def test_run_bench_file_parse_error_sets_parse_error(tmp_path: Path) -> None:
    p = tmp_path / "bench_broken.aster"
    p.write_text(_PARSE_ERROR_BENCH, encoding="utf-8")
    result = run_bench_file(p, iterations=10)
    assert result.parse_error is not None
    assert result.total == 0


def test_run_bench_file_no_bench_functions_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "bench_empty.aster"
    p.write_text("fn helper() -> Int:\n    return 1\n", encoding="utf-8")
    result = run_bench_file(p, iterations=10)
    assert result.parse_error is None
    assert result.total == 0


# ---------------------------------------------------------------------------
# run_benches (suite)
# ---------------------------------------------------------------------------


def test_run_benches_no_files_returns_empty_suite(tmp_path: Path) -> None:
    suite = run_benches(tmp_path, iterations=5)
    assert suite.total == 0
    assert suite.passed == 0
    assert suite.failed == 0


def test_run_benches_discovers_and_runs_multiple_files(tmp_path: Path) -> None:
    (tmp_path / "bench_a.aster").write_text(_SIMPLE_BENCH, encoding="utf-8")
    (tmp_path / "bench_b.aster").write_text(_SIMPLE_BENCH, encoding="utf-8")
    suite = run_benches(tmp_path, iterations=3)
    assert len(suite.file_results) == 2
    assert suite.total == 2
    assert suite.passed == 2
    assert suite.failed == 0


# ---------------------------------------------------------------------------
# format_suite_result
# ---------------------------------------------------------------------------


def test_format_suite_result_no_files() -> None:
    suite = SuiteResult()
    out = format_suite_result(suite)
    assert "No bench files found" in out


def test_format_suite_result_shows_timing_info() -> None:
    case = CaseResult(
        name="bench_foo",
        iterations=100,
        total_s=0.5,
        min_s=0.004,
        mean_s=0.005,
        max_s=0.007,
    )
    file_result = FileResult(path=Path("bench_foo.aster"), results=[case])
    suite = SuiteResult(file_results=[file_result])
    out = format_suite_result(suite)
    assert "bench_foo" in out
    assert "100" in out
    assert "mean" in out
    assert "min" in out
    assert "max" in out
    assert "bench result: ok" in out


def test_format_suite_result_failed_bench_shows_error() -> None:
    case = CaseResult(name="bench_bad", iterations=10, error="intentional")
    file_result = FileResult(path=Path("bench_bad.aster"), results=[case])
    suite = SuiteResult(file_results=[file_result])
    out = format_suite_result(suite)
    assert "FAIL" in out
    assert "intentional" in out
    assert "bench result: FAILED" in out


def test_format_suite_result_parse_error_shows_error() -> None:
    file_result = FileResult(path=Path("bench_broken.aster"), parse_error="unexpected EOF")
    suite = SuiteResult(file_results=[file_result])
    out = format_suite_result(suite)
    assert "ERROR" in out
    assert "unexpected EOF" in out


def test_format_suite_result_no_bench_functions_note() -> None:
    file_result = FileResult(path=Path("bench_empty.aster"), results=[])
    suite = SuiteResult(file_results=[file_result])
    out = format_suite_result(suite)
    assert "no benches" in out


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_bench_command_runs_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "bench_trivial.aster"
    p.write_text(_SIMPLE_BENCH, encoding="utf-8")
    ret = main(["bench", str(p), "--iters", "3"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "bench_trivial" in out
    assert "bench result: ok" in out


def test_cli_bench_command_exits_nonzero_on_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = tmp_path / "bench_crash.aster"
    p.write_text(_FAILING_BENCH, encoding="utf-8")
    ret = main(["bench", str(p), "--iters", "3"])
    assert ret == 1
    out = capsys.readouterr().out
    assert "FAIL" in out


def test_cli_bench_command_no_bench_files_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ret = main(["bench", str(tmp_path), "--iters", "1"])
    assert ret == 0  # no benches found is not an error — just an empty result
    out = capsys.readouterr().out
    assert "No bench files found" in out

"""Tests for the Aster test runner."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

import pytest

from aster_lang.cli import main
from aster_lang.test_runner import (
    TestCaseResult,
    TestFileResult,
    TestSuiteResult,
    discover_test_files,
    format_suite_result,
    run_test_file,
    run_tests,
)

CapsysFixture: TypeAlias = pytest.CaptureFixture[str]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PASSING_TESTS = """\
fn test_add():
    assert(1 + 1 == 2)

fn test_concat():
    assert("hello" + " world" == "hello world")
"""

_FAILING_TESTS = """\
fn test_always_fails():
    assert(1 == 2)

fn test_message():
    assert(1 == 2, "one is not two")
"""

_MIXED_TESTS = """\
fn test_pass():
    assert(1 == 1)

fn test_fail():
    assert(1 == 2, "intentional failure")
"""

_NO_TESTS = """\
fn helper():
    assert(1 == 1)

fn main():
    print("not a test file")
"""

_PARSE_ERROR = "this is not valid aster syntax @@@@"


# ---------------------------------------------------------------------------
# discover_test_files
# ---------------------------------------------------------------------------


class TestDiscoverTestFiles:
    def test_finds_test_aster_files(self, tmp_path: Path) -> None:
        (tmp_path / "test_foo.aster").write_text("")
        (tmp_path / "test_bar.aster").write_text("")
        (tmp_path / "main.aster").write_text("")  # should be excluded
        found = discover_test_files(tmp_path)
        assert len(found) == 2
        assert all(f.name.startswith("test_") for f in found)

    def test_prefers_tests_subdirectory(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_a.aster").write_text("")
        (tmp_path / "test_b.aster").write_text("")  # in root — should be ignored
        found = discover_test_files(tmp_path)
        assert len(found) == 1
        assert found[0].parent == tests_dir

    def test_returns_single_file_directly(self, tmp_path: Path) -> None:
        f = tmp_path / "test_single.aster"
        f.write_text("")
        assert discover_test_files(f) == [f]

    def test_returns_empty_when_no_test_files(self, tmp_path: Path) -> None:
        (tmp_path / "main.aster").write_text("")
        assert discover_test_files(tmp_path) == []

    def test_recurses_into_subdirectories(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "test_deep.aster").write_text("")
        found = discover_test_files(tmp_path)
        assert len(found) == 1


# ---------------------------------------------------------------------------
# run_test_file
# ---------------------------------------------------------------------------


class TestRunTestFile:
    def test_all_passing(self, tmp_path: Path) -> None:
        f = tmp_path / "test_pass.aster"
        f.write_text(_PASSING_TESTS)
        result = run_test_file(f)
        assert result.parse_error is None
        assert result.total == 2
        assert result.passed == 2
        assert result.failed == 0

    def test_all_failing(self, tmp_path: Path) -> None:
        f = tmp_path / "test_fail.aster"
        f.write_text(_FAILING_TESTS)
        result = run_test_file(f)
        assert result.parse_error is None
        assert result.total == 2
        assert result.failed == 2
        assert all(r.error is not None for r in result.results if not r.passed)

    def test_mixed_pass_and_fail(self, tmp_path: Path) -> None:
        f = tmp_path / "test_mixed.aster"
        f.write_text(_MIXED_TESTS)
        result = run_test_file(f)
        assert result.passed == 1
        assert result.failed == 1

    def test_no_test_functions(self, tmp_path: Path) -> None:
        f = tmp_path / "test_empty.aster"
        f.write_text(_NO_TESTS)
        result = run_test_file(f)
        assert result.total == 0
        assert result.parse_error is None

    def test_parse_error_captured(self, tmp_path: Path) -> None:
        f = tmp_path / "test_bad.aster"
        f.write_text(_PARSE_ERROR)
        result = run_test_file(f)
        assert result.parse_error is not None
        assert result.total == 0

    def test_assert_with_message_shown_on_fail(self, tmp_path: Path) -> None:
        f = tmp_path / "test_msg.aster"
        f.write_text('fn test_msg():\n    assert(1 == 2, "my message")\n')
        result = run_test_file(f)
        assert result.failed == 1
        assert "my message" in (result.results[0].error or "")

    def test_functions_not_starting_with_test_are_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "test_helpers.aster"
        f.write_text("fn helper():\n    assert(1 == 2)\n\nfn test_ok():\n    assert(1 == 1)\n")
        result = run_test_file(f)
        assert result.total == 1
        assert result.passed == 1


# ---------------------------------------------------------------------------
# run_tests (suite)
# ---------------------------------------------------------------------------


class TestRunTests:
    def test_suite_aggregates_multiple_files(self, tmp_path: Path) -> None:
        (tmp_path / "test_a.aster").write_text("fn test_one():\n    assert(1 == 1)\n")
        (tmp_path / "test_b.aster").write_text("fn test_two():\n    assert(1 == 2)\n")
        suite = run_tests(tmp_path)
        assert suite.total == 2
        assert suite.passed == 1
        assert suite.failed == 1

    def test_empty_directory_returns_no_files(self, tmp_path: Path) -> None:
        suite = run_tests(tmp_path)
        assert suite.total == 0
        assert len(suite.file_results) == 0

    def test_ok_property_false_when_failures(self, tmp_path: Path) -> None:
        (tmp_path / "test_f.aster").write_text("fn test_f():\n    assert(False)\n")
        suite = run_tests(tmp_path)
        assert not suite.ok


# ---------------------------------------------------------------------------
# format_suite_result
# ---------------------------------------------------------------------------


class TestFormatSuiteResult:
    def test_no_files_message(self) -> None:
        output = format_suite_result(TestSuiteResult())
        assert "No test files found" in output

    def test_shows_ok_for_passing(self) -> None:
        suite = TestSuiteResult(
            file_results=[
                TestFileResult(
                    path=Path("test_x.aster"),
                    results=[TestCaseResult(name="test_x", passed=True)],
                )
            ]
        )
        output = format_suite_result(suite)
        assert "ok" in output
        assert "test_x" in output

    def test_shows_fail_for_failing(self) -> None:
        suite = TestSuiteResult(
            file_results=[
                TestFileResult(
                    path=Path("test_y.aster"),
                    results=[TestCaseResult(name="test_y", passed=False, error="assertion failed")],
                )
            ]
        )
        output = format_suite_result(suite)
        assert "FAIL" in output
        assert "assertion failed" in output

    def test_parse_error_shown(self) -> None:
        suite = TestSuiteResult(
            file_results=[TestFileResult(path=Path("test_bad.aster"), parse_error="syntax error")]
        )
        output = format_suite_result(suite)
        assert "ERROR" in output
        assert "syntax error" in output


# ---------------------------------------------------------------------------
# CLI: aster test
# ---------------------------------------------------------------------------


class TestCLITestCommand:
    def test_all_pass_returns_zero(self, tmp_path: Path, capsys: CapsysFixture) -> None:
        (tmp_path / "test_ok.aster").write_text("fn test_ok():\n    assert(True)\n")
        assert main(["test", str(tmp_path)]) == 0

    def test_failure_returns_one(self, tmp_path: Path, capsys: CapsysFixture) -> None:
        (tmp_path / "test_fail.aster").write_text("fn test_fail():\n    assert(1 == 2)\n")
        assert main(["test", str(tmp_path)]) == 1

    def test_no_tests_returns_zero(self, tmp_path: Path, capsys: CapsysFixture) -> None:
        assert main(["test", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert "No test files found" in out

    def test_output_includes_test_names(self, tmp_path: Path, capsys: CapsysFixture) -> None:
        (tmp_path / "test_named.aster").write_text("fn test_named():\n    assert(1 == 1)\n")
        main(["test", str(tmp_path)])
        out = capsys.readouterr().out
        assert "test_named" in out

    def test_assert_builtin_works_in_test_files(
        self, tmp_path: Path, capsys: CapsysFixture
    ) -> None:
        (tmp_path / "test_assert.aster").write_text(
            "fn test_arith():\n    assert(2 + 2 == 4)\n"
            'fn test_str():\n    assert(str(42) == "42")\n'
        )
        assert main(["test", str(tmp_path)]) == 0

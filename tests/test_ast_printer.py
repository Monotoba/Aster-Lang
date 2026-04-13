"""Tests for the AST pretty-printer."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_lang.ast_printer import dump
from aster_lang.parser import parse_module


def _lines(source: str) -> list[str]:
    return dump(parse_module(source)).splitlines()


def _has(lines: list[str], *fragments: str) -> bool:
    return any(all(f in line for f in fragments) for line in lines)


def test_module_root_is_first_line() -> None:
    lines = _lines("fn f() -> Int:\n    return 0\n")
    assert lines[0] == "Module"


def test_function_decl_shows_name() -> None:
    lines = _lines("fn add(a: Int, b: Int) -> Int:\n    return a + b\n")
    assert _has(lines, "FunctionDecl", "'add'")


def test_pub_flag_shown_when_true() -> None:
    lines = _lines("pub fn f() -> Int:\n    return 0\n")
    assert _has(lines, "is_public")


def test_pub_flag_absent_when_false() -> None:
    lines = _lines("fn f() -> Int:\n    return 0\n")
    assert not _has(lines, "is_public")


def test_param_decl_shows_name_and_type() -> None:
    lines = _lines("fn f(x: Int) -> Int:\n    return x\n")
    assert _has(lines, "ParamDecl", "'x'")
    assert _has(lines, "SimpleType", "'Int'")


def test_let_stmt_mutable_flag() -> None:
    lines = _lines("fn f() -> Int:\n    mut n := 0\n    return n\n")
    assert _has(lines, "LetStmt", "is_mutable")


def test_let_stmt_immutable_no_flag() -> None:
    lines = _lines("fn f() -> Int:\n    n := 0\n    return n\n")
    assert _has(lines, "LetStmt")
    assert not _has(lines, "is_mutable")


def test_binary_expr_shows_operator() -> None:
    lines = _lines("fn f(a: Int, b: Int) -> Int:\n    return a + b\n")
    assert _has(lines, "BinaryExpr", "'+'")


def test_identifier_shows_name() -> None:
    lines = _lines("fn f(x: Int) -> Int:\n    return x\n")
    assert _has(lines, "Identifier", "'x'")


def test_integer_literal_shows_value() -> None:
    lines = _lines("fn f() -> Int:\n    return 42\n")
    assert _has(lines, "IntegerLiteral", "42")


def test_string_literal_shows_value() -> None:
    lines = _lines('fn main():\n    print("hello")\n')
    assert _has(lines, "StringLiteral", "'hello'")


def test_return_stmt_has_child() -> None:
    lines = _lines("fn f() -> Int:\n    return 1\n")
    ret_idx = next(i for i, line in enumerate(lines) if "ReturnStmt" in line)
    assert lines[ret_idx + 1].startswith("    ")  # indented child exists


def test_while_stmt_rendered() -> None:
    lines = _lines(
        "fn f() -> Int:\n    mut i := 0\n    while i < 10:\n        i <- i + 1\n    return i\n"
    )
    assert _has(lines, "WhileStmt")
    assert _has(lines, "BinaryExpr", "'<'")


def test_if_stmt_rendered() -> None:
    lines = _lines(
        "fn f(n: Int) -> Int:\n    if n > 0:\n        return n\n    else:\n        return 0\n"
    )
    assert _has(lines, "IfStmt")


def test_match_arm_and_literal_pattern() -> None:
    lines = _lines(
        "fn f(n: Int) -> Int:\n"
        "    match n:\n"
        "        0:\n"
        "            return 1\n"
        "        _:\n"
        "            return 0\n"
    )
    assert _has(lines, "MatchStmt")
    assert _has(lines, "MatchArm")
    assert _has(lines, "LiteralPattern")
    assert _has(lines, "WildcardPattern")


def test_list_pattern_and_rest_pattern() -> None:
    lines = _lines(
        "fn f(items: List) -> Int:\n"
        "    match items:\n"
        "        [x, *rest]:\n"
        "            return x\n"
        "        _:\n"
        "            return 0\n"
    )
    assert _has(lines, "ListPattern")
    assert _has(lines, "BindingPattern", "'x'")
    assert _has(lines, "RestPattern", "'rest'")


def test_or_pattern_rendered() -> None:
    lines = _lines(
        "fn f(n: Int) -> Int:\n"
        "    match n:\n"
        "        1 | 2:\n"
        "            return 10\n"
        "        _:\n"
        "            return 0\n"
    )
    assert _has(lines, "OrPattern")


def test_import_decl_named_imports() -> None:
    lines = _lines("use helpers: foo, bar\n")
    assert _has(lines, "ImportDecl", "'foo'", "'bar'")
    assert _has(lines, "QualifiedName", "'helpers'")


def test_import_decl_alias() -> None:
    lines = _lines("use helpers as h\n")
    assert _has(lines, "ImportDecl", "'h'")


def test_type_alias_decl_rendered() -> None:
    lines = _lines("pub typealias Score = Int\n")
    assert _has(lines, "TypeAliasDecl", "'Score'", "is_public")


def test_indentation_increases_with_depth() -> None:
    lines = _lines("fn f() -> Int:\n    return 1 + 2\n")
    binary_line = next(line for line in lines if "BinaryExpr" in line)
    module_indent = len("Module") - len("Module".lstrip())
    binary_indent = len(binary_line) - len(binary_line.lstrip())
    assert binary_indent > module_indent


def test_dump_via_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from aster_lang.cli import main

    prog = tmp_path / "prog.aster"
    prog.write_text("fn f() -> Int:\n    return 0\n", encoding="utf-8")
    rc = main(["ast", str(prog)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Module" in out
    assert "FunctionDecl" in out


def test_dump_cli_parse_error_returns_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from aster_lang.cli import main

    prog = tmp_path / "bad.aster"
    prog.write_text("fn (\n", encoding="utf-8")
    rc = main(["ast", str(prog)])
    assert rc == 1
    assert "Parse error" in capsys.readouterr().out

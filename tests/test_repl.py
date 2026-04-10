"""Tests for the REPL session (non-interactive)."""

from __future__ import annotations

import pytest

from aster_lang.repl import ReplError, ReplSession


def make() -> ReplSession:
    return ReplSession()


# ------------------------------------------------------------------
# Expressions print their value


def test_repl_integer_expression() -> None:
    s = make()
    assert s.execute("42\n") == "42"


def test_repl_string_expression() -> None:
    s = make()
    assert s.execute('"hello"\n') == "hello"


def test_repl_arithmetic() -> None:
    s = make()
    assert s.execute("2 + 3\n") == "5"


def test_repl_nil_not_printed() -> None:
    """Nil results are not printed."""
    s = make()
    assert s.execute("nil\n") is None


# ------------------------------------------------------------------
# Declarations persist across calls


def test_repl_let_binding_persists() -> None:
    s = make()
    s.execute("x := 10\n")
    assert s.execute("x\n") == "10"


def test_repl_mutable_binding() -> None:
    s = make()
    s.execute("mut x := 1\n")
    s.execute("x <- 99\n")
    assert s.execute("x\n") == "99"


def test_repl_function_persists() -> None:
    s = make()
    s.execute("fn double(n: Int) -> Int:\n    return n + n\n")
    assert s.execute("double(7)\n") == "14"


def test_repl_multiple_functions() -> None:
    s = make()
    s.execute("fn inc(n: Int) -> Int:\n    return n + 1\n")
    s.execute("fn dec(n: Int) -> Int:\n    return n + -1\n")
    assert s.execute("inc(dec(5))\n") == "5"


# ------------------------------------------------------------------
# Statements work at top level


def test_repl_if_statement() -> None:
    s = make()
    s.execute("mut x := 5\n")
    # if statement doesn't produce a printable result
    result = s.execute("if x > 3:\n    x <- 99\n")
    assert result is None
    assert s.execute("x\n") == "99"


def test_repl_match_statement() -> None:
    s = make()
    src = (
        "fn classify(n: Int) -> String:\n"
        "    match n:\n"
        "        0:\n"
        '            return "zero"\n'
        "        _:\n"
        '            return "other"\n'
    )
    s.execute(src)
    assert s.execute("classify(0)\n") == "zero"
    assert s.execute("classify(5)\n") == "other"


# ------------------------------------------------------------------
# Error handling — errors are raised but session survives


def test_repl_parse_error_raised() -> None:
    s = make()
    with pytest.raises(ReplError):
        s.execute("fn (\n")


def test_repl_runtime_error_raised() -> None:
    s = make()
    with pytest.raises(ReplError):
        s.execute("undefined_var\n")


def test_repl_session_survives_error() -> None:
    """After an error the session keeps working."""
    s = make()
    s.execute("x := 42\n")
    with pytest.raises(ReplError):
        s.execute("undefined_var\n")
    assert s.execute("x\n") == "42"


def test_repl_immutable_mutation_error() -> None:
    s = make()
    s.execute("x := 1\n")
    with pytest.raises(ReplError):
        s.execute("x <- 2\n")


# ------------------------------------------------------------------
# Redefinition and shadowing


def test_repl_redefine_variable() -> None:
    """In REPL, redefining a name rebinds it in the global env."""
    s = make()
    s.execute("x := 1\n")
    s.execute("x := 2\n")
    # The second define overwrites the first in the same scope
    assert s.execute("x\n") == "2"


def test_repl_redefine_function() -> None:
    s = make()
    s.execute("fn f() -> Int:\n    return 1\n")
    s.execute("fn f() -> Int:\n    return 99\n")
    assert s.execute("f()\n") == "99"


# ------------------------------------------------------------------
# Built-in print works


def test_repl_print_builtin(capsys: pytest.CaptureFixture[str]) -> None:
    s = make()
    s.execute('print("hi")\n')
    captured = capsys.readouterr()
    assert captured.out == "hi\n"

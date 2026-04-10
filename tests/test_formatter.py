"""Tests for the Aster formatter."""

from __future__ import annotations

from aster_lang.formatter import format_source

# ------------------------------------------------------------------
# Helpers


def fmt(src: str) -> str:
    """Strip leading/trailing whitespace from src, then format."""
    return format_source(src.strip())


# ------------------------------------------------------------------
# Basic formatting rules


def test_format_source_ensures_trailing_newline() -> None:
    assert format_source("x := 1") == "x := 1\n"


def test_trailing_newline_idempotent() -> None:
    src = 'fn main():\n    print("hi")\n'
    assert format_source(src).endswith("\n")


# ------------------------------------------------------------------
# Declarations


def test_format_let_decl_immutable() -> None:
    assert fmt("x := 42") == "x := 42\n"


def test_format_let_decl_mutable() -> None:
    assert fmt("mut count := 0") == "mut count := 0\n"


def test_format_let_decl_with_type() -> None:
    assert fmt("x: Int := 42") == "x: Int := 42\n"


def test_format_function_no_params_no_return() -> None:
    src = 'fn main():\n    print("hello")'
    result = fmt(src)
    assert result == 'fn main():\n    print("hello")\n'


def test_format_function_with_params_and_return() -> None:
    src = "fn add(a: Int, b: Int) -> Int:\n    return a + b"
    result = fmt(src)
    assert result == "fn add(a: Int, b: Int) -> Int:\n    return a + b\n"


def test_format_multiple_declarations_blank_line() -> None:
    src = "x := 1\ny := 2"
    result = fmt(src)
    assert result == "x := 1\n\ny := 2\n"


def test_format_import_simple() -> None:
    assert fmt("use std.io") == "use std.io\n"


def test_format_import_with_names() -> None:
    assert fmt("use std.io: print, read") == "use std.io: print, read\n"


def test_format_import_with_alias() -> None:
    assert fmt("use std.io as io") == "use std.io as io\n"


def test_format_type_alias() -> None:
    assert fmt("typealias Str = String") == "typealias Str = String\n"


def test_format_type_alias_with_params() -> None:
    assert fmt("typealias Box[T] = List[T]") == "typealias Box[T] = List[T]\n"


# ------------------------------------------------------------------
# Statements


def test_format_let_stmt() -> None:
    src = "fn f():\n    x := 1"
    assert fmt(src) == "fn f():\n    x := 1\n"


def test_format_mut_let_stmt() -> None:
    src = "fn f():\n    mut x := 0"
    assert fmt(src) == "fn f():\n    mut x := 0\n"


def test_format_assign_stmt() -> None:
    src = "fn f():\n    mut x := 0\n    x <- 5"
    assert fmt(src) == "fn f():\n    mut x := 0\n    x <- 5\n"


def test_format_return_with_value() -> None:
    src = "fn f() -> Int:\n    return 42"
    assert fmt(src) == "fn f() -> Int:\n    return 42\n"


def test_format_return_void() -> None:
    src = "fn f():\n    return"
    assert fmt(src) == "fn f():\n    return\n"


def test_format_if_stmt() -> None:
    src = "fn f():\n    if x > 0:\n        return x"
    assert fmt(src) == "fn f():\n    if x > 0:\n        return x\n"


def test_format_if_else_stmt() -> None:
    src = "fn f():\n    if x > 0:\n        return x\n    else:\n        return 0"
    assert fmt(src) == "fn f():\n    if x > 0:\n        return x\n    else:\n        return 0\n"


def test_format_while_stmt() -> None:
    src = "fn f():\n    while i < 10:\n        i <- i + 1"
    assert fmt(src) == "fn f():\n    while i < 10:\n        i <- i + 1\n"


def test_format_for_stmt() -> None:
    src = "fn f():\n    for x in items:\n        print(x)"
    assert fmt(src) == "fn f():\n    for x in items:\n        print(x)\n"


def test_format_break_continue() -> None:
    src = "fn f():\n    while true:\n        break"
    assert fmt(src) == "fn f():\n    while true:\n        break\n"


# ------------------------------------------------------------------
# Expressions


def test_format_integer_literal() -> None:
    assert fmt("x := 123") == "x := 123\n"


def test_format_string_literal() -> None:
    assert fmt('x := "hello"') == 'x := "hello"\n'


def test_format_string_with_escapes() -> None:
    assert fmt('x := "a\\nb"') == 'x := "a\\nb"\n'


def test_format_bool_true() -> None:
    assert fmt("x := true") == "x := true\n"


def test_format_bool_false() -> None:
    assert fmt("x := false") == "x := false\n"


def test_format_nil() -> None:
    assert fmt("x := nil") == "x := nil\n"


def test_format_arithmetic() -> None:
    assert fmt("x := 1 + 2 * 3") == "x := 1 + 2 * 3\n"


def test_format_arithmetic_precedence_parens() -> None:
    # (1 + 2) * 3 — the addition needs parens due to lower precedence
    src = "x := (1 + 2) * 3"
    result = fmt(src)
    assert result == "x := (1 + 2) * 3\n"


def test_format_comparison() -> None:
    assert fmt("x := a <= b") == "x := a <= b\n"


def test_format_logical() -> None:
    assert fmt("x := a and b or c") == "x := a and b or c\n"


def test_format_unary_not() -> None:
    assert fmt("x := not true") == "x := not true\n"


def test_format_unary_neg() -> None:
    assert fmt("x := -1") == "x := -1\n"


def test_format_function_call() -> None:
    assert fmt("x := add(1, 2)") == "x := add(1, 2)\n"


def test_format_member_access() -> None:
    assert fmt("x := obj.field") == "x := obj.field\n"


def test_format_index_expr() -> None:
    assert fmt("x := arr[0]") == "x := arr[0]\n"


def test_format_list_expr() -> None:
    assert fmt("x := [1, 2, 3]") == "x := [1, 2, 3]\n"


def test_format_tuple_expr() -> None:
    assert fmt("x := (1, 2)") == "x := (1, 2)\n"


def test_format_record_expr() -> None:
    assert fmt("x := {a: 1, b: 2}") == "x := {a: 1, b: 2}\n"


# ------------------------------------------------------------------
# Type expressions


def test_format_simple_type() -> None:
    src = "fn f(x: Int) -> String:\n    return x"
    result = fmt(src)
    assert "x: Int" in result
    assert "-> String" in result


def test_format_generic_type() -> None:
    src = "fn f(x: List[Int]) -> Int:\n    return x[0]"
    result = fmt(src)
    assert "List[Int]" in result


# ------------------------------------------------------------------
# Idempotence: format(format(x)) == format(x)


def test_idempotent_hello() -> None:
    src = 'fn main():\n    print("hello, world")\n'
    once = format_source(src)
    twice = format_source(once)
    assert once == twice


def test_idempotent_sum_to() -> None:
    src = (
        "fn sum_to(n: Int) -> Int:\n"
        "    mut total := 0\n"
        "    mut i := 1\n"
        "    while i <= n:\n"
        "        total <- total + i\n"
        "        i <- i + 1\n"
        "    return total\n"
    )
    once = format_source(src)
    twice = format_source(once)
    assert once == twice


def test_idempotent_if_else() -> None:
    src = (
        "fn abs(n: Int) -> Int:\n"
        "    if n < 0:\n"
        "        return -n\n"
        "    else:\n"
        "        return n\n"
    )
    once = format_source(src)
    twice = format_source(once)
    assert once == twice


# ------------------------------------------------------------------
# Round-trip: example files


def test_round_trip_hello(tmp_path: object) -> None:
    src = 'fn main():\n    print("hello, world")\n'
    result = format_source(src)
    assert 'print("hello, world")' in result


def test_round_trip_sum_to() -> None:
    src = (
        "fn sum_to(n: Int) -> Int:\n"
        "    mut total := 0\n"
        "    mut i := 1\n"
        "    while i <= n:\n"
        "        total <- total + i\n"
        "        i <- i + 1\n"
        "    return total\n"
    )
    result = format_source(src)
    assert "fn sum_to(n: Int) -> Int:" in result
    assert "mut total := 0" in result
    assert "while i <= n:" in result
    assert "total <- total + i" in result
    assert "return total" in result

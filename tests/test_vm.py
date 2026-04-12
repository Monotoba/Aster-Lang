from __future__ import annotations

from pathlib import Path

import pytest

from aster_lang.cli import main
from aster_lang.vm import VMError, run_path_vm, run_source_vm


def test_vm_runs_hello_world() -> None:
    src = 'fn main():\n    print("hello")\n'
    assert run_source_vm(src) == "hello"


def test_vm_runs_arithmetic_and_function_call() -> None:
    src = (
        "fn add(a: Int, b: Int) -> Int:\n"
        "    return a + b\n"
        "fn main():\n"
        "    x := add(20, 22)\n"
        "    print(x)\n"
    )
    assert run_source_vm(src) == "42"


def test_vm_runs_lambda_expression_call() -> None:
    src = "fn main():\n    inc := x -> x + 1\n    print(inc(41))\n"
    assert run_source_vm(src) == "42"


def test_vm_runs_min_max() -> None:
    src = "fn main():\n    print(max(3, 7))\n    print(min(3, 7))\n"
    assert run_source_vm(src) == "7\n3"


def test_vm_print_rejects_multiple_args() -> None:
    src = "fn main():\n    print(1, 2)\n"
    with pytest.raises(VMError, match="Built-in print expects 1 argument"):
        run_source_vm(src)


def test_vm_int_conversions() -> None:
    src = 'fn main():\n    print(int(true))\n    print(int(false))\n    print(int("99"))\n'
    assert run_source_vm(src) == "1\n0\n99"


def test_vm_int_rejects_invalid_string() -> None:
    src = 'fn main():\n    print(int("nope"))\n'
    with pytest.raises(VMError, match="Cannot convert 'nope' to Int"):
        run_source_vm(src)


def test_vm_len_accepts_string() -> None:
    src = 'fn main():\n    print(len("hello"))\n'
    assert run_source_vm(src) == "5"


def test_vm_len_record() -> None:
    src = "fn main():\n    r := {x: 1, y: 2}\n    print(len(r))\n"
    assert run_source_vm(src) == "2"


def test_vm_str_formats_values() -> None:
    src = "fn main():\n    print(str(true))\n    print(str(nil))\n    print(str({x: 2}))\n"
    assert run_source_vm(src) == "true\nnil\n{x: 2}"


def test_vm_len_rejects_int() -> None:
    src = "fn main():\n    print(len(1))\n"
    with pytest.raises(VMError, match="len\\(\\) not supported for IntValue"):
        run_source_vm(src)


def test_vm_ascii_bytes_output() -> None:
    src = 'fn main():\n    print(ascii_bytes("hi"))\n'
    assert run_source_vm(src) == "[104, 105]"


def test_vm_ascii_bytes_rejects_non_ascii() -> None:
    src = 'fn main():\n    print(ascii_bytes("café"))\n'
    with pytest.raises(VMError, match="ascii_bytes\\(\\) only supports ASCII"):
        run_source_vm(src)


def test_vm_unicode_bytes_output() -> None:
    src = 'fn main():\n    print(unicode_bytes("café"))\n'
    assert run_source_vm(src) == "[99, 97, 102, 195, 169]"


def test_vm_unicode_bytes_rejects_non_string() -> None:
    src = "fn main():\n    print(unicode_bytes(1))\n"
    with pytest.raises(VMError, match="unicode_bytes\\(\\) expects String"):
        run_source_vm(src)


def test_vm_fixed_width_equals_int() -> None:
    src = "fn main():\n    print(byte(255) == 255)\n"
    assert run_source_vm(src) == "true"


def test_vm_deep_equality_collections() -> None:
    src = (
        "fn main():\n"
        "    print([1, 2] == [1, 2])\n"
        "    print([1, 2] == [1, 3])\n"
        "    print((1, 2) == (1, 2))\n"
        "    print({x: 1, y: 2} == {y: 2, x: 1})\n"
        "    print({x: 1} == {x: 2})\n"
        "    print([{x: 1}] == [{x: 1}])\n"
    )
    assert run_source_vm(src) == "true\nfalse\ntrue\ntrue\nfalse\ntrue"


def test_vm_range_rejects_bool() -> None:
    src = "fn main():\n    print(range(false))\n"
    with pytest.raises(VMError, match="range\\(\\) requires integers"):
        run_source_vm(src)


def test_vm_runs_lambda_closure_captures_by_reference() -> None:
    src = "fn main():\n    mut x := 1\n    f := (y) -> x + y\n    x <- 10\n    print(f(2))\n"
    assert run_source_vm(src) == "12"


def test_vm_mut_borrow_parameter_can_mutate_caller() -> None:
    src = (
        "fn inc(x: &mut Int):\n"
        "    x <- x + 1\n"
        "fn main():\n"
        "    mut a := 1\n"
        "    inc(a)\n"
        "    print(a)\n"
    )
    assert run_source_vm(src) == "2"


def test_vm_mut_borrow_can_target_record_member() -> None:
    src = (
        "fn inc(x: &mut Int):\n"
        "    x <- x + 1\n"
        "fn main():\n"
        "    mut r := {x: 1}\n"
        "    inc(&mut r.x)\n"
        "    print(r.x)\n"
    )
    assert run_source_vm(src) == "2"


def test_vm_mut_borrow_can_target_list_index() -> None:
    src = (
        "fn inc(x: &mut Int):\n"
        "    x <- x + 1\n"
        "fn main():\n"
        "    mut xs := [1, 2]\n"
        "    inc(&mut xs[0])\n"
        "    print(xs[0])\n"
    )
    assert run_source_vm(src) == "2"


def test_vm_mut_borrow_can_target_nested_member_chain() -> None:
    src = (
        "fn inc(x: &mut Int):\n"
        "    x <- x + 1\n"
        "fn main():\n"
        "    mut r := {inner: {x: 1}}\n"
        "    inc(&mut r.inner.x)\n"
        "    print(r.inner.x)\n"
    )
    assert run_source_vm(src) == "2"


def test_vm_mut_borrow_can_target_nested_index_chain() -> None:
    src = (
        "fn inc(x: &mut Int):\n"
        "    x <- x + 1\n"
        "fn main():\n"
        "    mut r := {items: [1, 2]}\n"
        "    inc(&mut r.items[0])\n"
        "    print(r.items[0])\n"
    )
    assert run_source_vm(src) == "2"


def test_vm_mut_borrow_can_target_computed_record_member() -> None:
    src = "fn main():\n    p := &mut {x: 1}.x\n    p <- 7\n    print(*p)\n"
    assert run_source_vm(src) == "7"


def test_vm_mut_borrow_can_target_computed_list_index() -> None:
    src = "fn main():\n    p := &mut [1, 2][0]\n    p <- 9\n    print(*p)\n"
    assert run_source_vm(src) == "9"


def test_vm_mut_borrow_rejects_immutable_variable() -> None:
    src = "fn main():\n    x := 1\n    p := &mut x\n"
    with pytest.raises(VMError, match="Cannot take &mut of immutable variable 'x'"):
        run_source_vm(src)


def test_vm_assign_through_immutable_reference_rejected() -> None:
    src = "fn main():\n    x := 1\n    p := &x\n    p <- 2\n"
    with pytest.raises(VMError, match="Cannot assign through immutable reference 'p'"):
        run_source_vm(src)


def test_vm_assign_to_immutable_global_rejected() -> None:
    src = "x := 1\n\nfn bump():\n    x <- 2\n\nfn main():\n    bump()\n"
    with pytest.raises(VMError, match="Cannot assign to immutable variable 'x'"):
        run_source_vm(src)


def test_vm_mut_borrow_immutable_global_rejected() -> None:
    src = "x := 1\n\nfn bump(y: &mut Int):\n    y <- y + 1\n\nfn main():\n    bump(&mut x)\n"
    with pytest.raises(VMError, match="Cannot take &mut of immutable variable 'x'"):
        run_source_vm(src)


def test_vm_assign_to_immutable_captured_rejected() -> None:
    src = "fn main():\n    x := 1\n    f := () -> :\n        x <- 2\n    f()\n"
    with pytest.raises(VMError, match="Cannot assign to immutable variable 'x'"):
        run_source_vm(src)


def test_vm_runs_if_else() -> None:
    src = 'fn main():\n    if 1 < 2:\n        print("yes")\n    else:\n        print("no")\n'
    assert run_source_vm(src) == "yes"


def test_vm_short_circuits_and() -> None:
    src = (
        "fn f() -> Bool:\n"
        '    print("f")\n'
        "    return false\n"
        "fn t() -> Bool:\n"
        '    print("t")\n'
        "    return true\n"
        "fn main():\n"
        "    x := f() and t()\n"
        "    print(x)\n"
    )
    # `t()` should not run.
    assert run_source_vm(src) == "f\nfalse"


def test_vm_short_circuits_or() -> None:
    src = (
        "fn t() -> Bool:\n"
        '    print("t")\n'
        "    return true\n"
        "fn f() -> Bool:\n"
        '    print("f")\n'
        "    return false\n"
        "fn main():\n"
        "    x := t() or f()\n"
        "    print(x)\n"
    )
    # `f()` should not run.
    assert run_source_vm(src) == "t\ntrue"


def test_vm_runs_while_loop() -> None:
    src = (
        "fn main():\n"
        "    mut i := 0\n"
        "    mut s := 0\n"
        "    while i < 5:\n"
        "        s <- s + i\n"
        "        i <- i + 1\n"
        "    print(s)\n"
    )
    assert run_source_vm(src) == "10"


def test_vm_runs_collections_and_access() -> None:
    src = (
        "fn main():\n"
        "    xs := [1, 2, 3]\n"
        "    t := (10, 20)\n"
        "    r := {x: 7, y: 9}\n"
        "    print(xs[1])\n"
        "    print(t[0])\n"
        "    print(r.x)\n"
    )
    assert run_source_vm(src) == "2\n10\n7"


def test_vm_runs_match_literal_wildcard_and_binding() -> None:
    src = (
        "fn main():\n"
        "    n := 2\n"
        "    match n:\n"
        "        0:\n"
        '            print("zero")\n'
        "        1 | 2:\n"
        '            print("small")\n'
        "        x:\n"
        "            print(x)\n"
        "        _:\n"
        '            print("many")\n'
    )
    assert run_source_vm(src) == "small"


def test_vm_runs_match_tuple_pattern() -> None:
    src = (
        "fn main():\n"
        "    t := (1, 42)\n"
        "    match t:\n"
        "        (1, x):\n"
        "            print(x)\n"
        "        _:\n"
        "            print(0)\n"
    )
    assert run_source_vm(src) == "42"


def test_vm_runs_match_list_pattern_with_rest() -> None:
    src = (
        "fn main():\n"
        "    xs := [1, 2, 3]\n"
        "    match xs:\n"
        "        [1, *tail]:\n"
        "            print(tail[0])\n"
        "        _:\n"
        "            print(0)\n"
    )
    assert run_source_vm(src) == "2"


def test_vm_runs_match_record_pattern() -> None:
    src = (
        "fn main():\n"
        "    r := {x: 7, y: 9}\n"
        "    match r:\n"
        "        {x, y}:\n"
        "            print(y)\n"
        "        _:\n"
        "            print(0)\n"
    )
    assert run_source_vm(src) == "9"


def test_vm_runs_match_structural_or_pattern() -> None:
    src = (
        "fn main():\n"
        "    xs := [0, 5]\n"
        "    match xs:\n"
        "        [x, 0] | [0, x]:\n"
        "            print(x)\n"
        "        _:\n"
        "            print(0)\n"
    )
    assert run_source_vm(src) == "5"


def test_vm_supports_index_and_member_assignment() -> None:
    src = (
        "fn main():\n"
        "    mut xs := [1, 2]\n"
        "    xs[0] <- 9\n"
        "    mut r := {x: 1}\n"
        "    r.x <- 7\n"
        "    print(xs[0])\n"
        "    print(r.x)\n"
    )
    assert run_source_vm(src) == "9\n7"


def test_vm_record_string_indexing() -> None:
    src = 'fn main():\n    r := {x: 1}\n    print(r["x"])\n'
    assert run_source_vm(src) == "1"


def test_vm_supports_nested_member_and_index_assignment() -> None:
    src = (
        "fn main():\n"
        "    mut r := {inner: {x: 1}, items: [1, 2]}\n"
        "    r.inner.x <- 7\n"
        "    r.items[0] <- 9\n"
        "    print(r.inner.x)\n"
        "    print(r.items[0])\n"
    )
    assert run_source_vm(src) == "7\n9"


def test_vm_supports_computed_member_and_index_assignment() -> None:
    src = 'fn main():\n    {x: 1}.x <- 7\n    [1, 2][0] <- 9\n    print("ok")\n'
    assert run_source_vm(src) == "ok"


def test_vm_index_error_message() -> None:
    src = "fn main():\n    r := {x: 1}\n    print(r[0])\n"
    with pytest.raises(VMError, match="Cannot index dict with int"):
        run_source_vm(src)


def test_vm_rejects_unsupported_control_flow() -> None:
    src = "fn main():\n    mut t := (1, 2)\n    t[0] <- 0\n"
    try:
        run_source_vm(src)
    except VMError as exc:
        assert "index assignment" in str(exc) or "Unsupported" in str(exc)
    else:
        raise AssertionError("expected VMError")


def test_cli_vm_command(tmp_path: Path) -> None:
    # Keep this simple: the rest of CLI is well covered in test_cli.py.
    program = tmp_path / "main.aster"
    program.write_text('fn main():\n    print("ok")\n', encoding="utf-8")
    assert main(["vm", str(program)]) == 0


def test_vm_imports_sibling_module(tmp_path: Path) -> None:
    (tmp_path / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n    return 42\n",
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use helpers\nfn main():\n    print(helpers.answer())\n",
        encoding="utf-8",
    )
    assert run_path_vm(program) == "42"


def test_vm_runs_for_loop_over_range_with_break_continue() -> None:
    src = (
        "fn main():\n"
        "    mut s := 0\n"
        "    for i in range(10):\n"
        "        if i == 2:\n"
        "            continue\n"
        "        if i == 6:\n"
        "            break\n"
        "        s <- s + i\n"
        "    print(s)\n"
    )
    # i = 0,1,3,4,5 => sum = 13
    assert run_source_vm(src) == "13"


# ------------------------------------------------------------------
# Destructuring bindings


def test_vm_tuple_destructuring_binding() -> None:
    src = "fn main():\n    (a, b) := (10, 20)\n    print(a)\n    print(b)\n"
    assert run_source_vm(src) == "10\n20"


def test_vm_list_destructuring_binding_with_rest() -> None:
    src = "fn main():\n    [head, *tail] := [1, 2, 3]\n    print(head)\n    print(tail[0])\n"
    assert run_source_vm(src) == "1\n2"


def test_vm_record_destructuring_binding() -> None:
    src = "fn main():\n    {x, y} := {x: 7, y: 9}\n    print(x)\n    print(y)\n"
    assert run_source_vm(src) == "7\n9"


def test_vm_nested_tuple_destructuring() -> None:
    src = (
        "fn swap(pair: Tuple) -> Tuple:\n"
        "    (a, b) := pair\n"
        "    return (b, a)\n"
        "fn main():\n"
        "    (x, y) := swap((1, 2))\n"
        "    print(x)\n"
        "    print(y)\n"
    )
    assert run_source_vm(src) == "2\n1"


def test_vm_mutable_destructuring_binding_allows_reassign() -> None:
    src = "fn main():\n    mut (a, b) := (1, 2)\n    a <- 99\n    print(a)\n    print(b)\n"
    assert run_source_vm(src) == "99\n2"


# ------------------------------------------------------------------
# Mutability enforcement


def test_vm_immutable_binding_rejects_reassign() -> None:
    src = "fn main():\n    x := 1\n    x <- 2\n"
    try:
        run_source_vm(src)
    except VMError as exc:
        assert "immutable" in str(exc)
    else:
        raise AssertionError("expected VMError for immutable reassign")


def test_vm_mutable_binding_allows_reassign() -> None:
    src = "fn main():\n    mut x := 1\n    x <- 42\n    print(x)\n"
    assert run_source_vm(src) == "42"

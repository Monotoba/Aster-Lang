"""Tests for the Aster → Python transpiler."""

from __future__ import annotations

import subprocess
import sys
import textwrap

from aster_lang.compiler import compile_source


def py(src: str) -> str:
    """Compile Aster source and return the Python code."""
    artifact = compile_source(textwrap.dedent(src).strip() + "\n")
    assert not artifact.errors, artifact.errors
    return artifact.code


def run_py(src: str) -> str:
    """Compile Aster, run the resulting Python, capture stdout."""
    code = py(src)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.rstrip("\n")


# ------------------------------------------------------------------
# Structural output checks


def test_transpile_function_def() -> None:
    code = py("fn add(a: Int, b: Int) -> Int:\n    return a + b\n")
    assert "def add(a, b):" in code
    assert "return a + b" in code


def test_transpile_let_binding() -> None:
    code = py("x := 42\n")
    assert "x = 42" in code


def test_transpile_mutable_let() -> None:
    code = py("mut x := 0\n")
    assert "x = 0" in code


def test_transpile_tuple_destructuring_binding() -> None:
    code = py("fn main():\n    (x, y) := pair\n")
    assert "(x, y) = pair" in code


def test_transpile_list_destructuring_binding_with_rest() -> None:
    code = py("fn main():\n    [head, *tail] := items\n")
    assert "[head, *tail] = items" in code


def test_transpile_record_destructuring_binding() -> None:
    code = py("fn main():\n    {x, y} := rec\n")
    assert "__aster_tmp0 = rec" in code
    assert 'x = __aster_tmp0["x"]' in code
    assert 'y = __aster_tmp0["y"]' in code


def test_transpile_bool_literals() -> None:
    code = py("x := true\ny := false\n")
    assert "x = True" in code
    assert "y = False" in code


def test_transpile_nil() -> None:
    code = py("x := nil\n")
    assert "x = None" in code


def test_transpile_main_guard() -> None:
    code = py('fn main():\n    print("hi")\n')
    assert 'if __name__ == "__main__":' in code
    assert "main()" in code


def test_transpile_no_main_guard_without_main() -> None:
    code = py("fn add(a: Int, b: Int) -> Int:\n    return a + b\n")
    assert "__main__" not in code


def test_transpile_import_simple() -> None:
    code = py("use os\n")
    assert "import os" in code


def test_transpile_import_from() -> None:
    code = py("use os.path: join, exists\n")
    assert "from os.path import join, exists" in code


def test_transpile_import_alias() -> None:
    code = py("use sys as system\n")
    assert "import sys as system" in code


def test_transpile_match_to_if_elif() -> None:
    src = (
        "fn f(n: Int) -> Int:\n"
        "    match n:\n"
        "        0:\n"
        "            return 10\n"
        "        1:\n"
        "            return 20\n"
        "        _:\n"
        "            return 99\n"
    )
    code = py(src)
    assert "if n == 0:" in code
    assert "elif n == 1:" in code
    assert "else:" in code
    assert "return 10" in code
    assert "return 20" in code
    assert "return 99" in code


def test_transpile_match_binding() -> None:
    src = "fn double(n: Int) -> Int:\n    match n:\n        x:\n            return x + x\n"
    code = py(src)
    assert "else:" in code
    assert "x = n" in code
    assert "return x + x" in code


def test_transpile_match_or_pattern_binding_irrefutable() -> None:
    # Binding or-pattern: both alternatives are the same binding name.
    # Should emit `else:` (irrefutable) and inject the binding assignment.
    src = "fn f(n: Int) -> Int:\n    match n:\n        x | x:\n            return x\n"
    code = py(src)
    assert "else:" in code
    assert "x = n" in code
    assert "return x" in code


def test_transpile_match_or_pattern_literal_preserved() -> None:
    # Literal-only or-pattern should still emit an elif condition, not else.
    src = (
        "fn f(n: Int) -> Int:\n"
        "    match n:\n"
        "        1 | 2:\n"
        "            return 10\n"
        "        _:\n"
        "            return 0\n"
    )
    code = py(src)
    assert "n == 1" in code and "n == 2" in code and "or" in code
    assert "return 10" in code


# ------------------------------------------------------------------
# End-to-end: compile and run


def test_run_hello_world() -> None:
    src = 'fn main():\n    print("hello, world")\n'
    assert run_py(src) == "hello, world"


def test_run_arithmetic() -> None:
    src = "fn main():\n    print(2 + 3 * 4)\n"
    assert run_py(src) == "14"


def test_run_function_call() -> None:
    src = "fn add(a: Int, b: Int) -> Int:\n    return a + b\nfn main():\n    print(add(3, 4))\n"
    assert run_py(src) == "7"


def test_run_if_else() -> None:
    src = (
        "fn abs_val(n: Int) -> Int:\n"
        "    if n < 0:\n"
        "        return -n\n"
        "    else:\n"
        "        return n\n"
        "fn main():\n"
        "    print(abs_val(-5))\n"
        "    print(abs_val(3))\n"
    )
    assert run_py(src) == "5\n3"


def test_run_while_loop() -> None:
    src = (
        "fn sum_to(n: Int) -> Int:\n"
        "    mut total := 0\n"
        "    mut i := 1\n"
        "    while i <= n:\n"
        "        total <- total + i\n"
        "        i <- i + 1\n"
        "    return total\n"
        "fn main():\n"
        "    print(sum_to(10))\n"
    )
    assert run_py(src) == "55"


def test_run_for_range() -> None:
    src = "fn main():\n    mut s := 0\n    for i in range(5):\n        s <- s + i\n    print(s)\n"
    assert run_py(src) == "10"


def test_run_recursion_factorial() -> None:
    src = (
        "fn fact(n: Int) -> Int:\n"
        "    if n <= 1:\n"
        "        return 1\n"
        "    return n * fact(n + -1)\n"
        "fn main():\n"
        "    print(fact(5))\n"
    )
    assert run_py(src) == "120"


def test_run_string_concat() -> None:
    src = 'fn main():\n    x := "hello" + ", " + "world"\n    print(x)\n'
    assert run_py(src) == "hello, world"


def test_run_list_and_index() -> None:
    src = "fn main():\n    xs := [10, 20, 30]\n    print(xs[1])\n"
    assert run_py(src) == "20"


def test_run_match_classify() -> None:
    src = (
        "fn classify(n: Int) -> String:\n"
        "    match n:\n"
        "        0:\n"
        '            return "zero"\n'
        "        1:\n"
        '            return "one"\n'
        "        _:\n"
        '            return "many"\n'
        "fn main():\n"
        "    print(classify(0))\n"
        "    print(classify(1))\n"
        "    print(classify(5))\n"
    )
    assert run_py(src) == "zero\none\nmany"


def test_run_match_list_pattern_binding() -> None:
    src = (
        "fn head(items: List) -> Int:\n"
        "    match items:\n"
        "        [x, *rest]:\n"
        "            return x\n"
        "        _:\n"
        "            return 0\n"
        "fn main():\n"
        "    print(head([42, 1, 2]))\n"
        "    print(head([]))\n"
    )
    assert run_py(src) == "42\n0"


def test_run_match_list_pattern_literal_guard() -> None:
    src = (
        "fn check(items: List) -> String:\n"
        "    match items:\n"
        "        [0, x]:\n"
        '            return "starts with zero"\n'
        "        _:\n"
        '            return "other"\n'
        "fn main():\n"
        "    print(check([0, 5]))\n"
        "    print(check([1, 5]))\n"
    )
    assert run_py(src) == "starts with zero\nother"


def test_run_match_or_pattern_structural_binding() -> None:
    # Or-pattern where both alternatives bind the same name from different positions.
    src = (
        "fn extract(items: List) -> Int:\n"
        "    match items:\n"
        "        [x, 0] | [0, x]:\n"
        "            return x\n"
        "        _:\n"
        "            return -1\n"
        "fn main():\n"
        "    print(extract([7, 0]))\n"
        "    print(extract([0, 3]))\n"
        "    print(extract([1, 2]))\n"
    )
    assert run_py(src) == "7\n3\n-1"

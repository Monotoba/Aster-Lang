"""Tests for the interpreter."""

from __future__ import annotations

from pathlib import Path

from aster_lang.interpreter import interpret_source

# Literals and basic expressions


def test_integer_literal() -> None:
    """Test integer literal evaluation."""
    result = interpret_source("x := 42\n")
    assert result.error is None


def test_string_literal() -> None:
    """Test string literal evaluation."""
    result = interpret_source('x := "hello"\n')
    assert result.error is None


def test_bool_literal() -> None:
    """Test boolean literal evaluation."""
    result = interpret_source("x := true\ny := false\n")
    assert result.error is None


def test_nil_literal() -> None:
    """Test nil literal evaluation."""
    result = interpret_source("x := nil\n")
    assert result.error is None


# Arithmetic


def test_arithmetic_addition() -> None:
    """Test addition."""
    result = interpret_source("""fn main():
    x := 2 + 3
    print(x)
""")
    assert result.output == "5"


def test_arithmetic_subtraction() -> None:
    """Test subtraction."""
    result = interpret_source("""fn main():
    x := 10 - 3
    print(x)
""")
    assert result.output == "7"


def test_arithmetic_multiplication() -> None:
    """Test multiplication."""
    result = interpret_source("""fn main():
    x := 4 * 5
    print(x)
""")
    assert result.output == "20"


def test_arithmetic_division() -> None:
    """Test division."""
    result = interpret_source("""fn main():
    x := 15 / 3
    print(x)
""")
    assert result.output == "5"


def test_arithmetic_modulo() -> None:
    """Test modulo."""
    result = interpret_source("""fn main():
    x := 10 % 3
    print(x)
""")
    assert result.output == "1"


def test_arithmetic_precedence() -> None:
    """Test operator precedence."""
    result = interpret_source("""fn main():
    x := 2 + 3 * 4
    print(x)
""")
    assert result.output == "14"


# Comparison


def test_comparison_less_than() -> None:
    """Test less than comparison."""
    result = interpret_source("""fn main():
    x := 5 < 10
    print(x)
""")
    assert result.output == "true"


def test_comparison_greater_than() -> None:
    """Test greater than comparison."""
    result = interpret_source("""fn main():
    x := 10 > 5
    print(x)
""")
    assert result.output == "true"


def test_comparison_equal() -> None:
    """Test equality comparison."""
    result = interpret_source("""fn main():
    x := 5 == 5
    print(x)
""")
    assert result.output == "true"


def test_comparison_not_equal() -> None:
    """Test inequality comparison."""
    result = interpret_source("""fn main():
    x := 5 != 10
    print(x)
""")
    assert result.output == "true"


# Logical operators


def test_logical_and() -> None:
    """Test logical and."""
    result = interpret_source("""fn main():
    x := true and false
    print(x)
""")
    assert result.output == "false"


def test_logical_or() -> None:
    """Test logical or."""
    result = interpret_source("""fn main():
    x := true or false
    print(x)
""")
    assert result.output == "true"


def test_logical_and_short_circuits() -> None:
    result = interpret_source(
        """fn f() -> Bool:
    print("f")
    return false
fn t() -> Bool:
    print("t")
    return true
fn main():
    x := f() and t()
    print(x)
"""
    )
    assert result.output == "f\nfalse"


def test_logical_or_short_circuits() -> None:
    result = interpret_source(
        """fn t() -> Bool:
    print("t")
    return true
fn f() -> Bool:
    print("f")
    return false
fn main():
    x := t() or f()
    print(x)
"""
    )
    assert result.output == "t\ntrue"


def test_logical_not() -> None:
    """Test logical not."""
    result = interpret_source("""fn main():
    x := not true
    print(x)
""")
    assert result.output == "false"


# Variables and assignment


def test_variable_binding() -> None:
    """Test variable binding."""
    result = interpret_source("""fn main():
    x := 42
    print(x)
""")
    assert result.output == "42"


def test_mutable_assignment() -> None:
    """Test assignment to mutable variable."""
    result = interpret_source("""fn main():
    mut x := 10
    x <- 20
    print(x)
""")
    assert result.output == "20"


def test_immutable_assignment_error() -> None:
    """Test error when assigning to immutable variable."""
    result = interpret_source("""fn main():
    x := 10
    x <- 20
""")
    assert result.error is not None
    assert "immutable" in result.error.lower()


# Control flow - if statements


def test_if_true_branch() -> None:
    """Test if statement with true condition."""
    result = interpret_source("""fn main():
    if true:
        print(42)
""")
    assert result.output == "42"


def test_if_false_branch() -> None:
    """Test if statement with false condition."""
    result = interpret_source("""fn main():
    if false:
        print(42)
""")
    assert result.output == ""


def test_if_else() -> None:
    """Test if-else statement."""
    result = interpret_source("""fn main():
    if false:
        print(1)
    else:
        print(2)
""")
    assert result.output == "2"


def test_if_with_expression() -> None:
    """Test if with comparison expression."""
    result = interpret_source("""fn main():
    x := 5
    if x < 10:
        print(true)
    else:
        print(false)
""")
    assert result.output == "true"


# Control flow - while loops


def test_while_loop() -> None:
    """Test while loop."""
    result = interpret_source("""fn main():
    mut i := 0
    while i < 3:
        print(i)
        i <- i + 1
""")
    assert result.output == "0\n1\n2"


def test_while_break() -> None:
    """Test break in while loop."""
    result = interpret_source("""fn main():
    mut i := 0
    while true:
        if i >= 2:
            break
        print(i)
        i <- i + 1
""")
    assert result.output == "0\n1"


def test_while_continue() -> None:
    """Test continue in while loop."""
    result = interpret_source("""fn main():
    mut i := 0
    while i < 3:
        i <- i + 1
        if i == 2:
            continue
        print(i)
""")
    assert result.output == "1\n3"


# Control flow - for loops


def test_for_loop() -> None:
    """Test for loop."""
    result = interpret_source("""fn main():
    for x in [1, 2, 3]:
        print(x)
""")
    assert result.output == "1\n2\n3"


# Functions


def test_function_call() -> None:
    """Test function definition and call."""
    result = interpret_source("""fn greet():
    print("hello")

fn main():
    greet()
""")
    assert result.output == "hello"


def test_function_with_parameters() -> None:
    """Test function with parameters."""
    result = interpret_source("""fn add(a: Int, b: Int) -> Int:
    return a + b

fn main():
    result := add(5, 3)
    print(result)
""")
    assert result.output == "8"


def test_function_return() -> None:
    """Test function return value."""
    result = interpret_source("""fn double(x: Int) -> Int:
    return x * 2

fn main():
    y := double(21)
    print(y)
""")
    assert result.output == "42"


def test_function_early_return() -> None:
    """Test early return from function."""
    result = interpret_source("""fn test(x: Int) -> Int:
    if x < 0:
        return 0
    return x

fn main():
    print(test(-5))
    print(test(10))
""")
    assert result.output == "0\n10"


def test_lambda_expression_call() -> None:
    result = interpret_source(
        """fn main():
    inc := x -> x + 1
    print(inc(41))
"""
    )
    assert result.output == "42"


def test_lambda_closure_captures_by_reference() -> None:
    result = interpret_source(
        """fn main():
    mut x := 1
    f := (y) -> x + y
    x <- 10
    print(f(2))
"""
    )
    assert result.output == "12"


# Collections


def test_list_creation() -> None:
    """Test list creation."""
    result = interpret_source("""fn main():
    x := [1, 2, 3]
    print(x)
""")
    assert result.output == "[1, 2, 3]"


def test_list_indexing() -> None:
    """Test list indexing."""
    result = interpret_source("""fn main():
    x := [10, 20, 30]
    print(x[0])
    print(x[2])
""")
    assert result.output == "10\n30"


def test_list_index_assignment() -> None:
    """Test list index assignment (copy-update-store)."""
    result = interpret_source("""fn main():
    mut xs := [1, 2]
    xs[0] <- 9
    print(xs[0])
""")
    assert result.error is None
    assert result.output == "9"


def test_tuple_creation() -> None:
    """Test tuple creation."""
    result = interpret_source("""fn main():
    x := (1, 2, 3)
    print(x)
""")
    assert result.output == "(1, 2, 3)"


def test_record_creation() -> None:
    """Test record creation."""
    result = interpret_source("""fn main():
    x := {a: 1, b: 2}
    print(x)
""")
    assert "a: 1" in result.output
    assert "b: 2" in result.output


def test_record_member_access() -> None:
    """Test record member access."""
    result = interpret_source("""fn main():
    x := {name: 42}
    print(x.name)
""")
    assert result.output == "42"


def test_record_member_assignment() -> None:
    """Test record member assignment (copy-update-store)."""
    result = interpret_source("""fn main():
    mut r := {x: 1}
    r.x <- 7
    print(r.x)
""")
    assert result.error is None
    assert result.output == "7"


# Built-in functions


def test_builtin_print() -> None:
    """Test built-in print function."""
    result = interpret_source("""fn main():
    print("hello, world")
""")
    assert result.output == "hello, world"


def test_hello_world_demo_output() -> None:
    """Test hello world example."""
    result = interpret_source('fn main():\n    print("hello, world")\n')
    assert result.output == "hello, world"


# Real examples


def test_sum_to_example() -> None:
    """Test sum_to.aster example."""
    result = interpret_source("""fn sum_to(n: Int) -> Int:
    mut total := 0
    mut i := 1
    while i <= n:
        total <- total + i
        i <- i + 1
    return total

fn main():
    result := sum_to(10)
    print(result)
""")
    assert result.output == "55"


def test_factorial() -> None:
    """Test factorial function."""
    result = interpret_source("""fn factorial(n: Int) -> Int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

fn main():
    print(factorial(5))
""")
    assert result.output == "120"


def test_fibonacci() -> None:
    """Test fibonacci function."""
    result = interpret_source("""fn fib(n: Int) -> Int:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

fn main():
    print(fib(10))
""")
    assert result.output == "55"


# Match statement


def test_match_integer_literal() -> None:
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
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "zero\none\nmany"


def test_match_wildcard_only() -> None:
    src = (
        "fn f(x: Int) -> Int:\n"
        "    match x:\n"
        "        _:\n"
        "            return 99\n"
        "fn main():\n"
        "    print(f(42))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "99"


def test_match_binding_pattern() -> None:
    src = (
        "fn double(x: Int) -> Int:\n"
        "    match x:\n"
        "        n:\n"
        "            return n + n\n"
        "fn main():\n"
        "    print(double(7))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "14"


def test_match_string_pattern() -> None:
    src = (
        "fn greet(name: String) -> String:\n"
        "    match name:\n"
        '        "world":\n'
        '            return "hello, world!"\n'
        "        _:\n"
        '            return "hello, stranger"\n'
        "fn main():\n"
        '    print(greet("world"))\n'
        '    print(greet("alice"))\n'
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "hello, world!\nhello, stranger"


def test_match_bool_pattern() -> None:
    src = (
        "fn describe(b: Bool) -> String:\n"
        "    match b:\n"
        "        true:\n"
        '            return "yes"\n'
        "        false:\n"
        '            return "no"\n'
        "        _:\n"
        '            return "?"\n'
        "fn main():\n"
        "    print(describe(true))\n"
        "    print(describe(false))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "yes\nno"


def test_match_no_arm_matches() -> None:
    """When no arm matches the subject, execution continues without error."""
    src = (
        "fn f():\n"
        "    match 99:\n"
        "        0:\n"
        "            return 0\n"
        "fn main():\n"
        '    print("done")\n'
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "done"


def test_match_demo_example() -> None:
    """The updated match_demo.aster example should execute correctly."""
    import pathlib

    src = pathlib.Path("examples/match_demo.aster").read_text()
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "zero\none\nmany"


def test_match_tuple_pattern_with_binding() -> None:
    src = (
        "fn second_if_zero(pair) -> Int:\n"
        "    match pair:\n"
        "        (0, x):\n"
        "            return x\n"
        "        _:\n"
        "            return -1\n"
        "fn main():\n"
        "    print(second_if_zero((0, 7)))\n"
        "    print(second_if_zero((1, 7)))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "7\n-1"


def test_match_nested_tuple_pattern() -> None:
    src = (
        "fn f(value) -> Int:\n"
        "    match value:\n"
        "        ((1, x), y):\n"
        "            return x + y\n"
        "        _:\n"
        "            return 0\n"
        "fn main():\n"
        "    print(f(((1, 2), 3)))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "5"


def test_match_list_pattern_with_binding() -> None:
    src = (
        "fn second_if_zero(items) -> Int:\n"
        "    match items:\n"
        "        [0, x]:\n"
        "            return x\n"
        "        _:\n"
        "            return -1\n"
        "fn main():\n"
        "    print(second_if_zero([0, 7]))\n"
        "    print(second_if_zero([1, 7]))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "7\n-1"


def test_match_nested_list_pattern() -> None:
    src = (
        "fn f(value) -> Int:\n"
        "    match value:\n"
        "        [[1, x], y]:\n"
        "            return x + y\n"
        "        _:\n"
        "            return 0\n"
        "fn main():\n"
        "    print(f([[1, 2], 3]))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "5"


def test_match_record_pattern_with_binding() -> None:
    src = (
        "fn y_if_x_zero(point) -> Int:\n"
        "    match point:\n"
        "        {x: 0, y}:\n"
        "            return y\n"
        "        _:\n"
        "            return -1\n"
        "fn main():\n"
        "    print(y_if_x_zero({x: 0, y: 7}))\n"
        "    print(y_if_x_zero({x: 1, y: 7}))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "7\n-1"


def test_match_nested_record_pattern() -> None:
    src = (
        "fn f(value) -> Int:\n"
        "    match value:\n"
        "        {point: {x: 1, y}, z}:\n"
        "            return y + z\n"
        "        _:\n"
        "            return 0\n"
        "fn main():\n"
        "    print(f({point: {x: 1, y: 2}, z: 3}))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "5"


def test_match_or_pattern_literals() -> None:
    src = (
        "fn classify(n: Int) -> Int:\n"
        "    match n:\n"
        "        0 | 1:\n"
        "            return 10\n"
        "        _:\n"
        "            return 0\n"
        "fn main():\n"
        "    print(classify(0))\n"
        "    print(classify(1))\n"
        "    print(classify(2))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "10\n10\n0"


def test_match_or_pattern_consistent_binding() -> None:
    # Both alternatives of the or-pattern bind x; arm body uses x
    src = (
        "fn pick(n: Int) -> Int:\n"
        "    match n:\n"
        "        x | x:\n"
        "            return x + 100\n"
        "        _:\n"
        "            return 0\n"
        "fn main():\n"
        "    print(pick(5))\n"
        "    print(pick(7))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "105\n107"


def test_match_list_rest_pattern() -> None:
    src = (
        "fn describe(items) -> Int:\n"
        "    match items:\n"
        "        [head, *tail]:\n"
        "            return len(tail)\n"
        "        _:\n"
        "            return -1\n"
        "fn main():\n"
        "    print(describe([1, 2, 3]))\n"
        "    print(describe([]))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "2\n-1"


def test_match_tuple_rest_pattern() -> None:
    src = (
        "fn describe(value) -> Int:\n"
        "    match value:\n"
        "        (head, *tail):\n"
        "            return len(tail)\n"
        "        _:\n"
        "            return -1\n"
        "fn main():\n"
        "    print(describe((1, 2, 3)))\n"
        "    print(describe(()))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "2\n-1"


def test_import_named_function_from_sibling_module(tmp_path: Path) -> None:
    """Named imports should load sibling .aster modules relative to the caller."""
    (tmp_path / "helpers.aster").write_text(
        "pub fn double(x: Int) -> Int:\n" "    return x + x\n",
        encoding="utf-8",
    )

    result = interpret_source(
        "use helpers: double\n" "fn main():\n" "    print(double(21))\n",
        base_dir=tmp_path,
    )

    assert result.error is None
    assert result.output == "42"


def test_import_module_namespace_from_sibling_module(tmp_path: Path) -> None:
    """Plain module imports should bind a namespace object using the module name."""
    (tmp_path / "math_utils.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )

    result = interpret_source(
        "use math_utils\n" "fn main():\n" "    print(math_utils.answer())\n",
        base_dir=tmp_path,
    )

    assert result.error is None
    assert result.output == "42"


def test_import_missing_module_reports_error(tmp_path: Path) -> None:
    result = interpret_source(
        "use missing\n" "fn main():\n" '    print("nope")\n',
        base_dir=tmp_path,
    )

    assert result.error is not None
    assert "Module not found" in result.error


def test_import_cycle_reports_error(tmp_path: Path) -> None:
    (tmp_path / "a.aster").write_text("use b\nfn value() -> Int:\n    return 1\n", encoding="utf-8")
    (tmp_path / "b.aster").write_text("use a\nfn value() -> Int:\n    return 2\n", encoding="utf-8")

    result = interpret_source(
        "use a\n" "fn main():\n" "    print(a.value())\n",
        base_dir=tmp_path,
    )

    assert result.error is not None
    assert "Cyclic import detected" in result.error


def test_import_resolves_parent_package_root(tmp_path: Path) -> None:
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    result = interpret_source(
        "use lib.helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        base_dir=app_dir,
    )

    assert result.error is None
    assert result.output == "42"


def test_import_resolves_manifest_module_root(tmp_path: Path) -> None:
    (tmp_path / "aster.toml").write_text(
        "[modules]\n" 'search_roots = ["src"]\n',
        encoding="utf-8",
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    result = interpret_source(
        "use helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        base_dir=app_dir,
    )

    assert result.error is None
    assert result.output == "42"


def test_import_resolves_current_package_name_prefix(tmp_path: Path) -> None:
    (tmp_path / "aster.toml").write_text(
        "[package]\n" 'name = "app"\n' "[modules]\n" 'search_roots = ["src"]\n',
        encoding="utf-8",
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    result = interpret_source(
        "use app.helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        base_dir=app_dir,
    )

    assert result.error is None
    assert result.output == "42"


def test_invalid_manifest_package_name_reports_error(tmp_path: Path) -> None:
    (tmp_path / "aster.toml").write_text(
        "[package]\n" "name = 42\n",
        encoding="utf-8",
    )

    result = interpret_source(
        "use missing\n" "fn main():\n" '    print("nope")\n',
        base_dir=tmp_path,
    )

    assert result.error is not None
    assert "package.name must be a string" in result.error


def test_import_private_name_reports_error(tmp_path: Path) -> None:
    (tmp_path / "helpers.aster").write_text(
        "fn hidden() -> Int:\n" "    return 7\n" "pub fn shown() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )

    result = interpret_source(
        "use helpers: hidden\n" "fn main():\n" "    print(hidden())\n",
        base_dir=tmp_path,
    )

    assert result.error is not None
    assert "has no public export 'hidden'" in result.error


def test_import_public_names_only_in_module_namespace(tmp_path: Path) -> None:
    (tmp_path / "helpers.aster").write_text(
        "hidden := 7\n" "pub answer := 42\n",
        encoding="utf-8",
    )

    result = interpret_source(
        "use helpers\n" "fn main():\n" "    print(helpers.answer)\n",
        base_dir=tmp_path,
    )

    assert result.error is None
    assert result.output == "42"

    private_result = interpret_source(
        "use helpers\n" "fn main():\n" "    print(helpers.hidden)\n",
        base_dir=tmp_path,
    )
    assert private_result.error is not None
    assert "has no export 'hidden'" in private_result.error


def test_tuple_destructuring_binding_statement() -> None:
    src = "fn main():\n" "    (x, y) := (2, 3)\n" "    print(x + y)\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "5"


def test_list_destructuring_binding_statement_with_rest() -> None:
    src = (
        "fn main():\n"
        "    [head, *tail] := [1, 2, 3]\n"
        "    print(head)\n"
        "    print(len(tail))\n"
    )
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "1\n2"


def test_record_destructuring_binding_statement() -> None:
    src = "fn main():\n" "    {x, y} := {x: 4, y: 9}\n" "    print(x + y)\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "13"


def test_destructuring_binding_mismatch_reports_error() -> None:
    src = "fn main():\n" "    (x, y) := (1,)\n" "    print(x)\n"
    result = interpret_source(src)
    assert result.error is not None
    assert "Binding pattern does not match initializer" in result.error


# String operations


def test_string_concatenation() -> None:
    src = 'fn main():\n    x := "hello" + ", " + "world"\n    print(x)\n'
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "hello, world"


def test_builtin_len_string() -> None:
    src = 'fn main():\n    print(len("hello"))\n'
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "5"


def test_builtin_len_list() -> None:
    src = "fn main():\n    print(len([1, 2, 3]))\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "3"


def test_builtin_str_int() -> None:
    src = 'fn main():\n    x := str(42)\n    print("value is " + x)\n'
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "value is 42"


def test_builtin_int_string() -> None:
    src = 'fn main():\n    x := int("99")\n    print(x + 1)\n'
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "100"


def test_builtin_int_bool() -> None:
    src = "fn main():\n    print(int(true))\n    print(int(false))\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "1\n0"


def test_string_equality() -> None:
    src = 'fn main():\n    x := "hi"\n    if x == "hi":\n        print("yes")\n'
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "yes"


# Built-in: abs, max, min, range


def test_builtin_abs() -> None:
    src = "fn main():\n    print(abs(-5))\n    print(abs(3))\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "5\n3"


def test_builtin_max() -> None:
    src = "fn main():\n    print(max(3, 7))\n    print(max(10, 2))\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "7\n10"


def test_builtin_min() -> None:
    src = "fn main():\n    print(min(3, 7))\n    print(min(10, 2))\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "3\n2"


def test_builtin_range_one_arg() -> None:
    src = "fn main():\n    for i in range(3):\n        print(i)\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "0\n1\n2"


def test_builtin_range_two_args() -> None:
    src = "fn main():\n    for i in range(2, 5):\n        print(i)\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "2\n3\n4"


def test_builtin_range_used_with_len() -> None:
    src = "fn main():\n    xs := range(10)\n    print(len(xs))\n"
    result = interpret_source(src)
    assert result.error is None
    assert result.output == "10"

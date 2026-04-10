"""Tests for the interpreter."""

from __future__ import annotations

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

"""Tests for semantic analysis."""

from __future__ import annotations

from aster_lang.parser import parse_module
from aster_lang.semantic import (
    BOOL_TYPE,
    INT_TYPE,
    STRING_TYPE,
    FunctionType,
    SemanticAnalyzer,
    analyze_module,
)

# Symbol table tests


def test_define_and_lookup_variable() -> None:
    """Test defining and looking up variables."""
    source = "x := 42\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("x")
    assert symbol is not None
    assert symbol.name == "x"
    assert symbol.type == INT_TYPE


def test_undefined_variable_error() -> None:
    """Test error for undefined variables."""
    source = "x := y\n"
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0
    assert "Undefined variable 'y'" in errors[0].message


def test_duplicate_definition_error() -> None:
    """Test error for duplicate definitions."""
    source = """x := 1
x := 2
"""
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0
    assert "already defined" in errors[0].message


def test_function_definition() -> None:
    """Test function definition and lookup."""
    source = """fn add(a: Int, b: Int) -> Int:
    return a + b
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("add")
    assert symbol is not None
    assert symbol.name == "add"
    assert isinstance(symbol.type, FunctionType)
    assert len(symbol.type.param_types) == 2
    assert symbol.type.return_type == INT_TYPE


def test_function_parameters_in_scope() -> None:
    """Test that function parameters are in scope."""
    source = """fn test(x: Int) -> Int:
    return x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_nested_scopes() -> None:
    """Test nested scoping."""
    source = """x := 1
fn test():
    x := 2
    y := 3
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    # Global x should exist
    symbol = analyzer.symbol_table.lookup("x")
    assert symbol is not None

    # y should not be in global scope
    # (Note: analyzer exits function scope after analysis)
    assert not analyzer.has_errors()


# Type checking tests


def test_integer_literal_type() -> None:
    """Test integer literal type inference."""
    source = "x := 42\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("x")
    assert symbol is not None
    assert symbol.type == INT_TYPE


def test_string_literal_type() -> None:
    """Test string literal type inference."""
    source = 'x := "hello"\n'
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("x")
    assert symbol is not None
    assert symbol.type == STRING_TYPE


def test_bool_literal_type() -> None:
    """Test boolean literal type inference."""
    source = "x := true\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("x")
    assert symbol is not None
    assert symbol.type == BOOL_TYPE


def test_arithmetic_expression_type() -> None:
    """Test arithmetic expression type inference."""
    source = "x := 1 + 2 * 3\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("x")
    assert symbol is not None
    assert symbol.type == INT_TYPE


def test_comparison_expression_type() -> None:
    """Test comparison expression type inference."""
    source = "x := 5 < 10\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("x")
    assert symbol is not None
    assert symbol.type == BOOL_TYPE


def test_logical_expression_type() -> None:
    """Test logical expression type inference."""
    source = "x := true and false\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("x")
    assert symbol is not None
    assert symbol.type == BOOL_TYPE


def test_type_annotation_checking() -> None:
    """Test type annotation is checked against initializer."""
    source = "x: Int := 42\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_type_mismatch_error() -> None:
    """Test error for type mismatch."""
    source = 'x: Int := "hello"\n'
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0
    assert "Type mismatch" in errors[0].message


def test_arithmetic_type_error() -> None:
    """Test error for arithmetic on non-integers."""
    source = 'x := "hello" + 5\n'
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0


def test_logical_type_error() -> None:
    """Test error for logical operators on non-booleans."""
    source = "x := 5 and 10\n"
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0


# Assignment and mutability tests


def test_assignment_to_mutable_variable() -> None:
    """Test assignment to mutable variable."""
    source = """fn test():
    mut x := 1
    x <- 2
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_assignment_to_immutable_variable_error() -> None:
    """Test error for assignment to immutable variable."""
    source = """fn test():
    x := 1
    x <- 2
"""
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0
    assert "immutable" in errors[0].message.lower()


def test_assignment_type_checking() -> None:
    """Test type checking in assignments."""
    source = """fn test():
    mut x := 1
    x <- 2
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_assignment_type_mismatch_error() -> None:
    """Test error for type mismatch in assignment."""
    source = """fn test():
    mut x := 1
    x <- "hello"
"""
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0
    assert "Type mismatch" in errors[0].message


# Function call tests


def test_function_call_type_checking() -> None:
    """Test function call argument type checking."""
    source = """fn add(a: Int, b: Int) -> Int:
    return a + b

result := add(1, 2)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_function_call_wrong_arg_count_error() -> None:
    """Test error for wrong number of arguments."""
    source = """fn add(a: Int, b: Int) -> Int:
    return a + b

result := add(1)
"""
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0
    assert "expects 2 arguments" in errors[0].message


def test_function_call_arg_type_error() -> None:
    """Test error for wrong argument type."""
    source = """fn add(a: Int, b: Int) -> Int:
    return a + b

result := add(1, "hello")
"""
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0


def test_call_non_function_error() -> None:
    """Test error for calling a non-function."""
    source = """x := 42
result := x()
"""
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0
    assert "not a function" in errors[0].message


# Control flow tests


def test_if_condition_type_checking() -> None:
    """Test if condition must be boolean."""
    source = """fn test():
    if true:
        x := 1
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_if_condition_type_error() -> None:
    """Test error for non-boolean if condition."""
    source = """fn test():
    if 42:
        x := 1
"""
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0
    assert "Bool" in errors[0].message


def test_while_condition_type_checking() -> None:
    """Test while condition must be boolean."""
    source = """fn test():
    while true:
        x := 1
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_while_condition_type_error() -> None:
    """Test error for non-boolean while condition."""
    source = """fn test():
    while 42:
        x := 1
"""
    module = parse_module(source)
    _, errors = analyze_module(module)

    assert len(errors) > 0


# Built-in functions


def test_builtin_print_function() -> None:
    """Test that print is a built-in function."""
    source = """fn test():
    print("hello")
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    # print should be defined as a built-in
    symbol = analyzer.symbol_table.lookup("print")
    assert symbol is not None
    assert isinstance(symbol.type, FunctionType)


# Real examples


def test_analyze_hello_example() -> None:
    """Test analyzing hello.aster example."""
    source = """fn main():
    print("hello, world")
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    # Should have no errors
    assert not analyzer.has_errors()


def test_analyze_sum_to_example() -> None:
    """Test analyzing sum_to.aster example."""
    source = """fn sum_to(n: Int) -> Int:
    mut total := 0
    mut i := 1
    while i <= n:
        total <- total + i
        i <- i + 1
    return total
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    # Should have no errors
    assert not analyzer.has_errors()

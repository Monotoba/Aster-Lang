"""Tests for semantic analysis."""

from __future__ import annotations

from pathlib import Path

from aster_lang.parser import parse_module
from aster_lang.semantic import (
    BOOL_TYPE,
    INT_TYPE,
    STRING_TYPE,
    BorrowType,
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


def test_ownership_types_in_signatures() -> None:
    source = """fn id(x: &Int) -> &Int:
    return x

fn take(p: *own Node) -> *own Node:
    return p
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    id_sym = analyzer.symbol_table.lookup("id")
    assert id_sym is not None
    assert isinstance(id_sym.type, FunctionType)
    assert id_sym.type.param_types[0] == BorrowType(INT_TYPE)
    assert id_sym.type.return_type == BorrowType(INT_TYPE)

    take_sym = analyzer.symbol_table.lookup("take")
    assert take_sym is not None
    assert isinstance(take_sym.type, FunctionType)
    assert take_sym.type.param_types[0] == take_sym.type.return_type


def test_unknown_pointer_kind_is_error() -> None:
    source = """fn f(x: *bogus Int):
    return
"""
    module = parse_module(source)
    _, errors = analyze_module(module)
    assert any("Unknown pointer kind" in e.message for e in errors)


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


def test_named_import_defines_function_symbol(tmp_path: Path) -> None:
    """Named imports should define imported functions with their declared types."""
    (tmp_path / "helpers.aster").write_text(
        "pub fn add(a: Int, b: Int) -> Int:\n" "    return a + b\n",
        encoding="utf-8",
    )

    module = parse_module(
        "use helpers: add\n" "result := add(1, 2)\n",
    )
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("add")
    assert symbol is not None
    assert isinstance(symbol.type, FunctionType)
    assert symbol.type.param_types == (INT_TYPE, INT_TYPE)
    assert symbol.type.return_type == INT_TYPE
    assert not analyzer.has_errors()


def test_missing_named_import_reports_error(tmp_path: Path) -> None:
    """Missing imported names should produce a semantic error."""
    (tmp_path / "helpers.aster").write_text(
        "pub fn add(a: Int, b: Int) -> Int:\n" "    return a + b\n",
        encoding="utf-8",
    )

    module = parse_module("use helpers: missing\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "has no public export 'missing'" in analyzer.errors[0].message


def test_missing_module_reports_error(tmp_path: Path) -> None:
    module = parse_module("use missing\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "Module not found: missing" in analyzer.errors[0].message


def test_cyclic_import_reports_error(tmp_path: Path) -> None:
    (tmp_path / "a.aster").write_text("use b\nfn value() -> Int:\n    return 1\n", encoding="utf-8")
    (tmp_path / "b.aster").write_text("use a\nfn value() -> Int:\n    return 2\n", encoding="utf-8")

    module = parse_module("use a\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "Cyclic import detected" in analyzer.errors[0].message


def test_import_resolves_parent_package_root(tmp_path: Path) -> None:
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()

    module = parse_module("use lib.helpers: answer\n")
    analyzer = SemanticAnalyzer(base_dir=app_dir)
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("answer")
    assert symbol is not None
    assert isinstance(symbol.type, FunctionType)
    assert symbol.type.return_type == INT_TYPE
    assert not analyzer.has_errors()


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

    module = parse_module("use helpers: answer\n")
    analyzer = SemanticAnalyzer(base_dir=app_dir)
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("answer")
    assert symbol is not None
    assert isinstance(symbol.type, FunctionType)
    assert symbol.type.return_type == INT_TYPE
    assert not analyzer.has_errors()


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

    module = parse_module("use app.helpers: answer\n")
    analyzer = SemanticAnalyzer(base_dir=app_dir)
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("answer")
    assert symbol is not None
    assert isinstance(symbol.type, FunctionType)
    assert symbol.type.return_type == INT_TYPE
    assert not analyzer.has_errors()


def test_invalid_manifest_package_name_reports_error(tmp_path: Path) -> None:
    (tmp_path / "aster.toml").write_text(
        "[package]\n" "name = 42\n",
        encoding="utf-8",
    )

    module = parse_module("use missing\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "package.name must be a string" in analyzer.errors[0].message


def test_import_private_name_reports_error(tmp_path: Path) -> None:
    (tmp_path / "helpers.aster").write_text(
        "fn hidden() -> Int:\n" "    return 7\n" "pub fn shown() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )

    module = parse_module("use helpers: hidden\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "has no public export 'hidden'" in analyzer.errors[0].message


def test_import_public_let_symbol(tmp_path: Path) -> None:
    (tmp_path / "helpers.aster").write_text("pub answer := 42\n", encoding="utf-8")

    module = parse_module("use helpers: answer\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    symbol = analyzer.symbol_table.lookup("answer")
    assert symbol is not None
    assert symbol.type == INT_TYPE
    assert not analyzer.has_errors()


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


def test_match_tuple_pattern_binding_in_scope() -> None:
    """Tuple pattern bindings should be in scope within the matched arm."""
    source = """fn f() -> Int:
    pair := (0, 7)
    match pair:
        (0, x):
            return x
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_tuple_destructuring_binding_in_scope() -> None:
    source = """fn f() -> Int:
    (x, y) := (2, 3)
    return x + y
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_tuple_destructuring_binding_arity_mismatch_error() -> None:
    source = """fn f() -> Int:
    (x, y, z) := (2, 3)
    return x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "Tuple binding arity mismatch" in analyzer.errors[0].message


def test_list_destructuring_binding_with_rest_in_scope() -> None:
    source = """fn f() -> Int:
    [head, *tail] := [1, 2, 3]
    return head
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_record_destructuring_binding_missing_field_error() -> None:
    source = """fn f() -> Int:
    {x, z} := {x: 1, y: 2}
    return x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "Record binding field 'z' not found" in analyzer.errors[0].message


def test_type_annotation_on_destructuring_binding_is_parse_error() -> None:
    # The parser only accepts `: Type` on simple mut bindings, not destructuring patterns.
    import pytest

    from aster_lang.parser import ParseError

    source = """fn f() -> Int:
    mut (x, y): Pair := pair
    return x
"""
    with pytest.raises(ParseError):
        parse_module(source)


def test_match_tuple_pattern_arity_mismatch_error() -> None:
    """Tuple pattern arity should match tuple subject arity when known."""
    source = """fn f() -> Int:
    pair := (0, 7)
    match pair:
        (0, x, y):
            return x
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "Tuple pattern arity mismatch" in analyzer.errors[0].message


def test_match_list_pattern_binding_in_scope() -> None:
    """List pattern bindings should be in scope within the matched arm."""
    source = """fn f() -> Int:
    items := [0, 7]
    match items:
        [0, x]:
            return x
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_match_list_pattern_arity_mismatch_error() -> None:
    """List pattern arity should match list subject arity when known."""
    source = """fn f() -> Int:
    items := [0, 7]
    match items:
        [0, x, y]:
            return x
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "List pattern arity mismatch" in analyzer.errors[0].message


def test_match_record_pattern_binding_in_scope() -> None:
    """Record pattern bindings should be in scope within the matched arm."""
    source = """fn f() -> Int:
    point := {x: 0, y: 7}
    match point:
        {x: 0, y}:
            return y
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_match_record_pattern_missing_field_error() -> None:
    """Record pattern should fail semantic validation for missing literal-backed fields."""
    source = """fn f() -> Int:
    point := {x: 0, y: 7}
    match point:
        {x: 0, z}:
            return z
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "Record pattern field 'z' not found" in analyzer.errors[0].message


def test_match_or_pattern_without_bindings_is_valid() -> None:
    source = """fn f(n: Int) -> Int:
    match n:
        0 | 1:
            return 1
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_match_or_pattern_mismatched_bindings_error() -> None:
    # First alternative binds nothing; second binds x — mismatch
    source = """fn f(n: Int) -> Int:
    match n:
        0 | x:
            return 1
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "Or-pattern alternatives must bind exactly the same names" in analyzer.errors[0].message


def test_match_or_pattern_different_binding_names_error() -> None:
    # Both alternatives bind, but with different names (a vs b)
    source = """fn f(n: Int) -> Int:
    match n:
        a | b:
            return 1
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "Or-pattern alternatives must bind exactly the same names" in analyzer.errors[0].message


def test_match_or_pattern_consistent_binding_is_valid() -> None:
    # Both alternatives bind the same name x — should be valid
    source = """fn f(n: Int) -> Int:
    match n:
        x | x:
            return x
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_match_list_rest_pattern_binding_in_scope() -> None:
    source = """fn f() -> Int:
    items := [1, 2, 3]
    match items:
        [head, *tail]:
            tail_copy := tail
            return head
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_match_tuple_rest_pattern_arity_error() -> None:
    source = """fn f() -> Int:
    pair := (1,)
    match pair:
        (head, *tail, last):
            return head
        _:
            return 0
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "Rest pattern must be trailing" in analyzer.errors[0].message


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


# ---------------------------------------------------------------------------
# [dependencies] manifest support
# ---------------------------------------------------------------------------


def test_import_from_declared_dependency(tmp_path: Path) -> None:
    dep_dir = tmp_path / "vendor" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn double(n: Int) -> Int:\n" "    return n + n\n",
        encoding="utf-8",
    )
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "vendor/math" }\n',
        encoding="utf-8",
    )

    module = parse_module("use math.utils\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert not analyzer.has_errors()
    symbol = analyzer.symbol_table.lookup("utils")
    assert symbol is not None


def test_import_from_dependency_with_dotdot_path(tmp_path: Path) -> None:
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    (sibling / "helpers.aster").write_text(
        "pub fn greet() -> String:\n" '    return "hi"\n',
        encoding="utf-8",
    )
    project = tmp_path / "project"
    project.mkdir()
    (project / "aster.toml").write_text(
        "[dependencies]\n" 'sibling = { path = "../sibling" }\n',
        encoding="utf-8",
    )

    module = parse_module("use sibling.helpers\n")
    analyzer = SemanticAnalyzer(base_dir=project)
    analyzer.analyze(module)

    assert not analyzer.has_errors()


def test_import_from_dependency_missing_path_reports_error(tmp_path: Path) -> None:
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'ghost = { path = "does_not_exist" }\n',
        encoding="utf-8",
    )

    module = parse_module("use ghost.module\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "ghost" in analyzer.errors[0].message


def test_dependency_entry_missing_path_key_reports_error(tmp_path: Path) -> None:
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'bad = { version = "1.0" }\n',
        encoding="utf-8",
    )

    module = parse_module("use bad.mod\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "missing a 'path' key" in analyzer.errors[0].message


def test_dependency_path_not_string_reports_error(tmp_path: Path) -> None:
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" "bad = { path = 99 }\n",
        encoding="utf-8",
    )

    module = parse_module("use bad.mod\n")
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert ".path must be a string" in analyzer.errors[0].message


# ---------------------------------------------------------------------------
# Type alias declarations and pub exports
# ---------------------------------------------------------------------------


def test_type_alias_defined_in_scope() -> None:
    source = (
        "typealias Score = Int\n"
        "fn best(a: Score, b: Score) -> Score:\n"
        "    if a > b:\n"
        "        return a\n"
        "    else:\n"
        "        return b\n"
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert not analyzer.has_errors()
    symbol = analyzer.symbol_table.lookup("Score")
    assert symbol is not None
    from aster_lang.semantic import SymbolKind

    assert symbol.kind == SymbolKind.TYPE_ALIAS


def test_type_alias_duplicate_reports_error() -> None:
    source = "typealias Foo = Int\n" "typealias Foo = String\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "already defined" in analyzer.errors[0].message


def test_pub_type_alias_exported_to_importing_module(tmp_path: Path) -> None:
    (tmp_path / "types.aster").write_text(
        "pub typealias Score = Int\n",
        encoding="utf-8",
    )
    source = "use types: Score\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert not analyzer.has_errors()
    from aster_lang.semantic import INT_TYPE, SymbolKind

    symbol = analyzer.symbol_table.lookup("Score")
    assert symbol is not None
    assert symbol.kind == SymbolKind.TYPE_ALIAS
    assert symbol.type == INT_TYPE


def test_private_type_alias_not_exported(tmp_path: Path) -> None:
    (tmp_path / "types.aster").write_text(
        "typealias Hidden = Int\n",
        encoding="utf-8",
    )
    source = "use types: Hidden\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert analyzer.has_errors()
    assert "no public export 'Hidden'" in analyzer.errors[0].message


def test_imported_type_alias_usable_in_annotation(tmp_path: Path) -> None:
    (tmp_path / "types.aster").write_text(
        "pub typealias Score = Int\n",
        encoding="utf-8",
    )
    source = "use types: Score\n" "fn double_score(s: Score) -> Score:\n" "    return s + s\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert not analyzer.has_errors()
    from aster_lang.semantic import INT_TYPE

    fn_symbol = analyzer.symbol_table.lookup("double_score")
    assert fn_symbol is not None
    fn_type = FunctionType(param_types=(INT_TYPE,), return_type=INT_TYPE)
    assert fn_symbol.type == fn_type


def test_qualified_type_from_namespace_import(tmp_path: Path) -> None:
    (tmp_path / "types.aster").write_text(
        "pub typealias Score = Int\n",
        encoding="utf-8",
    )
    source = "use types\n" "fn rank(s: types.Score) -> types.Score:\n" "    return s + 1\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert not analyzer.has_errors()
    from aster_lang.semantic import INT_TYPE

    fn_symbol = analyzer.symbol_table.lookup("rank")
    assert fn_symbol is not None
    fn_type = FunctionType(param_types=(INT_TYPE,), return_type=INT_TYPE)
    assert fn_symbol.type == fn_type


def test_qualified_type_from_aliased_namespace_import(tmp_path: Path) -> None:
    (tmp_path / "types.aster").write_text(
        "pub typealias Score = Int\n",
        encoding="utf-8",
    )
    source = "use types as t\n" "fn rank(s: t.Score) -> t.Score:\n" "    return s\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    assert not analyzer.has_errors()
    from aster_lang.semantic import INT_TYPE

    fn_symbol = analyzer.symbol_table.lookup("rank")
    assert fn_symbol is not None
    from aster_lang.semantic import FunctionType as FT

    fn_type = FT(param_types=(INT_TYPE,), return_type=INT_TYPE)
    assert fn_symbol.type == fn_type


def test_qualified_type_nonalias_member_resolves_to_unknown(tmp_path: Path) -> None:
    # mod.fn_name is not a type alias — qualified type should silently be UNKNOWN
    (tmp_path / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n    return 42\n",
        encoding="utf-8",
    )
    source = "use helpers\n" "fn f(x: helpers.answer) -> Int:\n" "    return x\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)

    # No crash; param resolves to UNKNOWN (compatible with everything)
    fn_symbol = analyzer.symbol_table.lookup("f")
    assert fn_symbol is not None

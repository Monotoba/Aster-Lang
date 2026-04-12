"""Tests for semantic analysis."""

from __future__ import annotations

from pathlib import Path

from aster_lang import ast
from aster_lang.parser import parse_module
from aster_lang.semantic import (
    BOOL_TYPE,
    BYTE_TYPE,
    INT_TYPE,
    STRING_TYPE,
    BorrowType,
    FunctionType,
    OwnershipMode,
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


def test_borrow_expression_infers_borrow_type() -> None:
    source = """mut x := 1
y := &mut x
z := &x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    y_sym = analyzer.symbol_table.lookup("y")
    assert y_sym is not None
    assert isinstance(y_sym.type, BorrowType)
    assert y_sym.type.inner == INT_TYPE
    assert y_sym.type.is_mutable is True

    z_sym = analyzer.symbol_table.lookup("z")
    assert z_sym is not None
    assert isinstance(z_sym.type, BorrowType)
    assert z_sym.type.inner == INT_TYPE
    assert z_sym.type.is_mutable is False


def test_nested_borrow_expression_infers_borrow_type() -> None:
    source = """mut r := {inner: {x: 1}}
y := &mut r.inner.x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    y_sym = analyzer.symbol_table.lookup("y")
    assert y_sym is not None
    assert isinstance(y_sym.type, BorrowType)
    assert y_sym.type.inner == INT_TYPE
    assert y_sym.type.is_mutable is True


def test_computed_root_borrow_expression_infers_borrow_type() -> None:
    source = """y := &mut {x: 1}.x
z := &mut [1, 2][0]
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    y_sym = analyzer.symbol_table.lookup("y")
    assert y_sym is not None
    assert isinstance(y_sym.type, BorrowType)
    assert y_sym.type.inner == INT_TYPE
    assert y_sym.type.is_mutable is True

    z_sym = analyzer.symbol_table.lookup("z")
    assert z_sym is not None
    assert isinstance(z_sym.type, BorrowType)
    assert z_sym.type.inner == INT_TYPE
    assert z_sym.type.is_mutable is True


def test_assign_through_mut_borrow_param_does_not_require_mut_binding() -> None:
    source = """fn bump(x: &mut Int):
    x <- x + 1
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_nested_member_and_index_assignment_are_valid_lvalues() -> None:
    source = """fn main():
    mut r := {inner: {x: 1}, items: [1, 2]}
    r.inner.x <- 7
    r.items[0] <- 9
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_computed_member_and_index_assignment_are_valid_lvalues() -> None:
    source = """fn main():
    {x: 1}.x <- 7
    [1, 2][0] <- 9
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_strict_types_rejects_unknown_in_arithmetic() -> None:
    source = """fn main():
    f := x -> x + 1
    print(f(1))
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(strict_types=True)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("unknown type" in e.message for e in analyzer.errors)


def test_strict_types_rejects_unknown_in_comparison() -> None:
    source = """fn main():
    f := x -> x
    y := f(1) == 1
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(strict_types=True)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any(
        ("compare unknown" in e.message or "unknown types" in e.message) for e in analyzer.errors
    )


def test_strict_types_rejects_unknown_if_condition() -> None:
    source = """fn main():
    f := x -> x
    if f(1):
        print(1)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(strict_types=True)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("If condition must be Bool" in e.message for e in analyzer.errors)


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


def test_string_concatenation_type() -> None:
    source = 'x := "a" + "b"\n'
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()
    symbol = analyzer.symbol_table.lookup("x")
    assert symbol is not None
    assert symbol.type == STRING_TYPE


def test_fixed_width_type_in_annotation() -> None:
    source = "x: Byte := 200\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()
    sym = analyzer.symbol_table.lookup("x")
    assert sym is not None
    assert sym.type == BYTE_TYPE


def test_bitwise_operator_type() -> None:
    source = "x := byte(1) & byte(2)\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()
    sym = analyzer.symbol_table.lookup("x")
    assert sym is not None
    assert sym.type == BYTE_TYPE


def test_ownership_mut_borrow_requires_mutable_arg_in_deny_mode() -> None:
    source = """fn bump(x: &mut Int) -> Int:
    return x + 1

fn main():
    x := 1
    bump(x)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()


def test_ownership_mut_borrow_allows_mutable_arg_in_deny_mode() -> None:
    source = """fn bump(x: &mut Int) -> Int:
    return x + 1

fn main():
    mut x := 1
    bump(x)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_ownership_conflicting_mut_borrows_in_same_call_are_error_in_deny_mode() -> None:
    source = """fn f(a: &mut Int, b: &mut Int):
    return

fn main():
    mut x := 1
    f(x, x)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()


def test_ownership_persistent_mut_borrow_blocks_direct_use_in_deny_mode() -> None:
    source = """fn main():
    mut x := 1
    p := &mut x
    y := x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("mutably borrowed" in e.message for e in analyzer.errors)


def test_ownership_persistent_shared_borrow_blocks_assignment_in_deny_mode() -> None:
    source = """fn main():
    mut x := 1
    p := &x
    x <- 2
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("borrowed" in e.message for e in analyzer.errors)


def test_ownership_borrow_released_on_scope_exit() -> None:
    source = """fn main():
    mut x := 1
    if true:
        p := &mut x
        p <- 2
    x <- 3
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_ownership_cannot_return_ref_to_local_in_deny_mode() -> None:
    source = """fn f() -> &Int:
    mut x := 1
    return &x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("return a reference to local" in e.message for e in analyzer.errors)


def test_ownership_can_return_borrow_parameter_in_deny_mode() -> None:
    source = """fn id(x: &Int) -> &Int:
    return x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_ownership_rejects_refs_in_list_literal_in_deny_mode() -> None:
    source = """fn main():
    mut x := 1
    xs := [&x]
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("collection literals" in e.message for e in analyzer.errors)


def test_ownership_rejects_refs_in_record_literal_in_deny_mode() -> None:
    source = """fn main():
    mut x := 1
    r := {p: &x}
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("collection literals" in e.message for e in analyzer.errors)


def test_ownership_cannot_return_ref_to_local_member_in_deny_mode() -> None:
    source = """fn f() -> &Int:
    mut r := {x: 1}
    return &r.x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("return a reference to local" in e.message for e in analyzer.errors)


def test_ownership_mut_borrow_of_member_blocks_use_of_base_in_deny_mode() -> None:
    source = """fn main():
    mut r := {x: 1}
    p := &mut r.x
    y := r
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("mutably borrowed" in e.message for e in analyzer.errors)


def test_ownership_rejects_module_level_member_borrow_binding_in_deny_mode() -> None:
    source = """mut r := {x: 1}
p := &mut r.x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any(
        ("module-level" in e.message or "module-level bindings" in e.message)
        for e in analyzer.errors
    )


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


def test_local_typed_binding_statement_type_checks() -> None:
    source = """fn f():
    x: Int := 1
    return
"""
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


def test_type_alias_type_params_resolve_as_type_variables() -> None:
    source = "typealias Id[T] = T\n" "fn use_id(x: Id[Int]) -> Id[Int]:\n" "    return x\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    from aster_lang.semantic import SymbolKind, TypeKind

    id_sym = analyzer.symbol_table.lookup("Id")
    assert id_sym is not None
    assert id_sym.kind == SymbolKind.TYPE_ALIAS
    assert id_sym.type.kind == TypeKind.TYPEVAR


def test_generic_function_type_params_resolve_as_type_variables() -> None:
    source = "fn id[T](x: T) -> T:\n    return x\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    fn_sym = analyzer.symbol_table.lookup("id")
    assert fn_sym is not None

    from aster_lang.semantic import FunctionType, TypeVarType

    assert fn_sym.type == FunctionType(
        param_types=(TypeVarType("T"),),
        return_type=TypeVarType("T"),
        type_params={"T": ()},
    )


def test_generic_trait_bounds_validate_against_known_traits() -> None:
    source = (
        "trait Show:\n"
        "    fn show(self) -> String\n"
        "fn f[T: Show](x: T) -> Int:\n"
        "    return 0\n"
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_generic_trait_bounds_unknown_trait_reports_error() -> None:
    source = "fn f[T: Missing](x: T) -> Int:\n    return 0\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert "Unknown trait" in analyzer.errors[0].message


def test_generic_trait_bounds_imported_named_trait_is_valid(tmp_path: Path) -> None:
    (tmp_path / "traits.aster").write_text(
        "pub trait Show:\n" "    fn show(self) -> String\n",
        encoding="utf-8",
    )
    source = "use traits: Show\n" "fn f[T: Show](x: T) -> Int:\n" "    return 0\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_generic_trait_bounds_imported_namespace_trait_is_valid(tmp_path: Path) -> None:
    (tmp_path / "traits.aster").write_text(
        "pub trait Show:\n" "    fn show(self) -> String\n",
        encoding="utf-8",
    )
    source = "use traits\n" "fn f[T: traits.Show](x: T) -> Int:\n" "    return 0\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_generic_type_param_bounds_are_recorded() -> None:
    source = (
        "trait Show:\n"
        "    fn show(self) -> String\n"
        "trait Hash:\n"
        "    fn hash(self) -> Int\n"
        "fn f[T: Show + Hash](x: T) -> Int:\n"
        "    return 0\n"
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    fn_decl = module.declarations[2]
    assert isinstance(fn_decl, ast.FunctionDecl)
    assert analyzer.decl_type_params[id(fn_decl)] == {"T": ("Show", "Hash")}


def test_generic_function_call_instantiates_type_vars() -> None:
    source = (
        "fn id[T](x: T) -> T:\n" "    return x\n" "fn main():\n" "    y := id(1)\n" "    print(y)\n"
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    main_decl = module.declarations[1]
    assert isinstance(main_decl, ast.FunctionDecl)
    y_stmt = main_decl.body[0]
    assert isinstance(y_stmt, ast.LetStmt)
    assert analyzer.expr_types[id(y_stmt.initializer)] == INT_TYPE


def test_generic_type_alias_instantiates_type_vars() -> None:
    source = "typealias Id[T] = T\n" "fn f(x: Id[Int]) -> Id[Int]:\n" "    return x\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    fn_sym = analyzer.symbol_table.lookup("f")
    assert fn_sym is not None
    assert fn_sym.type == FunctionType(param_types=(INT_TYPE,), return_type=INT_TYPE)


def test_trait_decl_registers_trait_symbol() -> None:
    source = "trait Show:\n    fn show(self) -> String\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()

    from aster_lang.semantic import SymbolKind

    sym = analyzer.symbol_table.lookup("Show")
    assert sym is not None
    assert sym.kind == SymbolKind.TRAIT


def test_impl_for_unknown_trait_reports_error() -> None:
    source = "impl Missing for Int:\n" "    fn show(self) -> String:\n" '        return "x"\n'
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert "Unknown trait" in analyzer.errors[0].message


def test_impl_for_qualified_imported_trait_is_valid(tmp_path: Path) -> None:
    (tmp_path / "traits.aster").write_text(
        "pub trait Show:\n" "    fn show(self) -> String\n",
        encoding="utf-8",
    )
    source = (
        "use traits\n"
        "impl traits.Show for Int:\n"
        "    fn show(self) -> String:\n"
        '        return "x"\n'
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer(base_dir=tmp_path)
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_impl_missing_required_method_reports_error() -> None:
    source = (
        "trait Show:\n"
        "    fn show(self) -> String\n"
        "impl Show for Int:\n"
        "    fn other(self) -> String:\n"
        '        return "x"\n'
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert "missing required method" in analyzer.errors[-1].message


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


# ---------------------------------------------------------------------------
# *own move-semantics tests
# ---------------------------------------------------------------------------


def test_own_single_move_to_call_is_ok_in_deny_mode() -> None:
    source = """fn take(p: *own Int):
    return

fn main(x: *own Int):
    take(x)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_own_use_after_move_in_call_is_error_in_deny_mode() -> None:
    source = """fn take(p: *own Int):
    return

fn main(x: *own Int):
    take(x)
    take(x)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("moved" in e.message for e in analyzer.errors)


def test_own_double_move_via_binding_is_error_in_deny_mode() -> None:
    source = """fn main(x: *own Int):
    y := x
    z := x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("moved" in e.message for e in analyzer.errors)


def test_own_use_after_move_in_return_is_error_in_deny_mode() -> None:
    source = """fn take(p: *own Int):
    return

fn main(x: *own Int):
    take(x)
    return x
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("moved" in e.message for e in analyzer.errors)


def test_own_move_via_binding_then_safe_use_of_new_owner_is_ok_in_deny_mode() -> None:
    source = """fn take(p: *own Int):
    return

fn main(x: *own Int):
    y := x
    take(y)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_own_duplicate_in_same_call_is_error_in_deny_mode() -> None:
    source = """fn two(a: *own Int, b: *own Int):
    return

fn main(x: *own Int):
    two(x, x)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer(ownership_mode=OwnershipMode.DENY)
    analyzer.analyze(module)
    assert analyzer.has_errors()


# ---------------------------------------------------------------------------
# Trait call-site resolution tests
# ---------------------------------------------------------------------------


def test_impl_correct_method_and_arity_passes() -> None:
    source = (
        "trait Show:\n"
        "    fn show(self) -> String\n"
        "impl Show for Int:\n"
        "    fn show(self) -> String:\n"
        '        return "42"\n'
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_impl_wrong_return_type_reports_error() -> None:
    source = (
        "trait Show:\n"
        "    fn show(self) -> String\n"
        "impl Show for Int:\n"
        "    fn show(self) -> Int:\n"
        "        return 0\n"
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("wrong return type" in e.message for e in analyzer.errors)


def test_impl_wrong_arity_reports_error() -> None:
    source = (
        "trait Compute:\n"
        "    fn run(self, x: Int) -> Int\n"
        "impl Compute for Int:\n"
        "    fn run(self) -> Int:\n"
        "        return 0\n"
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("wrong arity" in e.message for e in analyzer.errors)


def test_impl_extra_method_beyond_required_passes() -> None:
    """Extra methods in impl are allowed (open-world impls)."""
    source = (
        "trait Show:\n"
        "    fn show(self) -> String\n"
        "impl Show for Int:\n"
        "    fn show(self) -> String:\n"
        '        return "x"\n'
        "    fn debug(self) -> String:\n"
        '        return "debug"\n'
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_trait_call_site_resolution_on_bounded_type_var_passes() -> None:
    source = """
trait Show:
    fn show(self) -> String

fn print_it[T: Show](x: T):
    x.show()
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_trait_call_site_resolution_on_bounded_type_var_missing_method_fails() -> None:
    source = """
trait Show:
    fn show(self) -> String

fn print_it[T: Show](x: T):
    x.debug()
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("No method 'debug' found in trait bounds" in e.message for e in analyzer.errors)


def test_trait_call_site_resolution_wrong_arity_fails() -> None:
    source = """
trait Show:
    fn show(self) -> String

fn print_it[T: Show](x: T):
    x.show(1, 2)
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("expects 0 argument(s), got 2" in e.message for e in analyzer.errors)


def test_trait_call_site_resolution_on_concrete_type_passes() -> None:
    source = """
trait Show:
    fn show(self) -> String

impl Show for Int:
    fn show(self) -> String:
        return "42"

fn main():
    x := 42
    x.show()
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_trait_call_site_resolution_on_multiple_bounds_passes() -> None:
    source = """
trait Show:
    fn show(self) -> String
trait Debug:
    fn debug(self) -> String

fn print_it[T: Show + Debug](x: T):
    x.show()
    x.debug()
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_trait_call_site_resolution_ambiguous_method_reports_error() -> None:
    source = """
trait A:
    fn foo(self) -> Int
trait B:
    fn foo(self) -> Int

fn test[T: A + B](x: T):
    x.foo()
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("Ambiguous method 'foo'" in e.message for e in analyzer.errors)


def test_generic_call_checks_trait_bounds_on_inferred_type() -> None:
    source = """
trait Show:
    fn show(self) -> String

fn print_it[T: Show](x: T):
    x.show()

fn main():
    print_it(42) # Int does not impl Show in this snippet
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("does not implement trait" in e.message for e in analyzer.errors)


def test_generic_call_checks_trait_bounds_on_satisfied_impl_passes() -> None:
    source = """
trait Show:
    fn show(self) -> String

impl Show for Int:
    fn show(self) -> String:
        return "42"

fn print_it[T: Show](x: T):
    x.show()

fn main():
    print_it(42) # Int DOES impl Show here
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_trait_self_type_inference_passes() -> None:
    source = """
trait Clone:
    fn clone(self) -> Self

impl Clone for Int:
    fn clone(self) -> Int:
        return 42

fn test[T: Clone](x: T):
    # If Self is working, x.clone() should return T
    y: T := x.clone()
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_trait_self_type_inference_mismatch_fails() -> None:
    source = """
trait Clone:
    fn clone(self) -> Self

impl Clone for Int:
    fn clone(self) -> Int:
        return 42

fn test[T: Clone](x: T):
    # x.clone() returns T, which is not String
    y: String := x.clone()
"""
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("Type mismatch" in e.message for e in analyzer.errors)


# ---------------------------------------------------------------------------
# Effect tracking prototype tests
# ---------------------------------------------------------------------------


def test_effect_decl_registers_effect() -> None:
    source = "effect io\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()
    assert "io" in analyzer._declared_effects


def test_effect_duplicate_decl_reports_error() -> None:
    source = "effect io\neffect io\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("already declared" in e.message for e in analyzer.errors)


def test_function_with_declared_effect_passes() -> None:
    source = "effect io\n" "fn print_line(s: String) !io:\n" "    x := 1\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_function_with_undeclared_effect_reports_error() -> None:
    source = "fn foo() !io:\n    x := 1\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("Unknown effect 'io'" in e.message for e in analyzer.errors)


def test_effect_propagates_to_caller_passes() -> None:
    """Caller that declares the same effect can call an effectful function."""
    source = "effect io\n" "fn write() !io:\n" "    x := 1\n" "fn caller() !io:\n" "    write()\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_effect_propagation_missing_on_caller_reports_error() -> None:
    """Caller without the effect cannot call an effectful function."""
    source = "effect io\n" "fn write() !io:\n" "    x := 1\n" "fn caller():\n" "    write()\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("Effect 'io'" in e.message for e in analyzer.errors)


def test_effect_not_enforced_at_top_level() -> None:
    """Top-level (non-function) calls to effectful functions are unconstrained."""
    source = "effect io\n" "fn write() !io:\n" "    x := 1\n" "result := 0\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_multiple_effects_all_required() -> None:
    source = (
        "effect io\n"
        "effect net\n"
        "fn fetch() !io !net:\n"
        "    x := 1\n"
        "fn caller() !io:\n"
        "    fetch()\n"
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert analyzer.has_errors()
    assert any("Effect 'net'" in e.message for e in analyzer.errors)


def test_multiple_effects_all_declared_on_caller_passes() -> None:
    source = (
        "effect io\n"
        "effect net\n"
        "fn fetch() !io !net:\n"
        "    x := 1\n"
        "fn caller() !io !net:\n"
        "    fetch()\n"
    )
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    assert not analyzer.has_errors()


def test_pub_effect_decl_is_parsed() -> None:
    source = "pub effect io\n"
    module = parse_module(source)
    assert isinstance(module.declarations[0], ast.EffectDecl)
    assert module.declarations[0].name == "io"
    assert module.declarations[0].is_public


def test_effect_on_function_type_carries_effects() -> None:
    source = "effect io\n" "fn write() !io:\n" "    x := 1\n"
    module = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    sym = analyzer.symbol_table.lookup("write")
    assert sym is not None
    assert isinstance(sym.type, FunctionType)
    assert sym.type.effects == ("io",)

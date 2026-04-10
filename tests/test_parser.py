"""Tests for the parser."""

from __future__ import annotations

from aster_lang import ast
from aster_lang.parser import parse_module

# Literals and basic expressions


def test_parse_integer_literal() -> None:
    """Test parsing integer literals."""
    module = parse_module("x := 42\n")
    assert len(module.declarations) == 1
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    assert decl.name == "x"
    assert isinstance(decl.initializer, ast.IntegerLiteral)
    assert decl.initializer.value == 42


def test_parse_string_literal() -> None:
    """Test parsing string literals."""
    module = parse_module('x := "hello"\n')
    assert len(module.declarations) == 1
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    initializer = decl.initializer
    assert isinstance(initializer, ast.StringLiteral)
    assert initializer.value == "hello"


def test_parse_bool_literals() -> None:
    """Test parsing boolean literals."""
    module = parse_module("a := true\nb := false\n")
    assert len(module.declarations) == 2
    decl1 = module.declarations[0]
    decl2 = module.declarations[1]
    assert isinstance(decl1, ast.LetDecl)
    assert isinstance(decl2, ast.LetDecl)
    init1 = decl1.initializer
    init2 = decl2.initializer
    assert isinstance(init1, ast.BoolLiteral)
    assert isinstance(init2, ast.BoolLiteral)
    assert init1.value is True
    assert init2.value is False


def test_parse_nil_literal() -> None:
    """Test parsing nil literal."""
    module = parse_module("x := nil\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    assert isinstance(decl.initializer, ast.NilLiteral)


# Binary expressions


def test_parse_arithmetic_expression() -> None:
    """Test parsing arithmetic expressions."""
    module = parse_module("x := 1 + 2 * 3\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.BinaryExpr)
    assert expr.operator == "+"
    assert isinstance(expr.left, ast.IntegerLiteral)
    assert isinstance(expr.right, ast.BinaryExpr)
    assert expr.right.operator == "*"


def test_parse_comparison_expression() -> None:
    """Test parsing comparison expressions."""
    module = parse_module("x := a < b\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.BinaryExpr)
    assert expr.operator == "<"
    assert isinstance(expr.left, ast.Identifier)
    assert isinstance(expr.right, ast.Identifier)


def test_parse_logical_expression() -> None:
    """Test parsing logical expressions."""
    module = parse_module("x := a and b or c\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.BinaryExpr)
    assert expr.operator == "or"
    assert isinstance(expr.left, ast.BinaryExpr)
    assert expr.left.operator == "and"


# Unary expressions


def test_parse_unary_expression() -> None:
    """Test parsing unary expressions."""
    module = parse_module("x := -5\ny := not z\n")
    decl1 = module.declarations[0]
    assert isinstance(decl1, ast.LetDecl)
    assert isinstance(decl1.initializer, ast.UnaryExpr)
    assert decl1.initializer.operator == "-"
    assert isinstance(decl1.initializer.operand, ast.IntegerLiteral)

    decl2 = module.declarations[1]
    assert isinstance(decl2, ast.LetDecl)
    assert isinstance(decl2.initializer, ast.UnaryExpr)
    assert decl2.initializer.operator == "not"


# Postfix expressions


def test_parse_function_call() -> None:
    """Test parsing function calls."""
    module = parse_module("x := foo(1, 2, 3)\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.CallExpr)
    assert isinstance(expr.func, ast.Identifier)
    assert expr.func.name == "foo"
    assert len(expr.args) == 3


def test_parse_member_access() -> None:
    """Test parsing member access."""
    module = parse_module("x := obj.field\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.MemberExpr)
    assert isinstance(expr.obj, ast.Identifier)
    assert expr.member == "field"


def test_parse_index_expression() -> None:
    """Test parsing index expressions."""
    module = parse_module("x := arr[0]\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.IndexExpr)
    assert isinstance(expr.obj, ast.Identifier)
    assert isinstance(expr.index, ast.IntegerLiteral)


# Collection expressions


def test_parse_list_expression() -> None:
    """Test parsing list expressions."""
    module = parse_module("x := [1, 2, 3]\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.ListExpr)
    assert len(expr.elements) == 3


def test_parse_tuple_expression() -> None:
    """Test parsing tuple expressions."""
    module = parse_module("x := (1, 2, 3)\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.TupleExpr)
    assert len(expr.elements) == 3


def test_parse_record_expression() -> None:
    """Test parsing record expressions."""
    module = parse_module("x := {a: 1, b: 2}\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.RecordExpr)
    assert len(expr.fields) == 2
    assert expr.fields[0].name == "a"
    assert expr.fields[1].name == "b"


# Declarations


def test_parse_let_declaration() -> None:
    """Test parsing let declarations."""
    module = parse_module("x := 1\nmut y := 2\n")
    assert len(module.declarations) == 2
    decl1 = module.declarations[0]
    decl2 = module.declarations[1]
    assert isinstance(decl1, ast.LetDecl)
    assert isinstance(decl2, ast.LetDecl)
    assert decl1.name == "x"
    assert not decl1.is_mutable
    assert decl2.is_mutable


def test_parse_function_declaration() -> None:
    """Test parsing function declarations."""
    source = """fn add(a: Int, b: Int) -> Int:
    return a + b
"""
    module = parse_module(source)
    assert len(module.declarations) == 1
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    assert func.name == "add"
    assert len(func.params) == 2
    assert func.params[0].name == "a"
    assert func.params[1].name == "b"
    assert func.return_type is not None
    assert len(func.body) == 1


def test_parse_import_declaration() -> None:
    """Test parsing import declarations."""
    module = parse_module("use std.io\nuse std.math: sin, cos\n")
    assert len(module.declarations) == 2
    decl1 = module.declarations[0]
    decl2 = module.declarations[1]
    assert isinstance(decl1, ast.ImportDecl)
    assert isinstance(decl2, ast.ImportDecl)
    assert isinstance(decl1.module, ast.QualifiedName)
    assert decl1.module.parts == ["std", "io"]
    assert decl2.imports == ["sin", "cos"]


# Statements


def test_parse_let_statement() -> None:
    """Test parsing let statements in functions."""
    source = """fn test():
    x := 1
    mut y := 2
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    assert len(func.body) == 2
    stmt1 = func.body[0]
    stmt2 = func.body[1]
    assert isinstance(stmt1, ast.LetStmt)
    assert isinstance(stmt2, ast.LetStmt)
    assert stmt1.name == "x"
    assert not stmt1.is_mutable
    assert stmt2.is_mutable


def test_parse_assignment_statement() -> None:
    """Test parsing assignment statements."""
    source = """fn test():
    x <- 42
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    stmt = func.body[0]
    assert isinstance(stmt, ast.AssignStmt)
    assert isinstance(stmt.target, ast.Identifier)
    assert isinstance(stmt.value, ast.IntegerLiteral)


def test_parse_return_statement() -> None:
    """Test parsing return statements."""
    source = """fn test():
    return 42
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    stmt = func.body[0]
    assert isinstance(stmt, ast.ReturnStmt)
    assert stmt.value is not None
    assert isinstance(stmt.value, ast.IntegerLiteral)


def test_parse_if_statement() -> None:
    """Test parsing if statements."""
    source = """fn test():
    if x:
        y := 1
    else:
        y := 2
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    stmt = func.body[0]
    assert isinstance(stmt, ast.IfStmt)
    assert isinstance(stmt.condition, ast.Identifier)
    assert len(stmt.then_block) == 1
    assert stmt.else_block is not None
    assert len(stmt.else_block) == 1


def test_parse_while_statement() -> None:
    """Test parsing while statements."""
    source = """fn test():
    while x < 10:
        x <- x + 1
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    stmt = func.body[0]
    assert isinstance(stmt, ast.WhileStmt)
    assert isinstance(stmt.condition, ast.BinaryExpr)
    assert len(stmt.body) == 1


def test_parse_for_statement() -> None:
    """Test parsing for statements."""
    source = """fn test():
    for i in items:
        print(i)
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    stmt = func.body[0]
    assert isinstance(stmt, ast.ForStmt)
    assert stmt.variable == "i"
    assert isinstance(stmt.iterable, ast.Identifier)
    assert len(stmt.body) == 1


def test_parse_break_continue() -> None:
    """Test parsing break and continue statements."""
    source = """fn test():
    while true:
        break
        continue
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    loop = func.body[0]
    assert isinstance(loop, ast.WhileStmt)
    assert isinstance(loop.body[0], ast.BreakStmt)
    assert isinstance(loop.body[1], ast.ContinueStmt)


# Real examples


def test_parse_hello_example() -> None:
    """Test parsing hello.aster example."""
    source = """fn main():
    print("hello, world")
"""
    module = parse_module(source)
    assert len(module.declarations) == 1
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    assert func.name == "main"
    assert len(func.body) == 1


def test_parse_sum_to_example() -> None:
    """Test parsing sum_to.aster example."""
    source = """fn sum_to(n: Int) -> Int:
    mut total := 0
    mut i := 1
    while i <= n:
        total <- total + i
        i <- i + 1
    return total
"""
    module = parse_module(source)
    assert len(module.declarations) == 1
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    assert func.name == "sum_to"
    assert len(func.params) == 1
    assert func.return_type is not None
    assert len(func.body) == 4  # two lets, while, return


# Match statement


def test_parse_match_literal_arms() -> None:
    src = (
        "fn f():\n"
        "    match x:\n"
        "        0: return 1\n"
        "        1: return 2\n"
        "        _: return 3\n"
    )
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    assert len(match_stmt.arms) == 3
    assert isinstance(match_stmt.arms[0].pattern, ast.LiteralPattern)
    assert isinstance(match_stmt.arms[2].pattern, ast.WildcardPattern)


def test_parse_match_block_arms() -> None:
    src = (
        "fn classify(n: Int) -> String:\n"
        "    match n:\n"
        "        0:\n"
        '            return "zero"\n'
        "        _:\n"
        '            return "many"\n'
    )
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    assert len(match_stmt.arms) == 2
    arm0 = match_stmt.arms[0]
    assert isinstance(arm0.pattern, ast.LiteralPattern)
    assert isinstance(arm0.body[0], ast.ReturnStmt)


def test_parse_match_binding_pattern() -> None:
    src = "fn f():\n" "    match x:\n" "        n: return n\n"
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    assert isinstance(match_stmt.arms[0].pattern, ast.BindingPattern)
    assert match_stmt.arms[0].pattern.name == "n"


def test_parse_match_string_pattern() -> None:
    src = "fn f():\n" "    match s:\n" '        "hi": return 1\n' "        _: return 0\n"
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    assert isinstance(match_stmt.arms[0].pattern, ast.LiteralPattern)

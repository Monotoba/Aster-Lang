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


def test_parse_public_let_decl() -> None:
    module = parse_module("pub answer := 42\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    assert decl.name == "answer"
    assert decl.is_public is True


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


def test_parse_bitwise_precedence_and_over_or() -> None:
    module = parse_module("x := 1 | 2 & 3\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.BinaryExpr)
    assert expr.operator == "|"
    assert isinstance(expr.right, ast.BinaryExpr)
    assert expr.right.operator == "&"


def test_parse_shift_precedence_vs_additive() -> None:
    module = parse_module("x := 1 + 2 << 3\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    expr = decl.initializer
    assert isinstance(expr, ast.BinaryExpr)
    assert expr.operator == "<<"
    assert isinstance(expr.left, ast.BinaryExpr)
    assert expr.left.operator == "+"


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

    module2 = parse_module("x := *p\n")
    decl3 = module2.declarations[0]
    assert isinstance(decl3, ast.LetDecl)
    assert isinstance(decl3.initializer, ast.UnaryExpr)
    assert decl3.initializer.operator == "*"
    assert isinstance(decl3.initializer.operand, ast.Identifier)


def test_parse_borrow_expression() -> None:
    module = parse_module("x := &a\ny := &mut b\n")
    decl1 = module.declarations[0]
    assert isinstance(decl1, ast.LetDecl)
    assert isinstance(decl1.initializer, ast.BorrowExpr)
    assert isinstance(decl1.initializer.target, ast.Identifier)
    assert decl1.initializer.target.name == "a"
    assert decl1.initializer.is_mutable is False

    decl2 = module.declarations[1]
    assert isinstance(decl2, ast.LetDecl)
    assert isinstance(decl2.initializer, ast.BorrowExpr)
    assert isinstance(decl2.initializer.target, ast.Identifier)
    assert decl2.initializer.target.name == "b"
    assert decl2.initializer.is_mutable is True

    module2 = parse_module("x := &r.x\ny := &mut xs[0]\n")
    d1 = module2.declarations[0]
    assert isinstance(d1, ast.LetDecl)
    assert isinstance(d1.initializer, ast.BorrowExpr)
    assert isinstance(d1.initializer.target, ast.MemberExpr)
    assert isinstance(d1.initializer.target.obj, ast.Identifier)
    assert d1.initializer.target.obj.name == "r"
    assert d1.initializer.target.member == "x"

    d2 = module2.declarations[1]
    assert isinstance(d2, ast.LetDecl)
    assert isinstance(d2.initializer, ast.BorrowExpr)
    assert isinstance(d2.initializer.target, ast.IndexExpr)
    assert isinstance(d2.initializer.target.obj, ast.Identifier)
    assert d2.initializer.target.obj.name == "xs"

    module3 = parse_module("x := &mut {value: 1}.value\ny := &mut [1, 2][0]\n")
    d3 = module3.declarations[0]
    assert isinstance(d3, ast.LetDecl)
    assert isinstance(d3.initializer, ast.BorrowExpr)
    assert isinstance(d3.initializer.target, ast.MemberExpr)
    assert isinstance(d3.initializer.target.obj, ast.RecordExpr)

    d4 = module3.declarations[1]
    assert isinstance(d4, ast.LetDecl)
    assert isinstance(d4.initializer, ast.BorrowExpr)
    assert isinstance(d4.initializer.target, ast.IndexExpr)
    assert isinstance(d4.initializer.target.obj, ast.ListExpr)


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


def test_parse_binding_declaration() -> None:
    """Test parsing top-level binding declarations."""
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


def test_parse_generic_function_declaration() -> None:
    source = """fn id[T](x: T) -> T:
    return x
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    assert func.name == "id"
    assert len(func.type_params) == 1
    assert func.type_params[0].name == "T"
    assert func.type_params[0].bounds == []
    assert isinstance(func.params[0].type_annotation, ast.SimpleType)
    assert func.params[0].type_annotation.name.parts == ["T"]


def test_parse_type_param_bounds() -> None:
    source = """fn f[T: Show + Hash](x: T) -> Int:
    return 0
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    assert len(func.type_params) == 1
    tp = func.type_params[0]
    assert tp.name == "T"
    assert len(tp.bounds) == 2
    assert isinstance(tp.bounds[0], ast.SimpleType)
    assert tp.bounds[0].name.parts == ["Show"]
    assert isinstance(tp.bounds[1], ast.SimpleType)
    assert tp.bounds[1].name.parts == ["Hash"]


def test_parse_ownership_type_annotations() -> None:
    """Test parsing ownership and reference type annotations."""
    source = """fn f(a: &Int, b: &mut String, c: *own Node, d: *shared Graph) -> &Int:
    return a
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)

    a_ty = func.params[0].type_annotation
    assert isinstance(a_ty, ast.BorrowTypeExpr)
    assert a_ty.is_mutable is False
    assert isinstance(a_ty.inner, ast.SimpleType)
    assert a_ty.inner.name.parts == ["Int"]

    b_ty = func.params[1].type_annotation
    assert isinstance(b_ty, ast.BorrowTypeExpr)
    assert b_ty.is_mutable is True
    assert isinstance(b_ty.inner, ast.SimpleType)
    assert b_ty.inner.name.parts == ["String"]

    c_ty = func.params[2].type_annotation
    assert isinstance(c_ty, ast.PointerTypeExpr)
    assert c_ty.pointer_kind == "own"
    assert isinstance(c_ty.inner, ast.SimpleType)
    assert c_ty.inner.name.parts == ["Node"]

    d_ty = func.params[3].type_annotation
    assert isinstance(d_ty, ast.PointerTypeExpr)
    assert d_ty.pointer_kind == "shared"
    assert isinstance(d_ty.inner, ast.SimpleType)
    assert d_ty.inner.name.parts == ["Graph"]


def test_parse_lambda_single_param_expression_body() -> None:
    module = parse_module("inc := x -> x + 1\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    assert decl.name == "inc"
    lam = decl.initializer
    assert isinstance(lam, ast.LambdaExpr)
    assert [p.name for p in lam.params] == ["x"]
    assert isinstance(lam.body, ast.BinaryExpr)
    assert lam.body.operator == "+"


def test_parse_lambda_paren_params_expression_body() -> None:
    module = parse_module("add := (a, b: Int) -> a + b\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    lam = decl.initializer
    assert isinstance(lam, ast.LambdaExpr)
    assert [p.name for p in lam.params] == ["a", "b"]
    assert lam.params[1].type_annotation is not None
    assert isinstance(lam.body, ast.BinaryExpr)


def test_parse_lambda_block_body() -> None:
    module = parse_module("inc := (x) -> :\n" "    return x + 1\n")
    decl = module.declarations[0]
    assert isinstance(decl, ast.LetDecl)
    lam = decl.initializer
    assert isinstance(lam, ast.LambdaExpr)
    assert [p.name for p in lam.params] == ["x"]
    assert isinstance(lam.body, list)
    assert len(lam.body) == 1
    assert isinstance(lam.body[0], ast.ReturnStmt)


def test_parse_fn_type_expr() -> None:
    """Test parsing Fn(...) -> ... type expressions."""
    source = """fn apply(f: Fn(Int) -> Int, x: Int) -> Int:
    return f(x)
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    f_ty = func.params[0].type_annotation
    assert isinstance(f_ty, ast.FunctionType)
    assert len(f_ty.param_types) == 1
    assert isinstance(f_ty.param_types[0], ast.SimpleType)
    assert f_ty.param_types[0].name.parts == ["Int"]
    assert isinstance(f_ty.return_type, ast.SimpleType)
    assert f_ty.return_type.name.parts == ["Int"]


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


def test_parse_binding_statement() -> None:
    """Test parsing binding statements in functions."""
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


def test_parse_typed_binding_statement() -> None:
    source = """fn test():
    x: Int := 1
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    assert len(func.body) == 1
    stmt = func.body[0]
    assert isinstance(stmt, ast.LetStmt)
    assert stmt.name == "x"
    assert stmt.is_mutable is False
    assert stmt.type_annotation is not None
    assert isinstance(stmt.type_annotation, ast.SimpleType)
    assert stmt.type_annotation.name.parts == ["Int"]


def test_parse_tuple_destructuring_binding_statement() -> None:
    source = """fn test():
    (x, y) := pair
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    stmt = func.body[0]
    assert isinstance(stmt, ast.LetStmt)
    assert isinstance(stmt.pattern, ast.TuplePattern)
    assert len(stmt.pattern.elements) == 2
    assert isinstance(stmt.pattern.elements[0], ast.BindingPattern)
    assert isinstance(stmt.pattern.elements[1], ast.BindingPattern)


def test_parse_list_destructuring_binding_statement() -> None:
    source = """fn test():
    [head, *tail] := items
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    stmt = func.body[0]
    assert isinstance(stmt, ast.LetStmt)
    assert isinstance(stmt.pattern, ast.ListPattern)
    assert len(stmt.pattern.elements) == 2
    assert isinstance(stmt.pattern.elements[0], ast.BindingPattern)
    assert isinstance(stmt.pattern.elements[1], ast.RestPattern)


def test_parse_record_destructuring_binding_statement() -> None:
    source = """fn test():
    {x, y} := point
"""
    module = parse_module(source)
    func = module.declarations[0]
    assert isinstance(func, ast.FunctionDecl)
    stmt = func.body[0]
    assert isinstance(stmt, ast.LetStmt)
    assert isinstance(stmt.pattern, ast.RecordPattern)
    assert [field.name for field in stmt.pattern.fields] == ["x", "y"]


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


def test_parse_match_tuple_pattern() -> None:
    src = "fn f():\n" "    match pair:\n" "        (0, x): return x\n" "        _: return 0\n"
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    tuple_pattern = match_stmt.arms[0].pattern
    assert isinstance(tuple_pattern, ast.TuplePattern)
    assert len(tuple_pattern.elements) == 2
    assert isinstance(tuple_pattern.elements[0], ast.LiteralPattern)
    assert isinstance(tuple_pattern.elements[1], ast.BindingPattern)


def test_parse_match_list_pattern() -> None:
    src = "fn f():\n" "    match items:\n" "        [0, x]: return x\n" "        _: return 0\n"
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    list_pattern = match_stmt.arms[0].pattern
    assert isinstance(list_pattern, ast.ListPattern)
    assert len(list_pattern.elements) == 2
    assert isinstance(list_pattern.elements[0], ast.LiteralPattern)
    assert isinstance(list_pattern.elements[1], ast.BindingPattern)


def test_parse_match_record_pattern() -> None:
    src = "fn f():\n" "    match point:\n" "        {x: 0, y}: return y\n" "        _: return 0\n"
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    record_pattern = match_stmt.arms[0].pattern
    assert isinstance(record_pattern, ast.RecordPattern)
    assert len(record_pattern.fields) == 2
    assert record_pattern.fields[0].name == "x"
    assert isinstance(record_pattern.fields[0].pattern, ast.LiteralPattern)
    assert record_pattern.fields[1].name == "y"
    assert isinstance(record_pattern.fields[1].pattern, ast.BindingPattern)


def test_parse_match_or_pattern() -> None:
    src = "fn f():\n" "    match value:\n" "        0 | 1: return 1\n" "        _: return 0\n"
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    or_pattern = match_stmt.arms[0].pattern
    assert isinstance(or_pattern, ast.OrPattern)
    assert len(or_pattern.alternatives) == 2
    assert isinstance(or_pattern.alternatives[0], ast.LiteralPattern)
    assert isinstance(or_pattern.alternatives[1], ast.LiteralPattern)


def test_parse_match_list_rest_pattern() -> None:
    src = (
        "fn f():\n"
        "    match items:\n"
        "        [head, *tail]: return head\n"
        "        _: return 0\n"
    )
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    list_pattern = match_stmt.arms[0].pattern
    assert isinstance(list_pattern, ast.ListPattern)
    assert len(list_pattern.elements) == 2
    assert isinstance(list_pattern.elements[0], ast.BindingPattern)
    assert isinstance(list_pattern.elements[1], ast.RestPattern)
    assert list_pattern.elements[1].name == "tail"


def test_parse_match_tuple_rest_pattern() -> None:
    src = (
        "fn f():\n"
        "    match value:\n"
        "        (head, *tail): return head\n"
        "        _: return 0\n"
    )
    module = parse_module(src)
    fn = module.declarations[0]
    assert isinstance(fn, ast.FunctionDecl)
    match_stmt = fn.body[0]
    assert isinstance(match_stmt, ast.MatchStmt)
    tuple_pattern = match_stmt.arms[0].pattern
    assert isinstance(tuple_pattern, ast.TuplePattern)
    assert len(tuple_pattern.elements) == 2
    assert isinstance(tuple_pattern.elements[0], ast.BindingPattern)
    assert isinstance(tuple_pattern.elements[1], ast.RestPattern)
    assert tuple_pattern.elements[1].name == "tail"


def test_parse_trait_decl_with_method_signature() -> None:
    src = "trait Show:\n    fn show(self) -> String\n"
    module = parse_module(src)
    decl = module.declarations[0]
    assert isinstance(decl, ast.TraitDecl)
    assert decl.name == "Show"
    assert decl.type_params == []
    assert len(decl.members) == 1
    sig = decl.members[0]
    assert isinstance(sig, ast.FunctionSig)
    assert sig.name == "show"
    assert len(sig.params) == 1
    assert sig.return_type is not None


def test_parse_impl_decl_inherent_method() -> None:
    src = "impl Int:\n" "    fn show(self) -> String:\n" '        return "Int"\n'
    module = parse_module(src)
    decl = module.declarations[0]
    assert isinstance(decl, ast.ImplDecl)
    assert decl.trait is None
    assert isinstance(decl.target, ast.SimpleType)
    assert decl.target.name.parts == ["Int"]
    assert len(decl.members) == 1
    assert isinstance(decl.members[0], ast.FunctionDecl)


def test_parse_impl_decl_for_trait() -> None:
    src = "impl Show for Int:\n" "    fn show(self) -> String:\n" '        return "Int"\n'
    module = parse_module(src)
    decl = module.declarations[0]
    assert isinstance(decl, ast.ImplDecl)
    assert decl.trait is not None
    assert isinstance(decl.trait, ast.SimpleType)
    assert decl.trait.name.parts == ["Show"]
    assert isinstance(decl.target, ast.SimpleType)
    assert decl.target.name.parts == ["Int"]

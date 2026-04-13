from __future__ import annotations

from aster_lang.hir import (
    HClosure,
    HFunction,
    HLet,
    HMatch,
    HModule,
    HReturn,
    dump_hir,
    lower_module,
)
from aster_lang.parser import parse_module
from aster_lang.semantic import SemanticAnalyzer


def _lower(src: str) -> HModule:
    module = parse_module(src)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    return lower_module(module, analyzer)


# ---------------------------------------------------------------------------
# dump_hir smoke tests (pre-existing, kept)
# ---------------------------------------------------------------------------


def test_dump_hir_includes_expression_types() -> None:
    module = parse_module("fn add(a: Int, b: Int) -> Int:\n    return a + b\n")
    analyzer = SemanticAnalyzer()
    assert analyzer.analyze(module)
    text = dump_hir(module, analyzer)
    assert "return a + b" in text
    assert "# Int" in text


def test_dump_hir_emits_ownership_warnings_as_types() -> None:
    module = parse_module("fn f(x: &mut Int) -> *raw Int:\n    return x\n")
    analyzer = SemanticAnalyzer()
    assert analyzer.analyze(module)
    text = dump_hir(module, analyzer)
    assert "&mut Int" in text
    assert "*raw Int" in text


# ---------------------------------------------------------------------------
# lower_module: basic structure
# ---------------------------------------------------------------------------


def test_lower_empty_module() -> None:
    hmod = _lower("")
    assert hmod.decls == ()
    assert hmod.lifted_fns == {}


def test_lower_simple_function() -> None:
    hmod = _lower("fn add(a: Int, b: Int) -> Int:\n    return a + b\n")
    assert len(hmod.decls) == 1
    fn = hmod.decls[0]
    assert isinstance(fn, HFunction)
    assert fn.name == "add"
    assert fn.params == ("a", "b")
    assert len(fn.body) == 1
    assert isinstance(fn.body[0], HReturn)


def test_lower_function_with_effects() -> None:
    src = "effect Io\nfn greet() -> Int !Io:\n    return 0\n"
    hmod = _lower(src)
    fns = [d for d in hmod.decls if isinstance(d, HFunction)]
    assert len(fns) == 1
    assert fns[0].effects == ("Io",)


# ---------------------------------------------------------------------------
# Destructuring let desugar
# ---------------------------------------------------------------------------


def test_desugar_tuple_let() -> None:
    # Uses destructuring let syntax: (a, b) := pair
    src = "fn f():\n    (a, b) := pair\n    return a\n"
    hmod = _lower(src)
    fn = hmod.decls[0]
    assert isinstance(fn, HFunction)
    stmts = fn.body
    # First stmt should be HLet for the tmp
    assert isinstance(stmts[0], HLet)
    assert stmts[0].name.startswith("__hir_tmp")
    # Then HLets for a and b
    user_lets = [s for s in stmts if isinstance(s, HLet) and not s.name.startswith("__hir_tmp")]
    names = {s.name for s in user_lets}
    assert names == {"a", "b"}


def test_desugar_list_let() -> None:
    src = "fn f():\n    [x, y] := items\n    return x\n"
    hmod = _lower(src)
    fn = hmod.decls[0]
    assert isinstance(fn, HFunction)
    lets = [s for s in fn.body if isinstance(s, HLet)]
    assert any(s.name == "x" for s in lets)
    assert any(s.name == "y" for s in lets)


def test_desugar_nested_tuple_let() -> None:
    src = "fn f():\n    (a, (b, c)) := triple\n    return a\n"
    hmod = _lower(src)
    fn = hmod.decls[0]
    assert isinstance(fn, HFunction)
    lets = [s for s in fn.body if isinstance(s, HLet)]
    user_names = {s.name for s in lets if not s.name.startswith("__hir_tmp")}
    assert user_names == {"a", "b", "c"}


def test_desugar_rest_pattern() -> None:
    src = "fn f():\n    [head, *tail] := items\n    return head\n"
    hmod = _lower(src)
    fn = hmod.decls[0]
    assert isinstance(fn, HFunction)
    lets = [s for s in fn.body if isinstance(s, HLet)]
    user_names = {s.name for s in lets if not s.name.startswith("__hir_tmp")}
    assert "head" in user_names
    assert "tail" in user_names


def test_desugar_record_let() -> None:
    # {x, y} := point
    src = "fn f():\n    {x, y} := point\n    return x\n"
    hmod = _lower(src)
    fn = hmod.decls[0]
    assert isinstance(fn, HFunction)
    lets = [s for s in fn.body if isinstance(s, HLet)]
    user_names = {s.name for s in lets if not s.name.startswith("__hir_tmp")}
    assert user_names == {"x", "y"}


# ---------------------------------------------------------------------------
# Lambda lifting
# ---------------------------------------------------------------------------


def test_lambda_is_lifted() -> None:
    # Lambda syntax: g := x -> x + 1
    src = "fn f():\n    g := x -> x\n    return g\n"
    hmod = _lower(src)
    assert len(hmod.lifted_fns) == 1
    lifted = next(iter(hmod.lifted_fns.values()))
    assert isinstance(lifted, HFunction)
    assert lifted.name.startswith("__lambda")


def test_lambda_replaced_with_closure() -> None:
    src = "fn f():\n    g := x -> x\n    return g\n"
    hmod = _lower(src)
    fn = hmod.decls[0]
    assert isinstance(fn, HFunction)
    lets = [s for s in fn.body if isinstance(s, HLet)]
    g_let = next(s for s in lets if s.name == "g")
    assert isinstance(g_let.init, HClosure)


def test_lambda_free_var_captured() -> None:
    src = "fn f(n: Int):\n    g := x -> x + n\n    return g\n"
    hmod = _lower(src)
    assert len(hmod.lifted_fns) == 1
    lifted = next(iter(hmod.lifted_fns.values()))
    assert "n" in lifted.free_vars


def test_lambda_no_free_vars_when_closed() -> None:
    src = "fn f():\n    g := x -> x\n    return g\n"
    hmod = _lower(src)
    lifted = next(iter(hmod.lifted_fns.values()))
    assert lifted.free_vars == ()


# ---------------------------------------------------------------------------
# Control flow preserved in HIR
# ---------------------------------------------------------------------------


def test_match_stmt_preserved() -> None:
    src = "fn describe(n: Int) -> Int:\n    match n:\n        0: return 0\n        _: return 1\n"
    hmod = _lower(src)
    fn = hmod.decls[0]
    assert isinstance(fn, HFunction)
    match_stmts = [s for s in fn.body if isinstance(s, HMatch)]
    assert len(match_stmts) == 1
    assert len(match_stmts[0].arms) == 2


# ---------------------------------------------------------------------------
# dump_hir output format
# ---------------------------------------------------------------------------


def test_dump_hir_shows_function_signature() -> None:
    module = parse_module("fn inc(x: Int) -> Int:\n    return x\n")
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    text = dump_hir(module, analyzer)
    assert "fn inc(" in text
    assert "-> Int" in text


def test_dump_hir_shows_let_binding() -> None:
    src = "fn f() -> Int:\n    x := 1\n    return x\n"
    module = parse_module(src)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    text = dump_hir(module, analyzer)
    assert "x :=" in text


def test_dump_hir_shows_lifted_lambda() -> None:
    src = "fn f():\n    g := x -> x\n    return g\n"
    module = parse_module(src)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    text = dump_hir(module, analyzer)
    assert "# lambda fn" in text
    assert "__lambda" in text

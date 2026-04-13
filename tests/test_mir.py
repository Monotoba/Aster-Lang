from __future__ import annotations

from aster_lang.hir import HModule, lower_module
from aster_lang.mir import (
    MFunction,
    MIf,
    MLet,
    MModule,
    MReturn,
    MWhile,
    dump_mir,
    lower_hir,
)
from aster_lang.parser import parse_module
from aster_lang.semantic import SemanticAnalyzer


def _lower(src: str) -> MModule:
    module = parse_module(src)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    hmod = lower_module(module, analyzer)
    return lower_hir(hmod)


def _hmod(src: str) -> HModule:
    module = parse_module(src)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    return lower_module(module, analyzer)


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


def test_lower_empty_module() -> None:
    mmod = _lower("")
    assert mmod.decls == ()
    assert mmod.lifted_fns == {}


def test_lower_simple_function() -> None:
    mmod = _lower("fn add(a: Int, b: Int) -> Int:\n    return a + b\n")
    assert len(mmod.decls) == 1
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)
    assert fn.name == "add"
    assert fn.params == ("a", "b")
    assert len(fn.body) == 1
    assert isinstance(fn.body[0], MReturn)


def test_lower_carries_effects() -> None:
    src = "effect Io\nfn greet() -> Int !Io:\n    return 0\n"
    mmod = _lower(src)
    fns = [d for d in mmod.decls if isinstance(d, MFunction)]
    assert len(fns) == 1
    assert fns[0].effects == ("Io",)


def test_lower_lifts_lambdas() -> None:
    src = "fn f():\n    g := x -> x\n    return g\n"
    mmod = _lower(src)
    assert len(mmod.lifted_fns) == 1
    lifted = next(iter(mmod.lifted_fns.values()))
    assert isinstance(lifted, MFunction)
    assert lifted.name.startswith("__lambda")


# ---------------------------------------------------------------------------
# No HMatch / HFor in output
# ---------------------------------------------------------------------------


def test_no_hmatch_in_output() -> None:
    from aster_lang.hir import HMatch

    src = "fn f(n: Int) -> Int:\n    match n:\n        0: return 0\n        _: return 1\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)

    def has_hmatch(stmts: object) -> bool:
        if isinstance(stmts, tuple):
            for s in stmts:
                if isinstance(s, HMatch):
                    return True
                if isinstance(s, MIf) and (
                    has_hmatch(s.then_body) or has_hmatch(s.else_body or ())
                ):
                    return True
        return False

    assert not has_hmatch(fn.body)


def test_no_hfor_in_output() -> None:
    from aster_lang.hir import HFor

    src = "fn f():\n    for x in items:\n        return x\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)

    def has_hfor(stmts: tuple) -> bool:  # type: ignore[type-arg]
        for s in stmts:
            if isinstance(s, HFor):
                return True
            if isinstance(s, MWhile) and has_hfor(s.body):
                return True
            if isinstance(s, MIf) and (has_hfor(s.then_body) or has_hfor(s.else_body or ())):
                return True
        return False

    assert not has_hfor(fn.body)


# ---------------------------------------------------------------------------
# Match desugaring
# ---------------------------------------------------------------------------


def test_match_wildcard_arm_is_unconditional() -> None:
    src = "fn f(n: Int) -> Int:\n    match n:\n        _: return 1\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)
    # Wildcard arm has no condition — emits MLet (subj_tmp) + MReturn directly
    returns = [s for s in fn.body if isinstance(s, MReturn)]
    assert len(returns) == 1


def test_match_literal_arm_becomes_mif() -> None:
    src = "fn f(n: Int) -> Int:\n    match n:\n        0: return 0\n        _: return 1\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)
    mifs = [s for s in fn.body if isinstance(s, MIf)]
    assert len(mifs) == 1
    # The else branch handles the wildcard
    assert mifs[0].else_body is not None


def test_match_binding_arm_emits_let() -> None:
    src = "fn f(n: Int) -> Int:\n    match n:\n        x: return x\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)
    # Binding arm is unconditional — find MLet for 'x'
    user_lets = [s for s in fn.body if isinstance(s, MLet) and s.name == "x"]
    assert len(user_lets) == 1


def test_match_tuple_pattern_desugared() -> None:
    src = "fn f():\n    match pair:\n        (a, b): return a\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)
    # Should produce an MIf for the arity check
    mifs = [s for s in fn.body if isinstance(s, MIf)]
    assert len(mifs) == 1


def test_match_or_pattern_desugared() -> None:
    src = "fn f(n: Int) -> Int:\n    match n:\n        0 | 1: return 0\n        _: return 1\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)
    mifs = [s for s in fn.body if isinstance(s, MIf)]
    assert len(mifs) >= 1


# ---------------------------------------------------------------------------
# For-loop desugaring
# ---------------------------------------------------------------------------


def test_for_becomes_while() -> None:
    src = "fn f():\n    for x in items:\n        return x\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)
    whiles = [s for s in fn.body if isinstance(s, MWhile)]
    assert len(whiles) == 1


def test_for_iter_init_let_emitted() -> None:
    src = "fn f():\n    for x in items:\n        return x\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)
    # First let should bind __iter_init(...)
    iter_lets = [s for s in fn.body if isinstance(s, MLet) and s.name.startswith("__mir_tmp")]
    assert len(iter_lets) >= 1


def test_for_loop_var_bound_inside_while() -> None:
    src = "fn f():\n    for x in items:\n        return x\n"
    mmod = _lower(src)
    fn = mmod.decls[0]
    assert isinstance(fn, MFunction)
    while_stmt = next(s for s in fn.body if isinstance(s, MWhile))
    # First stmt in while body should bind x
    assert isinstance(while_stmt.body[0], MLet)
    assert while_stmt.body[0].name == "x"


# ---------------------------------------------------------------------------
# dump_mir output
# ---------------------------------------------------------------------------


def test_dump_mir_shows_function() -> None:
    text = dump_mir(_lower("fn inc(x: Int) -> Int:\n    return x\n"))
    assert "fn inc(" in text
    assert "-> Int" in text


def test_dump_mir_no_match_keyword() -> None:
    src = "fn f(n: Int) -> Int:\n    match n:\n        0: return 0\n        _: return 1\n"
    text = dump_mir(_lower(src))
    # match is desugared — no 'match' keyword should appear
    assert "match" not in text
    assert "if" in text


def test_dump_mir_no_for_keyword() -> None:
    src = "fn f():\n    for x in items:\n        return x\n"
    text = dump_mir(_lower(src))
    assert "for " not in text
    assert "while" in text

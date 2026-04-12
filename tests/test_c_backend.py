"""Tests for the C backend transpiler (CTranspiler + compile_c)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from aster_lang.c_transpiler import CTranspiler, _emit_literal, _mangle
from aster_lang.hir import HBinOp, HCall, HLit, HName, HUnaryOp
from aster_lang.mir import (
    MBreak,
    MContinue,
    MExprStmt,
    MFunction,
    MIf,
    MLet,
    MModule,
    MReturn,
    MStmt,
    MTopLevel,
    MWhile,
)
from aster_lang.semantic import UNKNOWN_TYPE

# ---------------------------------------------------------------------------
# Helpers to build minimal MIR structures
# ---------------------------------------------------------------------------

_T = UNKNOWN_TYPE


def _int(v: int) -> HLit:
    return HLit(value=v, ty=_T)


def _bool(v: bool) -> HLit:
    return HLit(value=v, ty=_T)


_NIL = HLit(value=None, ty=_T)


def _name(n: str) -> HName:
    return HName(name=n, ty=_T)


def _str(s: str) -> HLit:
    return HLit(value=s, ty=_T)


def _simple_fn(
    name: str,
    body: tuple[MStmt, ...],
    params: tuple[str, ...] = (),
) -> MFunction:
    return MFunction(
        fn_id=f"fn_{name}",
        name=name,
        params=params,
        param_types=tuple(_T for _ in params),
        return_type=_T,
        free_vars=(),
        body=body,
        is_public=False,
        effects=(),
    )


def _module(*decls: MTopLevel) -> MModule:
    return MModule(decls=decls)


# ---------------------------------------------------------------------------
# _mangle
# ---------------------------------------------------------------------------


def test_mangle_main() -> None:
    assert _mangle("main") == "aster_main"


def test_mangle_regular() -> None:
    assert _mangle("foo") == "foo"


def test_mangle_hyphen() -> None:
    assert _mangle("my-func") == "my_func"


# ---------------------------------------------------------------------------
# _emit_literal
# ---------------------------------------------------------------------------


def test_emit_literal_nil() -> None:
    assert _emit_literal(HLit(value=None, ty=_T)) == "ASTER_NIL_VAL"


def test_emit_literal_int() -> None:
    assert _emit_literal(HLit(value=42, ty=_T)) == "aster_int(42)"


def test_emit_literal_bool_true() -> None:
    assert _emit_literal(HLit(value=True, ty=_T)) == "aster_bool(1)"


def test_emit_literal_bool_false() -> None:
    assert _emit_literal(HLit(value=False, ty=_T)) == "aster_bool(0)"


def test_emit_literal_string() -> None:
    assert _emit_literal(HLit(value="hello", ty=_T)) == 'aster_string("hello")'


def test_emit_literal_string_escapes() -> None:
    assert _emit_literal(HLit(value='say "hi"', ty=_T)) == r'aster_string("say \"hi\"")'


def test_emit_literal_string_newline() -> None:
    assert _emit_literal(HLit(value="a\nb", ty=_T)) == 'aster_string("a\\nb")'


# ---------------------------------------------------------------------------
# CTranspiler — runtime header is always present
# ---------------------------------------------------------------------------


def test_transpile_includes_runtime_header() -> None:
    mmod = _module()
    c = CTranspiler().transpile(mmod)
    assert "AsterValue" in c
    assert "aster_truthy" in c
    assert "aster_print" in c
    assert "#include <stdio.h>" in c


# ---------------------------------------------------------------------------
# CTranspiler — empty module
# ---------------------------------------------------------------------------


def test_transpile_empty_module_no_main_wrapper() -> None:
    mmod = _module()
    c = CTranspiler().transpile(mmod)
    assert "int main(void)" not in c


# ---------------------------------------------------------------------------
# CTranspiler — main wrapper generation
# ---------------------------------------------------------------------------


def test_transpile_main_fn_gets_wrapper() -> None:
    fn = _simple_fn("main", (MReturn(value=_int(0)),))
    mmod = _module(fn)
    c = CTranspiler().transpile(mmod)
    assert "int main(void)" in c
    assert "aster_main();" in c


# ---------------------------------------------------------------------------
# CTranspiler — function signature
# ---------------------------------------------------------------------------


def test_fn_no_params_uses_void() -> None:
    fn = _simple_fn("add", ())
    mmod = _module(fn)
    c = CTranspiler().transpile(mmod)
    assert "AsterValue add(void)" in c


def test_fn_with_params() -> None:
    fn = _simple_fn("add", (), params=("x", "y"))
    mmod = _module(fn)
    c = CTranspiler().transpile(mmod)
    assert "AsterValue add(AsterValue x, AsterValue y)" in c


# ---------------------------------------------------------------------------
# CTranspiler — forward declarations
# ---------------------------------------------------------------------------


def test_forward_declarations_are_emitted() -> None:
    fn = _simple_fn("foo", ())
    mmod = _module(fn)
    c = CTranspiler().transpile(mmod)
    # The forward decl (with semicolon) must appear before the definition.
    decl_pos = c.index("AsterValue foo(void);")
    defn_pos = c.index("AsterValue foo(void) {")
    assert decl_pos < defn_pos


# ---------------------------------------------------------------------------
# CTranspiler — statement emission
# ---------------------------------------------------------------------------


def test_emit_let() -> None:
    fn = _simple_fn("f", (MLet(name="x", is_mutable=False, ty=_T, init=_int(7)),))
    c = CTranspiler().transpile(_module(fn))
    assert "AsterValue x = aster_int(7);" in c


def test_emit_return_value() -> None:
    fn = _simple_fn("f", (MReturn(value=_int(1)),))
    c = CTranspiler().transpile(_module(fn))
    assert "return aster_int(1);" in c


def test_emit_return_nil() -> None:
    fn = _simple_fn("f", (MReturn(value=None),))
    c = CTranspiler().transpile(_module(fn))
    assert "return ASTER_NIL_VAL;" in c


def test_emit_implicit_nil_return() -> None:
    # Every function gets an implicit nil return at the end.
    fn = _simple_fn("f", ())
    c = CTranspiler().transpile(_module(fn))
    assert "return ASTER_NIL_VAL;" in c


def test_emit_break() -> None:
    fn = _simple_fn("f", (MBreak(),))
    c = CTranspiler().transpile(_module(fn))
    assert "break;" in c


def test_emit_continue() -> None:
    fn = _simple_fn("f", (MContinue(),))
    c = CTranspiler().transpile(_module(fn))
    assert "continue;" in c


def test_emit_expr_stmt() -> None:
    call = HCall(func=_name("print"), args=(_int(1),), ty=_T)
    fn = _simple_fn("f", (MExprStmt(expr=call),))
    c = CTranspiler().transpile(_module(fn))
    assert "aster_print(aster_int(1));" in c


def test_emit_if() -> None:
    fn = _simple_fn(
        "f",
        (
            MIf(
                condition=_bool(True),
                then_body=(MReturn(value=_int(1)),),
                else_body=(),
            ),
        ),
    )
    c = CTranspiler().transpile(_module(fn))
    assert "if (aster_truthy(aster_bool(1)))" in c
    assert "return aster_int(1);" in c


def test_emit_if_else() -> None:
    fn = _simple_fn(
        "f",
        (
            MIf(
                condition=_bool(True),
                then_body=(MReturn(value=_int(1)),),
                else_body=(MReturn(value=_int(2)),),
            ),
        ),
    )
    c = CTranspiler().transpile(_module(fn))
    assert "} else {" in c


def test_emit_while() -> None:
    fn = _simple_fn(
        "f",
        (MWhile(condition=_bool(False), body=(MBreak(),)),),
    )
    c = CTranspiler().transpile(_module(fn))
    assert "while (aster_truthy(aster_bool(0)))" in c


# ---------------------------------------------------------------------------
# CTranspiler — expression emission
# ---------------------------------------------------------------------------


def test_emit_binop_add() -> None:
    expr = HBinOp(op="+", left=_int(2), right=_int(3), ty=_T)
    fn = _simple_fn("f", (MReturn(value=expr),))
    c = CTranspiler().transpile(_module(fn))
    assert "aster_add(aster_int(2), aster_int(3))" in c


def test_emit_binop_all_operators() -> None:
    ops = {
        "+": "aster_add",
        "-": "aster_sub",
        "*": "aster_mul",
        "/": "aster_div",
        "%": "aster_mod",
        "==": "aster_eq",
        "!=": "aster_ne",
        "<": "aster_lt",
        ">": "aster_gt",
        "<=": "aster_le",
        ">=": "aster_ge",
        "and": "aster_and",
        "or": "aster_or",
    }
    for op, c_fn in ops.items():
        expr = HBinOp(op=op, left=_int(1), right=_int(2), ty=_T)
        fn = _simple_fn("f", (MReturn(value=expr),))
        c = CTranspiler().transpile(_module(fn))
        assert c_fn in c, f"expected {c_fn} for op {op!r}"


def test_emit_unary_neg() -> None:
    expr = HUnaryOp(op="-", operand=_int(5), ty=_T)
    fn = _simple_fn("f", (MReturn(value=expr),))
    c = CTranspiler().transpile(_module(fn))
    assert "aster_neg(aster_int(5))" in c


def test_emit_unary_not() -> None:
    expr = HUnaryOp(op="not", operand=_bool(True), ty=_T)
    fn = _simple_fn("f", (MReturn(value=expr),))
    c = CTranspiler().transpile(_module(fn))
    assert "aster_not(aster_bool(1))" in c


def test_emit_user_function_call() -> None:
    call = HCall(func=_name("foo"), args=(_int(1), _int(2)), ty=_T)
    fn = _simple_fn("f", (MReturn(value=call),))
    c = CTranspiler().transpile(_module(fn))
    assert "foo(aster_int(1), aster_int(2))" in c


def test_emit_print_builtin() -> None:
    call = HCall(func=_name("print"), args=(_str("hi"),), ty=_T)
    fn = _simple_fn("f", (MExprStmt(expr=call),))
    c = CTranspiler().transpile(_module(fn))
    assert 'aster_print(aster_string("hi"))' in c


# ---------------------------------------------------------------------------
# End-to-end compile test (skipped when no C compiler available)
# ---------------------------------------------------------------------------


_NO_CC = (
    shutil.which("cc") is None and shutil.which("gcc") is None and shutil.which("clang") is None
)


@pytest.mark.skipif(_NO_CC, reason="no C compiler available")  # type: ignore[misc]
def test_compile_hello_world(tmp_path: Path) -> None:
    """Compiles a minimal Aster program to a native binary and runs it."""
    import subprocess

    from aster_lang.c_transpiler import compile_c

    # Build a module with: fn main() { print("hello"); return nil; }
    call = HCall(func=_name("print"), args=(_str("hello"),), ty=_T)
    fn = _simple_fn("main", (MExprStmt(expr=call), MReturn(value=None)))
    mmod = _module(fn)
    c_code = CTranspiler().transpile(mmod)

    bin_path = tmp_path / "hello"
    compile_c(c_code, bin_path)

    result = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert result.stdout.strip() == "hello"


@pytest.mark.skipif(_NO_CC, reason="no C compiler available")  # type: ignore[misc]
def test_compile_arithmetic(tmp_path: Path) -> None:
    """Compiles integer arithmetic and verifies output."""
    import subprocess

    from aster_lang.c_transpiler import compile_c

    # fn main(): print(2 + 3 * 4)  => print(add(2, mul(3, 4))) => 14
    inner = HBinOp(op="*", left=_int(3), right=_int(4), ty=_T)
    outer = HBinOp(op="+", left=_int(2), right=inner, ty=_T)
    call = HCall(func=_name("print"), args=(outer,), ty=_T)
    fn = _simple_fn("main", (MExprStmt(expr=call), MReturn(value=None)))
    mmod = _module(fn)
    c_code = CTranspiler().transpile(mmod)

    bin_path = tmp_path / "arith"
    compile_c(c_code, bin_path)

    result = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert result.stdout.strip() == "14"

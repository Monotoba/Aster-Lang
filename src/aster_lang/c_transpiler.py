"""C backend transpiler for Aster.

Translates a lowered MIR module into a single C translation unit.  The
generated file is self-contained: it embeds the minimal Aster runtime as a
header block followed by the emitted functions.

Spike coverage
--------------
- Int / Bool / Nil / String literals
- Arithmetic: + - * / %
- Comparisons: == != < > <= >=
- Logical: and or not
- Variables (MLet, MAssign)
- Control flow: if/else, while, break, continue, return
- Function calls (named, no closures in spike)
- Built-in: print
- Aster ``main`` lowered to ``aster_main()`` + generated C ``main``

Not yet supported (emits ``/* unsupported */`` comment):
- Closures, lists, tuples, records, borrows, index/member access
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from aster_lang.hir import (
    HBinOp,
    HBorrow,
    HCall,
    HClosure,
    HExpr,
    HIndex,
    HList,
    HLit,
    HMember,
    HName,
    HRecord,
    HTuple,
    HUnaryOp,
)
from aster_lang.mir import (
    MAssign,
    MBreak,
    MContinue,
    MExprStmt,
    MFunction,
    MIf,
    MLet,
    MModule,
    MReturn,
    MStmt,
    MWhile,
)

# ---------------------------------------------------------------------------
# Embedded C runtime reference (replaced by aster_runtime.h)
# ---------------------------------------------------------------------------

_ASTER_RUNTIME_HEADER = r"""
#include "aster_runtime.h"
"""

# Operator → C helper name
_BINOP_FN: dict[str, str] = {
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

_UNARY_FN: dict[str, str] = {
    "-": "aster_neg",
    "not": "aster_not",
}

# Built-in Aster names that map to C helpers
_BUILTIN_FN: dict[str, str] = {
    "print": "aster_print",
    "len": "aster_list_len",
}

_INDENT = "    "


class CTranspiler:
    """Translates an Aster MIR module into a C translation unit."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._forward_decls: list[str] = []
        self._tmp_counter = 0

    def _fresh_tmp(self) -> str:
        self._tmp_counter += 1
        return f"_tmp{self._tmp_counter}"

    def transpile(self, mmod: MModule) -> str:
        """Return a complete C translation unit for *mmod*."""
        self._lines = []
        self._forward_decls = []

        # Collect functions in emit order: lifted lambdas first, then module decls.
        fns: list[MFunction] = []
        for fn in mmod.lifted_fns.values():
            fns.append(fn)
        for decl in mmod.decls:
            if isinstance(decl, MFunction):
                fns.append(decl)

        # Build forward declarations.
        for fn in fns:
            self._forward_decls.append(self._fn_signature(fn) + ";")

        # Emit runtime + forward decls + function bodies.
        self._lines.append(_ASTER_RUNTIME_HEADER)
        for fd in self._forward_decls:
            self._lines.append(fd)
        if self._forward_decls:
            self._lines.append("")

        for fn in fns:
            self._emit_function(fn)

        # If there is an aster `main`, emit a C `main` that calls it.
        fn_names = {fn.name for fn in fns}
        if "main" in fn_names:
            self._lines.append("int main(void) {")
            self._lines.append(f"{_INDENT}aster_main();")
            self._lines.append(f"{_INDENT}return 0;")
            self._lines.append("}")
            self._lines.append("")

        return "\n".join(self._lines)

    # ------------------------------------------------------------------
    # Function emission
    # ------------------------------------------------------------------

    def _fn_signature(self, fn: MFunction) -> str:
        c_name = _mangle(fn.name)
        params = ", ".join(f"AsterValue {p}" for p in fn.params) if fn.params else "void"
        return f"AsterValue {c_name}({params})"

    def _emit_function(self, fn: MFunction) -> None:
        self._lines.append(self._fn_signature(fn) + " {")
        self._emit_stmts(fn.body, depth=1)
        # Implicit nil return — ensures every C path has a return value.
        # Not needed when the last statement is already an unconditional return,
        # but emitting it unconditionally is safe; C will never reach it after
        # the explicit return.  We guard only to avoid dead-code warnings.
        if not fn.body or not isinstance(fn.body[-1], MReturn):
            self._lines.append(f"{_INDENT}return ASTER_NIL_VAL;")
        self._lines.append("}")
        self._lines.append("")

    # ------------------------------------------------------------------
    # Statement emission
    # ------------------------------------------------------------------

    def _emit_stmts(self, stmts: tuple[MStmt, ...], depth: int) -> None:
        for s in stmts:
            self._emit_stmt(s, depth)

    def _emit_stmt(self, s: MStmt, depth: int) -> None:
        pad = _INDENT * depth

        if isinstance(s, MLet):
            expr_c = self._emit_expr(s.init)
            c_name = _mangle(s.name)
            if isinstance(s.init, HClosure):
                # Lambda-lifted functions are top-level C functions.
                fn_name = s.init.fn_id.split("::")[-1]
                self._lines.append(f"{pad}AsterValue (*{c_name})(AsterValue) = {fn_name};")
            else:
                self._lines.append(f"{pad}AsterValue {c_name} = {expr_c};")

        elif isinstance(s, MAssign):
            target_c = self._emit_lvalue(s.target)
            val_c = self._emit_expr(s.value)
            self._lines.append(f"{pad}{target_c} = {val_c};")

        elif isinstance(s, MReturn):
            if s.value is not None:
                self._lines.append(f"{pad}return {self._emit_expr(s.value)};")
            else:
                self._lines.append(f"{pad}return ASTER_NIL_VAL;")

        elif isinstance(s, MExprStmt):
            self._lines.append(f"{pad}{self._emit_expr(s.expr)};")

        elif isinstance(s, MBreak):
            self._lines.append(f"{pad}break;")

        elif isinstance(s, MContinue):
            self._lines.append(f"{pad}continue;")

        elif isinstance(s, MIf):
            cond_c = self._emit_expr(s.condition)
            self._lines.append(f"{pad}if (aster_truthy({cond_c})) {{")
            self._emit_stmts(s.then_body, depth + 1)
            if s.else_body:
                self._lines.append(f"{pad}}} else {{")
                self._emit_stmts(s.else_body, depth + 1)
            self._lines.append(f"{pad}}}")

        elif isinstance(s, MWhile):
            cond_c = self._emit_expr(s.condition)
            self._lines.append(f"{pad}while (aster_truthy({cond_c})) {{")
            self._emit_stmts(s.body, depth + 1)
            self._lines.append(f"{pad}}}")

        else:
            raise AssertionError(f"unhandled MStmt type: {type(s).__name__}")

    # ------------------------------------------------------------------
    # Expression emission
    # ------------------------------------------------------------------

    def _emit_expr(self, e: HExpr) -> str:
        if isinstance(e, HLit):
            return _emit_literal(e)

        if isinstance(e, HName):
            return _mangle(e.name)

        if isinstance(e, HBinOp):
            fn = _BINOP_FN.get(e.op)
            if fn:
                left = self._emit_expr(e.left)
                right = self._emit_expr(e.right)
                return f"{fn}({left}, {right})"
            return f"/* unsupported op: {e.op} */"

        if isinstance(e, HUnaryOp):
            fn = _UNARY_FN.get(e.op)
            if fn:
                return f"{fn}({self._emit_expr(e.operand)})"
            return f"/* unsupported unary: {e.op} */"

        if isinstance(e, HCall):
            if isinstance(e.func, HName) and e.func.name == "len":
                # len() returns size_t, wrap in aster_int for AsterValue.
                args = ", ".join(self._emit_expr(a) for a in e.args)
                return f"aster_int(aster_list_len({args}))"
            return self._emit_call(e)

        if isinstance(e, HList):
            # Create new list
            list_val = self._fresh_tmp()
            self._lines.append(f"{_INDENT}AsterValue {list_val} = aster_list_new();")
            for elem in e.elements:
                elem_val = self._emit_expr(elem)
                self._lines.append(f"{_INDENT}aster_list_append({list_val}, {elem_val});")
            return list_val

        if isinstance(e, HIndex):
            obj = self._emit_expr(e.obj)
            idx = self._emit_expr(e.index)
            return f"aster_list_get({obj}, {idx})"

        if isinstance(e, HClosure):
            # For spike, ignore the closure and just call the function directly
            # by name if possible, or emit a placeholder.
            # Lambda-lifted functions have names like "__lambda1".
            fn_name = e.fn_id.split("::")[-1]
            return fn_name

        if isinstance(e, HRecord):
            # Create new record
            rec_val = self._fresh_tmp()
            self._lines.append(f"{_INDENT}AsterValue {rec_val} = aster_record_new();")
            for name, val in e.fields:
                val_c = self._emit_expr(val)
                self._lines.append(f'{_INDENT}aster_record_set({rec_val}, "{name}", {val_c});')
            return rec_val

        if isinstance(e, HMember):
            obj = self._emit_expr(e.obj)
            return f'aster_record_get({obj}, "{e.member}")'

        if isinstance(e, HBorrow | HTuple):
            return f"/* unsupported expr: {type(e).__name__} */"

        raise AssertionError(f"unhandled HExpr type: {type(e).__name__}")

    def _emit_call(self, e: HCall) -> str:
        # Check for built-in names first.
        if isinstance(e.func, HName):
            builtin = _BUILTIN_FN.get(e.func.name)
            if builtin:
                args = ", ".join(self._emit_expr(a) for a in e.args)
                return f"{builtin}({args})"
            # Regular user-defined call.
            c_name = _mangle(e.func.name)
            args = ", ".join(self._emit_expr(a) for a in e.args)
            return f"{c_name}({args})"

        # Handle closure calls.
        if isinstance(e.func, HClosure):
            # For spike, ignore the closure and just call the function directly
            # by name if possible, or emit a placeholder.
            # Lambda-lifted functions have names like "__lambda1".
            fn_name = e.func.fn_id.split("::")[-1]
            args = ", ".join(self._emit_expr(a) for a in e.args)
            return f"{fn_name}({args})"

        # Expression call (closure etc.) — not yet supported.
        return "/* unsupported: expression call */"

    def _emit_lvalue(self, e: HExpr) -> str:
        """Emit an assignable lvalue (HName only for now)."""
        if isinstance(e, HName):
            return _mangle(e.name)
        return "/* unsupported lvalue */"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mangle(name: str) -> str:
    """Map Aster identifiers to C-safe names.

    ``main`` → ``aster_main`` (avoids collision with C ``main``).
    Leading ``__`` names (temporaries) are kept as-is after sanitising.
    """
    if name == "main":
        return "aster_main"
    # Replace characters not valid in C identifiers.
    return name.replace("-", "_")


def _emit_literal(e: HLit) -> str:
    if e.value is None:
        return "ASTER_NIL_VAL"
    if isinstance(e.value, bool):
        return f"aster_bool({1 if e.value else 0})"
    if isinstance(e.value, int):
        return f"aster_int({e.value})"
    if isinstance(e.value, str):
        escaped = e.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'aster_string("{escaped}")'
    raise AssertionError(f"unhandled HLit value type: {type(e.value).__name__}")


# ---------------------------------------------------------------------------
# Build harness
# ---------------------------------------------------------------------------


class CBuildError(Exception):
    """Raised when the system C compiler is unavailable or compilation fails."""


def compile_c(c_source: str, out_path: Path) -> list[str]:
    """Compile *c_source* to a native binary at *out_path* using system ``cc``.

    Returns a list of warning/error strings.  Raises ``CBuildError`` if
    ``cc`` is not found or compilation fails.
    """
    import aster_lang

    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        raise CBuildError("No C compiler found (tried cc, gcc, clang)")

    # Locate the runtime files
    runtime_dir = Path(aster_lang.__file__).parent / "runtime"
    runtime_c = runtime_dir / "aster_runtime.c"
    runtime_h = runtime_dir / "aster_runtime.h"

    if not runtime_c.exists() or not runtime_h.exists():
        raise CBuildError(f"Aster runtime not found in {runtime_dir}")

    c_file = out_path.with_suffix(".c")
    c_file.write_text(c_source, encoding="utf-8")

    result = subprocess.run(
        [
            cc,
            "-o",
            str(out_path),
            str(c_file),
            str(runtime_c),
            f"-I{runtime_dir}",
            "-std=c11",
            "-lm",
        ],
        capture_output=True,
        text=True,
    )
    errors: list[str] = []
    if result.stderr:
        errors.extend(result.stderr.splitlines())
    if result.returncode != 0:
        raise CBuildError(f"C compilation failed (exit {result.returncode}):\n{result.stderr}")
    return errors

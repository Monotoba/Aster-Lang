"""ctypes-based Foreign Function Interface for Aster.

Called lazily by the interpreter when an ``extern`` declaration is executed.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aster_lang import ast as _ast

# ---------------------------------------------------------------------------
# Type mapping: Aster type name -> ctypes type (None == void)
# ---------------------------------------------------------------------------

_ASTER_TO_CTYPE: dict[str, type | None] = {
    "Int": ctypes.c_int64,
    "Float": ctypes.c_double,
    "String": ctypes.c_char_p,
    "Bool": ctypes.c_int,
    "Byte": ctypes.c_uint8,
    "Word": ctypes.c_uint16,
    "DWord": ctypes.c_uint32,
    "QWord": ctypes.c_uint64,
    "Nil": None,
}


def _resolve_ctype(type_expr: _ast.TypeExpr | None) -> type | None:
    """Return the ctypes type for an Aster type expression, or None for void."""
    from aster_lang import ast  # noqa: PLC0415

    if type_expr is None:
        return None
    if isinstance(type_expr, ast.SimpleType) and len(type_expr.name.parts) == 1:
        name = type_expr.name.parts[0]
        if name in _ASTER_TO_CTYPE:
            return _ASTER_TO_CTYPE[name]
    return ctypes.c_int64  # safe fallback


# ---------------------------------------------------------------------------
# Value coercion: Aster Value -> C arg, C result -> Aster Value
# ---------------------------------------------------------------------------


def _coerce_arg(value: object, ctype: type | None) -> object:
    """Convert an Aster runtime Value to a C-compatible argument."""
    from aster_lang.interpreter import (  # noqa: PLC0415
        BitsValue,
        BoolValue,
        FloatValue,
        IntValue,
        StringValue,
    )

    if isinstance(value, IntValue | BitsValue):
        return value.value
    if isinstance(value, FloatValue):
        return value.value
    if isinstance(value, BoolValue):
        return 1 if value.value else 0
    if isinstance(value, StringValue):
        return value.value.encode()
    return value  # pass through


def _c_to_aster(raw: object, ctype: type | None) -> object:
    """Convert a C return value to an Aster runtime Value."""
    from aster_lang.interpreter import FloatValue, IntValue, NilValue, StringValue  # noqa: PLC0415

    if ctype is None or raw is None:
        return NilValue()
    if ctype is ctypes.c_double or ctype is ctypes.c_float:
        return FloatValue(float(raw))  # type: ignore[arg-type]
    if ctype is ctypes.c_char_p:
        if raw is None:
            return StringValue("")
        return StringValue(raw.decode() if isinstance(raw, bytes) else str(raw))
    if ctype is ctypes.c_int:
        # Bool return: normalise to Python bool kept as IntValue(0/1)
        return IntValue(int(raw))  # type: ignore[call-overload]
    return IntValue(int(raw))  # type: ignore[call-overload]


# ---------------------------------------------------------------------------
# Library loading
# ---------------------------------------------------------------------------


def _load_library(library: str) -> ctypes.CDLL:
    """Load a shared library by name or path.

    Resolution order:
    1. Absolute / relative path (starts with '/' or './')
    2. ctypes.util.find_library lookup
    3. Direct CDLL(library) fallback
    """
    from aster_lang.interpreter import InterpreterError  # noqa: PLC0415

    if library.startswith("/") or library.startswith("./"):
        try:
            return ctypes.CDLL(library)
        except OSError as exc:
            raise InterpreterError(f"FFI: cannot load library '{library}': {exc}") from exc

    # Strip leading "lib" for find_library (e.g. "libm" -> "m")
    stem = library[3:] if library.startswith("lib") else library
    found = ctypes.util.find_library(stem)
    if found:
        try:
            return ctypes.CDLL(found)
        except OSError:
            pass  # fall through to direct attempt

    try:
        return ctypes.CDLL(library)
    except OSError as exc:
        raise InterpreterError(f"FFI: cannot load library '{library}': {exc}") from exc


# ---------------------------------------------------------------------------
# Per-function wrapper factory (avoids loop-variable capture)
# ---------------------------------------------------------------------------


def _make_wrapper(
    cfn: object,
    param_ctypes: list[type | None],
    ret_ctype: type | None,
    fn_name: str,
) -> object:
    """Return a BuiltinFunction.func compatible callable wrapping *cfn*."""

    def wrapper(args: list[object]) -> object:
        coerced = [_coerce_arg(a, pt) for a, pt in zip(args, param_ctypes, strict=False)]
        raw = cfn(*coerced)  # type: ignore[operator]
        return _c_to_aster(raw, ret_ctype)

    wrapper.__name__ = fn_name
    return wrapper


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_extern_functions(
    library: str,
    signatures: list[_ast.FunctionSig],
) -> dict[str, object]:
    """Load *library* and return a dict of name -> BuiltinFunction for each sig."""
    from aster_lang.interpreter import BuiltinFunction  # noqa: PLC0415

    lib = _load_library(library)
    result: dict[str, object] = {}

    for sig in signatures:
        param_ctypes = [_resolve_ctype(p.type_annotation) for p in sig.params]
        ret_ctype = _resolve_ctype(sig.return_type)

        try:
            cfn = getattr(lib, sig.name)
        except AttributeError as exc:
            from aster_lang.interpreter import InterpreterError  # noqa: PLC0415

            raise InterpreterError(f"FFI: library '{library}' has no symbol '{sig.name}'") from exc

        # Configure ctypes argtypes / restype for type safety
        cfn.argtypes = [ct for ct in param_ctypes if ct is not None]
        cfn.restype = ret_ctype

        wrapper = _make_wrapper(cfn, param_ctypes, ret_ctype, sig.name)
        result[sig.name] = BuiltinFunction(
            name=sig.name,
            func=wrapper,  # type: ignore[arg-type]
            arity=len(sig.params),
        )

    return result

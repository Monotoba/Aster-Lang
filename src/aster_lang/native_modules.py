"""Native (built-in) module implementations for the Aster standard library.

Three modules are provided:

* ``math``  — mathematical functions and constants (backed by Python's ``math``).
* ``str``   — string manipulation functions.
* ``std``   — general utilities (type_of, panic, todo, input).

Each module is a callable that returns a ``ModuleValue`` when invoked; the
registry ``NATIVE_MODULES`` maps module names to those callables.

``NATIVE_MODULE_SYMBOLS`` maps the same names to ``dict[str, Symbol]`` entries
used by the semantic analyser so that ``use math`` etc. do not raise
"module not found" errors during static analysis.
"""

from __future__ import annotations

import math as _math
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# mypy: ignore-errors  (file uses lazy runtime imports for circular-import avoidance)

# ---------------------------------------------------------------------------
# Helpers — imported lazily at call-time to avoid circular imports
# ---------------------------------------------------------------------------


def _interp() -> object:
    """Return the interpreter module (lazy import)."""
    import aster_lang.interpreter as _m  # noqa: PLC0415

    return _m


def _sem() -> object:
    """Return the semantic module (lazy import)."""
    import aster_lang.semantic as _m  # noqa: PLC0415

    return _m


# ---------------------------------------------------------------------------
# Numeric helpers shared by math functions
# ---------------------------------------------------------------------------


def _to_float(v: object) -> float:
    """Coerce an Aster numeric value to Python float."""
    interp = _interp()
    if isinstance(v, interp.FloatValue):  # type: ignore[attr-defined]
        return v.value  # type: ignore[attr-defined]
    if isinstance(v, (interp.IntValue, interp.BitsValue)):  # type: ignore[attr-defined]  # noqa: UP038
        return float(v.value)  # type: ignore[attr-defined]
    raise _interp().InterpreterError(  # type: ignore[attr-defined]
        f"Expected numeric value, got {type(v).__name__}"
    )


def _int_or_float(x: float) -> object:
    """Return IntValue if x is a whole number, else FloatValue."""
    interp = _interp()
    if x == int(x) and _math.isfinite(x):
        return interp.IntValue(int(x))  # type: ignore[attr-defined]
    return interp.FloatValue(x)  # type: ignore[attr-defined]


def _require_string(v: object, label: str) -> str:
    interp = _interp()
    if not isinstance(v, interp.StringValue):  # type: ignore[attr-defined]
        raise interp.InterpreterError(  # type: ignore[attr-defined]
            f"{label}: expected String, got {type(v).__name__}"
        )
    return v.value  # type: ignore[attr-defined]


def _require_int(v: object, label: str) -> int:
    interp = _interp()
    if isinstance(v, interp.IntValue):  # type: ignore[attr-defined]
        return v.value  # type: ignore[attr-defined]
    if isinstance(v, interp.BitsValue):  # type: ignore[attr-defined]
        return v.value  # type: ignore[attr-defined]
    raise interp.InterpreterError(  # type: ignore[attr-defined]
        f"{label}: expected Int, got {type(v).__name__}"
    )


# ---------------------------------------------------------------------------
# math module
# ---------------------------------------------------------------------------


def _build_math_module() -> object:
    interp = _interp()
    IV = interp.IntValue  # type: ignore[attr-defined]
    FV = interp.FloatValue  # type: ignore[attr-defined]
    BF = interp.BuiltinFunction  # type: ignore[attr-defined]
    MV = interp.ModuleValue  # type: ignore[attr-defined]
    IE = interp.InterpreterError  # type: ignore[attr-defined]

    def _abs(args: list) -> object:
        x = _to_float(args[0])
        return _int_or_float(abs(x))

    def _floor(args: list) -> object:
        return IV(_math.floor(_to_float(args[0])))

    def _ceil(args: list) -> object:
        return IV(_math.ceil(_to_float(args[0])))

    def _round(args: list) -> object:
        return IV(round(_to_float(args[0])))

    def _sqrt(args: list) -> object:
        x = _to_float(args[0])
        if x < 0:
            raise IE("math.sqrt: domain error (negative input)")
        return _int_or_float(_math.sqrt(x))

    def _pow(args: list) -> object:
        base = _to_float(args[0])
        exp = _to_float(args[1])
        return _int_or_float(base**exp)

    def _log(args: list) -> object:
        x = _to_float(args[0])
        if x <= 0:
            raise IE("math.log: domain error (non-positive input)")
        return FV(_math.log(x))

    def _log2(args: list) -> object:
        x = _to_float(args[0])
        if x <= 0:
            raise IE("math.log2: domain error (non-positive input)")
        return FV(_math.log2(x))

    def _log10(args: list) -> object:
        x = _to_float(args[0])
        if x <= 0:
            raise IE("math.log10: domain error (non-positive input)")
        return FV(_math.log10(x))

    def _sin(args: list) -> object:
        return FV(_math.sin(_to_float(args[0])))

    def _cos(args: list) -> object:
        return FV(_math.cos(_to_float(args[0])))

    def _tan(args: list) -> object:
        return FV(_math.tan(_to_float(args[0])))

    def _min(args: list) -> object:
        a = _to_float(args[0])
        b = _to_float(args[1])
        return _int_or_float(min(a, b))

    def _max(args: list) -> object:
        a = _to_float(args[0])
        b = _to_float(args[1])
        return _int_or_float(max(a, b))

    def _clamp(args: list) -> object:
        x = _to_float(args[0])
        lo = _to_float(args[1])
        hi = _to_float(args[2])
        return _int_or_float(max(lo, min(hi, x)))

    exports: dict[str, object] = {
        # Constants
        "pi": FV(_math.pi),
        "e": FV(_math.e),
        "tau": FV(_math.tau),
        "inf": FV(_math.inf),
        # Functions
        "abs": BF("abs", _abs, arity=1),
        "floor": BF("floor", _floor, arity=1),
        "ceil": BF("ceil", _ceil, arity=1),
        "round": BF("round", _round, arity=1),
        "sqrt": BF("sqrt", _sqrt, arity=1),
        "pow": BF("pow", _pow, arity=2),
        "log": BF("log", _log, arity=1),
        "log2": BF("log2", _log2, arity=1),
        "log10": BF("log10", _log10, arity=1),
        "sin": BF("sin", _sin, arity=1),
        "cos": BF("cos", _cos, arity=1),
        "tan": BF("tan", _tan, arity=1),
        "min": BF("min", _min, arity=2),
        "max": BF("max", _max, arity=2),
        "clamp": BF("clamp", _clamp, arity=3),
    }
    return MV("math", exports)


# ---------------------------------------------------------------------------
# str module
# ---------------------------------------------------------------------------


def _build_str_module() -> object:
    interp = _interp()
    IV = interp.IntValue  # type: ignore[attr-defined]
    SV = interp.StringValue  # type: ignore[attr-defined]
    BoolV = interp.BoolValue  # type: ignore[attr-defined]
    LV = interp.ListValue  # type: ignore[attr-defined]
    BF = interp.BuiltinFunction  # type: ignore[attr-defined]
    MV = interp.ModuleValue  # type: ignore[attr-defined]

    def _split(args: list) -> object:
        s = _require_string(args[0], "str.split")
        sep = _require_string(args[1], "str.split")
        parts = s.split(sep)
        return LV(tuple(SV(p) for p in parts))

    def _join(args: list) -> object:
        sep = _require_string(args[0], "str.join")
        lst = args[1]
        if not isinstance(lst, interp.ListValue):  # type: ignore[attr-defined]
            raise interp.InterpreterError("str.join: second argument must be a List")  # type: ignore[attr-defined]
        parts = [_require_string(e, "str.join element") for e in lst.elements]
        return SV(sep.join(parts))

    def _strip(args: list) -> object:
        return SV(_require_string(args[0], "str.strip").strip())

    def _lstrip(args: list) -> object:
        return SV(_require_string(args[0], "str.lstrip").lstrip())

    def _rstrip(args: list) -> object:
        return SV(_require_string(args[0], "str.rstrip").rstrip())

    def _upper(args: list) -> object:
        return SV(_require_string(args[0], "str.upper").upper())

    def _lower(args: list) -> object:
        return SV(_require_string(args[0], "str.lower").lower())

    def _starts_with(args: list) -> object:
        s = _require_string(args[0], "str.starts_with")
        prefix = _require_string(args[1], "str.starts_with")
        return BoolV(s.startswith(prefix))

    def _ends_with(args: list) -> object:
        s = _require_string(args[0], "str.ends_with")
        suffix = _require_string(args[1], "str.ends_with")
        return BoolV(s.endswith(suffix))

    def _contains(args: list) -> object:
        s = _require_string(args[0], "str.contains")
        sub = _require_string(args[1], "str.contains")
        return BoolV(sub in s)

    def _find(args: list) -> object:
        s = _require_string(args[0], "str.find")
        sub = _require_string(args[1], "str.find")
        return IV(s.find(sub))

    def _replace(args: list) -> object:
        s = _require_string(args[0], "str.replace")
        old = _require_string(args[1], "str.replace")
        new = _require_string(args[2], "str.replace")
        return SV(s.replace(old, new))

    def _pad_left(args: list) -> object:
        s = _require_string(args[0], "str.pad_left")
        width = _require_int(args[1], "str.pad_left")
        fill = _require_string(args[2], "str.pad_left") if len(args) > 2 else " "
        if len(fill) != 1:
            raise interp.InterpreterError("str.pad_left: fill character must be a single character")  # type: ignore[attr-defined]
        return SV(s.rjust(width, fill))

    def _pad_right(args: list) -> object:
        s = _require_string(args[0], "str.pad_right")
        width = _require_int(args[1], "str.pad_right")
        fill = _require_string(args[2], "str.pad_right") if len(args) > 2 else " "
        if len(fill) != 1:
            raise interp.InterpreterError(  # type: ignore[attr-defined]
                "str.pad_right: fill character must be a single character"
            )
        return SV(s.ljust(width, fill))

    def _chars(args: list) -> object:
        s = _require_string(args[0], "str.chars")
        return LV(tuple(SV(c) for c in s))

    def _char_at(args: list) -> object:
        s = _require_string(args[0], "str.char_at")
        i = _require_int(args[1], "str.char_at")
        if i < 0 or i >= len(s):
            raise interp.InterpreterError(  # type: ignore[attr-defined]
                f"str.char_at: index {i} out of bounds for string of length {len(s)}"
            )
        return SV(s[i])

    def _repeat(args: list) -> object:
        s = _require_string(args[0], "str.repeat")
        n = _require_int(args[1], "str.repeat")
        return SV(s * n)

    def _slice(args: list) -> object:
        s = _require_string(args[0], "str.slice")
        start = _require_int(args[1], "str.slice")
        end = _require_int(args[2], "str.slice")
        return SV(s[start:end])

    exports: dict[str, object] = {
        "split": BF("split", _split, arity=2),
        "join": BF("join", _join, arity=2),
        "strip": BF("strip", _strip, arity=1),
        "lstrip": BF("lstrip", _lstrip, arity=1),
        "rstrip": BF("rstrip", _rstrip, arity=1),
        "upper": BF("upper", _upper, arity=1),
        "lower": BF("lower", _lower, arity=1),
        "starts_with": BF("starts_with", _starts_with, arity=2),
        "ends_with": BF("ends_with", _ends_with, arity=2),
        "contains": BF("contains", _contains, arity=2),
        "find": BF("find", _find, arity=2),
        "replace": BF("replace", _replace, arity=3),
        "pad_left": BF("pad_left", _pad_left, arity=-1),
        "pad_right": BF("pad_right", _pad_right, arity=-1),
        "chars": BF("chars", _chars, arity=1),
        "char_at": BF("char_at", _char_at, arity=2),
        "repeat": BF("repeat", _repeat, arity=2),
        "slice": BF("slice", _slice, arity=3),
    }
    return MV("str", exports)


# ---------------------------------------------------------------------------
# std module
# ---------------------------------------------------------------------------


def _build_std_module() -> object:
    interp = _interp()
    SV = interp.StringValue  # type: ignore[attr-defined]
    BF = interp.BuiltinFunction  # type: ignore[attr-defined]
    MV = interp.ModuleValue  # type: ignore[attr-defined]
    IE = interp.InterpreterError  # type: ignore[attr-defined]

    def _type_of(args: list) -> object:
        v = args[0]
        names: dict[type, str] = {
            interp.IntValue: "Int",  # type: ignore[attr-defined]
            interp.FloatValue: "Float",  # type: ignore[attr-defined]
            interp.StringValue: "String",  # type: ignore[attr-defined]
            interp.BoolValue: "Bool",  # type: ignore[attr-defined]
            interp.NilValue: "Nil",  # type: ignore[attr-defined]
            interp.ListValue: "List",  # type: ignore[attr-defined]
            interp.TupleValue: "Tuple",  # type: ignore[attr-defined]
            interp.RecordValue: "Record",  # type: ignore[attr-defined]
            interp.FunctionValue: "Function",  # type: ignore[attr-defined]
            interp.BuiltinFunction: "Function",  # type: ignore[attr-defined]
            interp.ModuleValue: "Module",  # type: ignore[attr-defined]
            interp.BitsValue: "Bits",  # type: ignore[attr-defined]
        }
        return SV(names.get(type(v), type(v).__name__))

    def _panic(args: list) -> object:
        msg = _require_string(args[0], "std.panic") if args else "explicit panic"
        raise IE(f"panic: {msg}")

    def _todo(args: list) -> object:
        raise IE("not yet implemented (todo)")

    def _input(args: list) -> object:
        prompt = _require_string(args[0], "std.input") if args else ""
        try:
            return SV(input(prompt))
        except EOFError:
            return SV("")

    exports: dict[str, object] = {
        "type_of": BF("type_of", _type_of, arity=1),
        "panic": BF("panic", _panic, arity=-1),
        "todo": BF("todo", _todo, arity=0),
        "input": BF("input", _input, arity=-1),
    }
    return MV("std", exports)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

NATIVE_MODULES: dict[str, Callable[[], object]] = {
    "math": _build_math_module,
    "str": _build_str_module,
    "std": _build_std_module,
}

# ---------------------------------------------------------------------------
# Semantic symbols for native modules (used by semantic analyser)
# ---------------------------------------------------------------------------


def _build_native_symbols() -> dict[str, dict[str, object]]:
    """Build Symbol dicts for each native module (lazy, called once)."""
    from aster_lang.semantic import (  # noqa: PLC0415
        BOOL_TYPE,
        INT_TYPE,
        NIL_TYPE,
        STRING_TYPE,
        UNKNOWN_TYPE,
        FunctionType,
        ListType,
        Symbol,
        SymbolKind,
    )

    def fn(*_: object) -> object:
        """Helper: create a variadic-unknown function Symbol."""
        return Symbol(
            name="",
            kind=SymbolKind.FUNCTION,
            type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=UNKNOWN_TYPE),
        )

    def _sym(name: str, sym_type: object = None) -> object:
        if sym_type is None:
            sym_type = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=UNKNOWN_TYPE)
        return Symbol(name=name, kind=SymbolKind.FUNCTION, type=sym_type)

    def _const(name: str, t: object) -> object:
        return Symbol(name=name, kind=SymbolKind.VARIABLE, type=t)

    from aster_lang.semantic import FloatType  # noqa: PLC0415

    FLOAT = FloatType()
    ret_int = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=INT_TYPE)
    ret_float = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=FLOAT)
    ret_str = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=STRING_TYPE)
    ret_bool = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=BOOL_TYPE)
    ret_list = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=ListType(STRING_TYPE))
    ret_unk = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=UNKNOWN_TYPE)

    math_syms = {
        "pi": _const("pi", FLOAT),
        "e": _const("e", FLOAT),
        "tau": _const("tau", FLOAT),
        "inf": _const("inf", FLOAT),
        "abs": _sym("abs", ret_unk),
        "floor": _sym("floor", ret_int),
        "ceil": _sym("ceil", ret_int),
        "round": _sym("round", ret_int),
        "sqrt": _sym("sqrt", ret_float),
        "pow": _sym("pow", ret_unk),
        "log": _sym("log", ret_float),
        "log2": _sym("log2", ret_float),
        "log10": _sym("log10", ret_float),
        "sin": _sym("sin", ret_float),
        "cos": _sym("cos", ret_float),
        "tan": _sym("tan", ret_float),
        "min": _sym("min", ret_unk),
        "max": _sym("max", ret_unk),
        "clamp": _sym("clamp", ret_unk),
    }

    str_syms = {
        "split": _sym("split", ret_list),
        "join": _sym("join", ret_str),
        "strip": _sym("strip", ret_str),
        "lstrip": _sym("lstrip", ret_str),
        "rstrip": _sym("rstrip", ret_str),
        "upper": _sym("upper", ret_str),
        "lower": _sym("lower", ret_str),
        "starts_with": _sym("starts_with", ret_bool),
        "ends_with": _sym("ends_with", ret_bool),
        "contains": _sym("contains", ret_bool),
        "find": _sym("find", ret_int),
        "replace": _sym("replace", ret_str),
        "pad_left": _sym("pad_left", ret_str),
        "pad_right": _sym("pad_right", ret_str),
        "chars": _sym("chars", ret_list),
        "char_at": _sym("char_at", ret_str),
        "repeat": _sym("repeat", ret_str),
        "slice": _sym("slice", ret_str),
    }

    std_syms = {
        "type_of": _sym("type_of", ret_str),
        "panic": _sym("panic", FunctionType(param_types=(UNKNOWN_TYPE,), return_type=NIL_TYPE)),
        "todo": _sym("todo", FunctionType(param_types=(), return_type=NIL_TYPE)),
        "input": _sym("input", ret_str),
    }

    return {"math": math_syms, "str": str_syms, "std": std_syms}  # type: ignore[return-value]


# Populated on first import of this module.
NATIVE_MODULE_SYMBOLS: dict[str, dict[str, object]] = _build_native_symbols()

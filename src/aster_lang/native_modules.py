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

    def _exp(args: list) -> object:
        return FV(_math.exp(_to_float(args[0])))

    def _asin(args: list) -> object:
        x = _to_float(args[0])
        if x < -1 or x > 1:
            raise IE("math.asin: domain error (input must be in [-1, 1])")
        return FV(_math.asin(x))

    def _acos(args: list) -> object:
        x = _to_float(args[0])
        if x < -1 or x > 1:
            raise IE("math.acos: domain error (input must be in [-1, 1])")
        return FV(_math.acos(x))

    def _atan(args: list) -> object:
        return FV(_math.atan(_to_float(args[0])))

    def _atan2(args: list) -> object:
        y = _to_float(args[0])
        x = _to_float(args[1])
        return FV(_math.atan2(y, x))

    def _sinh(args: list) -> object:
        return FV(_math.sinh(_to_float(args[0])))

    def _cosh(args: list) -> object:
        return FV(_math.cosh(_to_float(args[0])))

    def _tanh(args: list) -> object:
        return FV(_math.tanh(_to_float(args[0])))

    def _gcd(args: list) -> object:
        a = _require_int(args[0], "math.gcd")
        b = _require_int(args[1], "math.gcd")
        return IV(_math.gcd(abs(a), abs(b)))

    def _lcm(args: list) -> object:
        a = _require_int(args[0], "math.lcm")
        b = _require_int(args[1], "math.lcm")
        return IV(_math.lcm(abs(a), abs(b)))

    def _sign(args: list) -> object:
        x = _to_float(args[0])
        if x > 0:
            return IV(1)
        if x < 0:
            return IV(-1)
        return IV(0)

    def _is_nan(args: list) -> object:
        interp2 = _interp()
        x = _to_float(args[0])
        return interp2.BoolValue(_math.isnan(x))  # type: ignore[attr-defined]

    def _is_inf(args: list) -> object:
        interp2 = _interp()
        x = _to_float(args[0])
        return interp2.BoolValue(_math.isinf(x))  # type: ignore[attr-defined]

    def _is_finite(args: list) -> object:
        interp2 = _interp()
        x = _to_float(args[0])
        return interp2.BoolValue(_math.isfinite(x))  # type: ignore[attr-defined]

    exports: dict[str, object] = {
        # Constants
        "pi": FV(_math.pi),
        "e": FV(_math.e),
        "tau": FV(_math.tau),
        "inf": FV(_math.inf),
        "nan": FV(_math.nan),
        # Basic numeric
        "abs": BF("abs", _abs, arity=1),
        "floor": BF("floor", _floor, arity=1),
        "ceil": BF("ceil", _ceil, arity=1),
        "round": BF("round", _round, arity=1),
        "sign": BF("sign", _sign, arity=1),
        "clamp": BF("clamp", _clamp, arity=3),
        "min": BF("min", _min, arity=2),
        "max": BF("max", _max, arity=2),
        # Power / logarithm
        "sqrt": BF("sqrt", _sqrt, arity=1),
        "pow": BF("pow", _pow, arity=2),
        "exp": BF("exp", _exp, arity=1),
        "log": BF("log", _log, arity=1),
        "log2": BF("log2", _log2, arity=1),
        "log10": BF("log10", _log10, arity=1),
        # Trigonometry
        "sin": BF("sin", _sin, arity=1),
        "cos": BF("cos", _cos, arity=1),
        "tan": BF("tan", _tan, arity=1),
        "asin": BF("asin", _asin, arity=1),
        "acos": BF("acos", _acos, arity=1),
        "atan": BF("atan", _atan, arity=1),
        "atan2": BF("atan2", _atan2, arity=2),
        # Hyperbolic
        "sinh": BF("sinh", _sinh, arity=1),
        "cosh": BF("cosh", _cosh, arity=1),
        "tanh": BF("tanh", _tanh, arity=1),
        # Integer operations
        "gcd": BF("gcd", _gcd, arity=2),
        "lcm": BF("lcm", _lcm, arity=2),
        # Classification
        "is_nan": BF("is_nan", _is_nan, arity=1),
        "is_inf": BF("is_inf", _is_inf, arity=1),
        "is_finite": BF("is_finite", _is_finite, arity=1),
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

    def _len(args: list) -> object:
        return IV(len(_require_string(args[0], "str.len")))

    def _is_empty(args: list) -> object:
        return BoolV(len(_require_string(args[0], "str.is_empty")) == 0)

    def _is_digit(args: list) -> object:
        return BoolV(_require_string(args[0], "str.is_digit").isdigit())

    def _is_alpha(args: list) -> object:
        return BoolV(_require_string(args[0], "str.is_alpha").isalpha())

    def _is_alnum(args: list) -> object:
        return BoolV(_require_string(args[0], "str.is_alnum").isalnum())

    def _is_space(args: list) -> object:
        return BoolV(_require_string(args[0], "str.is_space").isspace())

    def _to_int(args: list) -> object:
        s = _require_string(args[0], "str.to_int")
        try:
            return IV(int(s, 10))
        except ValueError as exc:
            raise interp.InterpreterError(  # type: ignore[attr-defined]
                f"str.to_int: cannot parse {s!r} as Int"
            ) from exc

    def _to_float(args: list) -> object:
        s = _require_string(args[0], "str.to_float")
        try:
            return interp.FloatValue(float(s))  # type: ignore[attr-defined]
        except ValueError as exc:
            raise interp.InterpreterError(  # type: ignore[attr-defined]
                f"str.to_float: cannot parse {s!r} as Float"
            ) from exc

    def _reverse(args: list) -> object:
        return SV(_require_string(args[0], "str.reverse")[::-1])

    def _count(args: list) -> object:
        s = _require_string(args[0], "str.count")
        sub = _require_string(args[1], "str.count")
        return IV(s.count(sub))

    def _title(args: list) -> object:
        return SV(_require_string(args[0], "str.title").title())

    def _format(args: list) -> object:
        """str.format(template, [arg, ...]) — replaces {} placeholders in order."""
        template = _require_string(args[0], "str.format")
        parts = template.split("{}")
        if len(parts) != len(args):
            raise interp.InterpreterError(  # type: ignore[attr-defined]
                f"str.format: expected {len(parts) - 1} argument(s), got {len(args) - 1}"
            )
        result = parts[0]
        for i, part in enumerate(parts[1:], 1):
            result += str(args[i]) + part
        return SV(result)

    exports: dict[str, object] = {
        # Inspection
        "len": BF("len", _len, arity=1),
        "is_empty": BF("is_empty", _is_empty, arity=1),
        "is_digit": BF("is_digit", _is_digit, arity=1),
        "is_alpha": BF("is_alpha", _is_alpha, arity=1),
        "is_alnum": BF("is_alnum", _is_alnum, arity=1),
        "is_space": BF("is_space", _is_space, arity=1),
        # Transformation
        "upper": BF("upper", _upper, arity=1),
        "lower": BF("lower", _lower, arity=1),
        "title": BF("title", _title, arity=1),
        "strip": BF("strip", _strip, arity=1),
        "lstrip": BF("lstrip", _lstrip, arity=1),
        "rstrip": BF("rstrip", _rstrip, arity=1),
        "reverse": BF("reverse", _reverse, arity=1),
        "repeat": BF("repeat", _repeat, arity=2),
        "replace": BF("replace", _replace, arity=3),
        "pad_left": BF("pad_left", _pad_left, arity=-1),
        "pad_right": BF("pad_right", _pad_right, arity=-1),
        # Splitting / joining
        "split": BF("split", _split, arity=2),
        "join": BF("join", _join, arity=2),
        "chars": BF("chars", _chars, arity=1),
        # Search
        "starts_with": BF("starts_with", _starts_with, arity=2),
        "ends_with": BF("ends_with", _ends_with, arity=2),
        "contains": BF("contains", _contains, arity=2),
        "find": BF("find", _find, arity=2),
        "count": BF("count", _count, arity=2),
        # Indexing
        "char_at": BF("char_at", _char_at, arity=2),
        "slice": BF("slice", _slice, arity=3),
        # Parsing
        "to_int": BF("to_int", _to_int, arity=1),
        "to_float": BF("to_float", _to_float, arity=1),
        # Formatting
        "format": BF("format", _format, arity=-1),
    }
    return MV("str", exports)


# ---------------------------------------------------------------------------
# std module
# ---------------------------------------------------------------------------


def _build_std_module() -> object:
    import os as _os  # noqa: PLC0415
    import sys as _sys  # noqa: PLC0415

    interp = _interp()
    SV = interp.StringValue  # type: ignore[attr-defined]
    LV = interp.ListValue  # type: ignore[attr-defined]
    NilV = interp.NilValue  # type: ignore[attr-defined]
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

    def _exit(args: list) -> object:
        code = _require_int(args[0], "std.exit") if args else 0
        _sys.exit(code)

    def _env(args: list) -> object:
        key = _require_string(args[0], "std.env")
        val = _os.environ.get(key)
        if val is None:
            return NilV()
        return SV(val)

    def _env_or(args: list) -> object:
        key = _require_string(args[0], "std.env_or")
        default = _require_string(args[1], "std.env_or")
        return SV(_os.environ.get(key, default))

    def _args(args: list) -> object:
        return LV(tuple(SV(a) for a in _sys.argv))

    def _assert_fn(args: list) -> object:
        if not args:
            raise IE("std.assert: requires at least one argument")
        cond = args[0]
        if not isinstance(cond, interp.BoolValue):  # type: ignore[attr-defined]
            raise IE(f"std.assert: expected Bool, got {type(cond).__name__}")
        if not cond.value:  # type: ignore[attr-defined]
            msg = _require_string(args[1], "std.assert") if len(args) > 1 else "assertion failed"
            raise IE(f"assert: {msg}")
        return NilV()

    exports: dict[str, object] = {
        "type_of": BF("type_of", _type_of, arity=1),
        "panic": BF("panic", _panic, arity=-1),
        "todo": BF("todo", _todo, arity=0),
        "input": BF("input", _input, arity=-1),
        "exit": BF("exit", _exit, arity=-1),
        "env": BF("env", _env, arity=1),
        "env_or": BF("env_or", _env_or, arity=2),
        "args": BF("args", _args, arity=0),
        "assert": BF("assert", _assert_fn, arity=-1),
    }
    return MV("std", exports)


# ---------------------------------------------------------------------------
# list module
# ---------------------------------------------------------------------------


def _build_list_module() -> object:
    """Higher-order list utilities: map, filter, reduce, sort, zip, etc."""
    interp = _interp()
    IV = interp.IntValue  # type: ignore[attr-defined]
    BoolV = interp.BoolValue  # type: ignore[attr-defined]
    LV = interp.ListValue  # type: ignore[attr-defined]
    BF = interp.BuiltinFunction  # type: ignore[attr-defined]
    MV = interp.ModuleValue  # type: ignore[attr-defined]
    IE = interp.InterpreterError  # type: ignore[attr-defined]
    FnV = interp.FunctionValue  # type: ignore[attr-defined]
    BuiltinFn = interp.BuiltinFunction  # type: ignore[attr-defined]

    def _require_list(v: object, label: str) -> tuple:
        if not isinstance(v, interp.ListValue):  # type: ignore[attr-defined]
            raise IE(f"{label}: expected List, got {type(v).__name__}")
        return v.elements  # type: ignore[attr-defined]

    def _call_fn(fn: object, args: list) -> object:
        """Call an Aster function or builtin with args."""
        if isinstance(fn, BuiltinFn):
            return fn.fn(args)  # type: ignore[attr-defined]
        if isinstance(fn, FnV):
            # Re-use the interpreter's call machinery via a private helper.
            # We need an Interpreter instance; we spawn a fresh one for purity.
            # This is safe because list.map etc. are pure higher-order ops.
            from aster_lang.interpreter import Interpreter as _Interp  # noqa: PLC0415

            tmp = _Interp()
            return tmp._call_function(fn, args)  # type: ignore[attr-defined]
        raise IE(f"list: expected a function, got {type(fn).__name__}")

    def _map(args: list) -> object:
        fn = args[0]
        elems = _require_list(args[1], "list.map")
        return LV(tuple(_call_fn(fn, [e]) for e in elems))

    def _filter(args: list) -> object:
        fn = args[0]
        elems = _require_list(args[1], "list.filter")
        result = []
        for e in elems:
            v = _call_fn(fn, [e])
            if not isinstance(v, interp.BoolValue):  # type: ignore[attr-defined]
                raise IE("list.filter: predicate must return Bool")
            if v.value:  # type: ignore[attr-defined]
                result.append(e)
        return LV(tuple(result))

    def _reduce(args: list) -> object:
        fn = args[0]
        elems = _require_list(args[1], "list.reduce")
        init = args[2]
        acc = init
        for e in elems:
            acc = _call_fn(fn, [acc, e])
        return acc

    def _sort(args: list) -> object:
        """sort(lst) — sort a list of comparable values (Int, Float, String)."""
        elems = list(_require_list(args[0], "list.sort"))

        def _key(v: object) -> object:
            if isinstance(v, (interp.IntValue, interp.BitsValue)):  # type: ignore[attr-defined]  # noqa: UP038
                return v.value  # type: ignore[attr-defined]
            if isinstance(v, interp.FloatValue):  # type: ignore[attr-defined]
                return v.value  # type: ignore[attr-defined]
            if isinstance(v, interp.StringValue):  # type: ignore[attr-defined]
                return v.value  # type: ignore[attr-defined]
            raise IE(f"list.sort: cannot compare {type(v).__name__}")

        return LV(tuple(sorted(elems, key=_key)))

    def _sort_by(args: list) -> object:
        """sort_by(key_fn, lst) — sort by applying key_fn to each element."""
        fn = args[0]
        elems = list(_require_list(args[1], "list.sort_by"))

        def _key(v: object) -> object:
            k = _call_fn(fn, [v])
            if isinstance(k, (interp.IntValue, interp.BitsValue)):  # type: ignore[attr-defined]  # noqa: UP038
                return k.value  # type: ignore[attr-defined]
            if isinstance(k, interp.FloatValue):  # type: ignore[attr-defined]
                return k.value  # type: ignore[attr-defined]
            if isinstance(k, interp.StringValue):  # type: ignore[attr-defined]
                return k.value  # type: ignore[attr-defined]
            raise IE("list.sort_by: key function must return a comparable value")

        return LV(tuple(sorted(elems, key=_key)))

    def _reverse(args: list) -> object:
        elems = _require_list(args[0], "list.reverse")
        return LV(tuple(reversed(elems)))

    def _zip(args: list) -> object:
        a = _require_list(args[0], "list.zip")
        b = _require_list(args[1], "list.zip")
        length = min(len(a), len(b))
        return LV(tuple(interp.TupleValue((a[i], b[i])) for i in range(length)))  # type: ignore[attr-defined]

    def _enumerate(args: list) -> object:
        elems = _require_list(args[0], "list.enumerate")
        return LV(
            tuple(interp.TupleValue((IV(i), e)) for i, e in enumerate(elems))  # type: ignore[attr-defined]
        )

    def _flatten(args: list) -> object:
        outer = _require_list(args[0], "list.flatten")
        result: list = []
        for item in outer:
            if isinstance(item, interp.ListValue):  # type: ignore[attr-defined]
                result.extend(item.elements)  # type: ignore[attr-defined]
            else:
                result.append(item)
        return LV(tuple(result))

    def _any(args: list) -> object:
        fn = args[0]
        elems = _require_list(args[1], "list.any")
        for e in elems:
            v = _call_fn(fn, [e])
            if not isinstance(v, interp.BoolValue):  # type: ignore[attr-defined]
                raise IE("list.any: predicate must return Bool")
            if v.value:  # type: ignore[attr-defined]
                return BoolV(True)
        return BoolV(False)

    def _all(args: list) -> object:
        fn = args[0]
        elems = _require_list(args[1], "list.all")
        for e in elems:
            v = _call_fn(fn, [e])
            if not isinstance(v, interp.BoolValue):  # type: ignore[attr-defined]
                raise IE("list.all: predicate must return Bool")
            if not v.value:  # type: ignore[attr-defined]
                return BoolV(False)
        return BoolV(True)

    def _sum(args: list) -> object:
        elems = _require_list(args[0], "list.sum")
        total: float = 0.0
        all_int = True
        for e in elems:
            if isinstance(e, interp.FloatValue):  # type: ignore[attr-defined]
                all_int = False
                total += e.value  # type: ignore[attr-defined]
            elif isinstance(e, (interp.IntValue, interp.BitsValue)):  # type: ignore[attr-defined]  # noqa: UP038
                total += e.value  # type: ignore[attr-defined]
            else:
                raise IE(f"list.sum: cannot sum {type(e).__name__}")
        return IV(int(total)) if all_int else interp.FloatValue(total)  # type: ignore[attr-defined]

    def _product(args: list) -> object:
        elems = _require_list(args[0], "list.product")
        result: float = 1.0
        all_int = True
        for e in elems:
            if isinstance(e, interp.FloatValue):  # type: ignore[attr-defined]
                all_int = False
                result *= e.value  # type: ignore[attr-defined]
            elif isinstance(e, (interp.IntValue, interp.BitsValue)):  # type: ignore[attr-defined]  # noqa: UP038
                result *= e.value  # type: ignore[attr-defined]
            else:
                raise IE(f"list.product: cannot multiply {type(e).__name__}")
        return IV(int(result)) if all_int else interp.FloatValue(result)  # type: ignore[attr-defined]

    def _contains(args: list) -> object:
        elems = _require_list(args[0], "list.contains")
        target = args[1]
        for e in elems:
            if str(e) == str(target) and type(e) is type(target):
                return BoolV(True)
        return BoolV(False)

    def _unique(args: list) -> object:
        elems = _require_list(args[0], "list.unique")
        seen: list = []
        seen_keys: list = []
        for e in elems:
            key = (type(e).__name__, str(e))
            if key not in seen_keys:
                seen_keys.append(key)
                seen.append(e)
        return LV(tuple(seen))

    def _head(args: list) -> object:
        elems = _require_list(args[0], "list.head")
        if not elems:
            raise IE("list.head: list is empty")
        return elems[0]

    def _tail(args: list) -> object:
        elems = _require_list(args[0], "list.tail")
        if not elems:
            raise IE("list.tail: list is empty")
        return LV(elems[1:])

    def _last(args: list) -> object:
        elems = _require_list(args[0], "list.last")
        if not elems:
            raise IE("list.last: list is empty")
        return elems[-1]

    def _count(args: list) -> object:
        fn = args[0]
        elems = _require_list(args[1], "list.count")
        n = 0
        for e in elems:
            v = _call_fn(fn, [e])
            if not isinstance(v, interp.BoolValue):  # type: ignore[attr-defined]
                raise IE("list.count: predicate must return Bool")
            if v.value:  # type: ignore[attr-defined]
                n += 1
        return IV(n)

    def _take(args: list) -> object:
        n = _require_int(args[0], "list.take")
        elems = _require_list(args[1], "list.take")
        return LV(elems[:n])

    def _drop(args: list) -> object:
        n = _require_int(args[0], "list.drop")
        elems = _require_list(args[1], "list.drop")
        return LV(elems[n:])

    def _append(args: list) -> object:
        elems = _require_list(args[0], "list.append")
        elem = args[1]
        return LV(elems + (elem,))

    def _prepend(args: list) -> object:
        elem = args[0]
        elems = _require_list(args[1], "list.prepend")
        return LV((elem,) + elems)

    def _concat(args: list) -> object:
        a = _require_list(args[0], "list.concat")
        b = _require_list(args[1], "list.concat")
        return LV(a + b)

    def _len(args: list) -> object:
        return IV(len(_require_list(args[0], "list.len")))

    def _range(args: list) -> object:
        """range(start, end) or range(end) — produce an integer list."""
        if len(args) == 1:
            start, end = 0, _require_int(args[0], "list.range")
        else:
            start = _require_int(args[0], "list.range")
            end = _require_int(args[1], "list.range")
        return LV(tuple(IV(i) for i in range(start, end)))

    def _repeat(args: list) -> object:
        """repeat(value, n) — produce a list of n copies of value."""
        val = args[0]
        n = _require_int(args[1], "list.repeat")
        return LV(tuple(val for _ in range(n)))

    exports: dict[str, object] = {
        # Higher-order
        "map": BF("map", _map, arity=2),
        "filter": BF("filter", _filter, arity=2),
        "reduce": BF("reduce", _reduce, arity=3),
        "any": BF("any", _any, arity=2),
        "all": BF("all", _all, arity=2),
        "count": BF("count", _count, arity=2),
        "sort": BF("sort", _sort, arity=1),
        "sort_by": BF("sort_by", _sort_by, arity=2),
        # Aggregate
        "sum": BF("sum", _sum, arity=1),
        "product": BF("product", _product, arity=1),
        # Construction
        "range": BF("range", _range, arity=-1),
        "repeat": BF("repeat", _repeat, arity=2),
        "append": BF("append", _append, arity=2),
        "prepend": BF("prepend", _prepend, arity=2),
        "concat": BF("concat", _concat, arity=2),
        # Access
        "head": BF("head", _head, arity=1),
        "tail": BF("tail", _tail, arity=1),
        "last": BF("last", _last, arity=1),
        "take": BF("take", _take, arity=2),
        "drop": BF("drop", _drop, arity=2),
        "len": BF("len", _len, arity=1),
        # Transformation
        "reverse": BF("reverse", _reverse, arity=1),
        "flatten": BF("flatten", _flatten, arity=1),
        "zip": BF("zip", _zip, arity=2),
        "enumerate": BF("enumerate", _enumerate, arity=1),
        "unique": BF("unique", _unique, arity=1),
        "contains": BF("contains", _contains, arity=2),
    }
    return MV("list", exports)


# ---------------------------------------------------------------------------
# io module
# ---------------------------------------------------------------------------


def _build_io_module() -> object:
    """File and stream I/O operations."""
    import sys as _sys  # noqa: PLC0415
    from pathlib import Path as _Path  # noqa: PLC0415

    interp = _interp()
    SV = interp.StringValue  # type: ignore[attr-defined]
    BoolV = interp.BoolValue  # type: ignore[attr-defined]
    LV = interp.ListValue  # type: ignore[attr-defined]
    NilV = interp.NilValue  # type: ignore[attr-defined]
    BF = interp.BuiltinFunction  # type: ignore[attr-defined]
    MV = interp.ModuleValue  # type: ignore[attr-defined]
    IE = interp.InterpreterError  # type: ignore[attr-defined]

    def _read_file(args: list) -> object:
        path = _require_string(args[0], "io.read_file")
        try:
            return SV(_Path(path).read_text(encoding="utf-8"))
        except OSError as exc:
            raise IE(f"io.read_file: {exc}") from exc

    def _write_file(args: list) -> object:
        path = _require_string(args[0], "io.write_file")
        content = _require_string(args[1], "io.write_file")
        try:
            _Path(path).write_text(content, encoding="utf-8")
        except OSError as exc:
            raise IE(f"io.write_file: {exc}") from exc
        return NilV()

    def _append_file(args: list) -> object:
        path = _require_string(args[0], "io.append_file")
        content = _require_string(args[1], "io.append_file")
        try:
            with _Path(path).open("a", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            raise IE(f"io.append_file: {exc}") from exc
        return NilV()

    def _file_exists(args: list) -> object:
        path = _require_string(args[0], "io.file_exists")
        return BoolV(_Path(path).exists())

    def _is_file(args: list) -> object:
        path = _require_string(args[0], "io.is_file")
        return BoolV(_Path(path).is_file())

    def _is_dir(args: list) -> object:
        path = _require_string(args[0], "io.is_dir")
        return BoolV(_Path(path).is_dir())

    def _delete_file(args: list) -> object:
        path = _require_string(args[0], "io.delete_file")
        try:
            _Path(path).unlink()
        except OSError as exc:
            raise IE(f"io.delete_file: {exc}") from exc
        return NilV()

    def _list_dir(args: list) -> object:
        path = _require_string(args[0], "io.list_dir")
        try:
            entries = sorted(str(p.name) for p in _Path(path).iterdir())
            return LV(tuple(SV(e) for e in entries))
        except OSError as exc:
            raise IE(f"io.list_dir: {exc}") from exc

    def _mkdir(args: list) -> object:
        path = _require_string(args[0], "io.mkdir")
        try:
            _Path(path).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise IE(f"io.mkdir: {exc}") from exc
        return NilV()

    def _print_err(args: list) -> object:
        msg = _require_string(args[0], "io.print_err")
        print(msg, file=_sys.stderr)
        return NilV()

    def _walk_dir(args: list) -> object:
        """walk_dir(root) — recursively walk a directory tree.

        Returns a List of Records, one per entry, each with fields:
          path   : String  — path relative to root (using '/' separator)
          is_dir : Bool    — True if the entry is a directory
          name   : String  — the entry's filename component only
        """
        root = _require_string(args[0], "io.walk_dir")
        root_path = _Path(root)
        if not root_path.exists():
            raise IE(f"io.walk_dir: path does not exist: {root!r}")
        if not root_path.is_dir():
            raise IE(f"io.walk_dir: not a directory: {root!r}")
        results: list = []
        try:
            for entry in sorted(root_path.rglob("*"), key=lambda p: str(p)):
                rel = entry.relative_to(root_path)
                rel_str = str(rel).replace("\\", "/")
                record = interp.RecordValue(  # type: ignore[attr-defined]
                    {
                        "path": SV(rel_str),
                        "is_dir": BoolV(entry.is_dir()),
                        "name": SV(entry.name),
                    }
                )
                results.append(record)
        except OSError as exc:
            raise IE(f"io.walk_dir: {exc}") from exc
        return LV(tuple(results))

    def _read_lines(args: list) -> object:
        path = _require_string(args[0], "io.read_lines")
        try:
            lines = _Path(path).read_text(encoding="utf-8").splitlines()
            return LV(tuple(SV(ln) for ln in lines))
        except OSError as exc:
            raise IE(f"io.read_lines: {exc}") from exc

    def _write_lines(args: list) -> object:
        path = _require_string(args[0], "io.write_lines")
        if not isinstance(args[1], interp.ListValue):  # type: ignore[attr-defined]
            raise IE("io.write_lines: second argument must be a List")
        lines = [_require_string(e, "io.write_lines element") for e in args[1].elements]  # type: ignore[attr-defined]
        try:
            _Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            raise IE(f"io.write_lines: {exc}") from exc
        return NilV()

    exports: dict[str, object] = {
        "read_file": BF("read_file", _read_file, arity=1),
        "write_file": BF("write_file", _write_file, arity=2),
        "append_file": BF("append_file", _append_file, arity=2),
        "read_lines": BF("read_lines", _read_lines, arity=1),
        "write_lines": BF("write_lines", _write_lines, arity=2),
        "file_exists": BF("file_exists", _file_exists, arity=1),
        "is_file": BF("is_file", _is_file, arity=1),
        "is_dir": BF("is_dir", _is_dir, arity=1),
        "delete_file": BF("delete_file", _delete_file, arity=1),
        "list_dir": BF("list_dir", _list_dir, arity=1),
        "walk_dir": BF("walk_dir", _walk_dir, arity=1),
        "mkdir": BF("mkdir", _mkdir, arity=1),
        "print_err": BF("print_err", _print_err, arity=1),
    }
    return MV("io", exports)


# ---------------------------------------------------------------------------
# random module
# ---------------------------------------------------------------------------


def _build_random_module() -> object:
    """Pseudo-random number generation."""
    import random as _random  # noqa: PLC0415

    interp = _interp()
    IV = interp.IntValue  # type: ignore[attr-defined]
    FV = interp.FloatValue  # type: ignore[attr-defined]
    LV = interp.ListValue  # type: ignore[attr-defined]
    NilV = interp.NilValue  # type: ignore[attr-defined]
    BF = interp.BuiltinFunction  # type: ignore[attr-defined]
    MV = interp.ModuleValue  # type: ignore[attr-defined]
    IE = interp.InterpreterError  # type: ignore[attr-defined]

    def _random_fn(args: list) -> object:
        """random() — uniform float in [0.0, 1.0)."""
        return FV(_random.random())

    def _rand_int(args: list) -> object:
        """rand_int(low, high) — random Int in [low, high] inclusive."""
        lo = _require_int(args[0], "random.rand_int")
        hi = _require_int(args[1], "random.rand_int")
        if lo > hi:
            raise IE(f"random.rand_int: low ({lo}) must be <= high ({hi})")
        return IV(_random.randint(lo, hi))

    def _rand_float(args: list) -> object:
        """rand_float(low, high) — uniform float in [low, high)."""
        lo = _to_float(args[0])
        hi = _to_float(args[1])
        return FV(_random.uniform(lo, hi))

    def _choice(args: list) -> object:
        if not isinstance(args[0], interp.ListValue):  # type: ignore[attr-defined]
            raise IE("random.choice: expected a List")
        elems = args[0].elements  # type: ignore[attr-defined]
        if not elems:
            raise IE("random.choice: list is empty")
        return _random.choice(elems)

    def _shuffle(args: list) -> object:
        if not isinstance(args[0], interp.ListValue):  # type: ignore[attr-defined]
            raise IE("random.shuffle: expected a List")
        elems = list(args[0].elements)  # type: ignore[attr-defined]
        _random.shuffle(elems)
        return interp.ListValue(tuple(elems))  # type: ignore[attr-defined]

    def _sample(args: list) -> object:
        if not isinstance(args[0], interp.ListValue):  # type: ignore[attr-defined]
            raise IE("random.sample: first argument must be a List")
        k = _require_int(args[1], "random.sample")
        elems = list(args[0].elements)  # type: ignore[attr-defined]
        if k > len(elems):
            raise IE(f"random.sample: sample size ({k}) larger than population ({len(elems)})")
        return LV(tuple(_random.sample(elems, k)))

    def _seed(args: list) -> object:
        n = _require_int(args[0], "random.seed")
        _random.seed(n)
        return NilV()

    exports: dict[str, object] = {
        "random": BF("random", _random_fn, arity=0),
        "rand_int": BF("rand_int", _rand_int, arity=2),
        "rand_float": BF("rand_float", _rand_float, arity=2),
        "choice": BF("choice", _choice, arity=1),
        "shuffle": BF("shuffle", _shuffle, arity=1),
        "sample": BF("sample", _sample, arity=2),
        "seed": BF("seed", _seed, arity=1),
    }
    return MV("random", exports)


# ---------------------------------------------------------------------------
# time module
# ---------------------------------------------------------------------------


def _build_time_module() -> object:
    """Time and timing utilities."""
    import time as _time  # noqa: PLC0415

    interp = _interp()
    IV = interp.IntValue  # type: ignore[attr-defined]
    FV = interp.FloatValue  # type: ignore[attr-defined]
    SV = interp.StringValue  # type: ignore[attr-defined]
    NilV = interp.NilValue  # type: ignore[attr-defined]
    BF = interp.BuiltinFunction  # type: ignore[attr-defined]
    MV = interp.ModuleValue  # type: ignore[attr-defined]

    def _now(args: list) -> object:
        """now() — current Unix timestamp as Float (seconds since epoch)."""
        return FV(_time.time())

    def _now_ms(args: list) -> object:
        """now_ms() — current timestamp in integer milliseconds."""
        return IV(int(_time.time() * 1000))

    def _monotonic(args: list) -> object:
        """monotonic() — monotonic clock Float, for measuring intervals."""
        return FV(_time.monotonic())

    def _sleep(args: list) -> object:
        """sleep(seconds) — pause execution for the given number of seconds."""
        secs = _to_float(args[0])
        _time.sleep(secs)
        return NilV()

    def _strftime(args: list) -> object:
        """strftime(fmt) — format the current local time using strftime format string."""
        fmt = _require_string(args[0], "time.strftime")
        return SV(_time.strftime(fmt, _time.localtime()))

    def _clock(args: list) -> object:
        """clock() — CPU process time in seconds (Float)."""
        return FV(_time.process_time())

    exports: dict[str, object] = {
        "now": BF("now", _now, arity=0),
        "now_ms": BF("now_ms", _now_ms, arity=0),
        "monotonic": BF("monotonic", _monotonic, arity=0),
        "sleep": BF("sleep", _sleep, arity=1),
        "strftime": BF("strftime", _strftime, arity=1),
        "clock": BF("clock", _clock, arity=0),
    }
    return MV("time", exports)


# ---------------------------------------------------------------------------
# linalg module
# ---------------------------------------------------------------------------


def _build_linalg_module() -> object:
    """Linear algebra: vectors and matrices backed by plain Aster lists."""
    interp = _interp()
    IV = interp.IntValue  # type: ignore[attr-defined]
    LV = interp.ListValue  # type: ignore[attr-defined]
    BF = interp.BuiltinFunction  # type: ignore[attr-defined]
    MV = interp.ModuleValue  # type: ignore[attr-defined]
    IE = interp.InterpreterError  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Python-level helpers
    # ------------------------------------------------------------------

    def _v2py(v: object) -> list:
        """ListValue of numerics → list[float]."""
        if not isinstance(v, interp.ListValue):  # type: ignore[attr-defined]
            raise IE("linalg: expected a vector (List), got " + type(v).__name__)
        return [_to_float(e) for e in v.elements]  # type: ignore[attr-defined]

    def _py2v(xs: list) -> object:
        """list[float] → ListValue, using Int when value is whole."""
        return LV(tuple(_int_or_float(x) for x in xs))

    def _m2py(m: object) -> list:
        """ListValue of ListValues → list[list[float]]."""
        if not isinstance(m, interp.ListValue):  # type: ignore[attr-defined]
            raise IE("linalg: expected a matrix (List of Lists), got " + type(m).__name__)
        rows = []
        for i, row in enumerate(m.elements):  # type: ignore[attr-defined]
            if not isinstance(row, interp.ListValue):  # type: ignore[attr-defined]
                raise IE(f"linalg: matrix row {i} must be a List")
            rows.append([_to_float(e) for e in row.elements])  # type: ignore[attr-defined]
        return rows

    def _py2m(rows: list) -> object:
        """list[list[float]] → ListValue of ListValues."""
        return LV(tuple(_py2v(row) for row in rows))

    def _check_same_dim(a: list, b: list, name: str) -> None:
        if len(a) != len(b):
            raise IE(f"linalg.{name}: dimension mismatch ({len(a)} vs {len(b)})")

    def _check_same_shape(a: list, b: list, name: str) -> None:
        ra, rb = len(a), len(b)
        if ra != rb or (ra > 0 and len(a[0]) != len(b[0])):
            raise IE(
                f"linalg.{name}: shape mismatch "
                f"({ra}×{len(a[0]) if ra else 0} vs {rb}×{len(b[0]) if rb else 0})"
            )

    def _require_square(m: list, name: str) -> int:
        n = len(m)
        if n == 0:
            raise IE(f"linalg.{name}: empty matrix")
        for i, row in enumerate(m):
            if len(row) != n:
                raise IE(
                    f"linalg.{name}: matrix must be square "
                    f"(row {i} has {len(row)} cols, expected {n})"
                )
        return n

    def _det_py(m: list) -> float:
        """Determinant via cofactor expansion."""
        n = len(m)
        if n == 1:
            return m[0][0]
        if n == 2:
            return m[0][0] * m[1][1] - m[0][1] * m[1][0]
        result = 0.0
        for j in range(n):
            minor = [[m[r][c] for c in range(n) if c != j] for r in range(1, n)]
            result += ((-1.0) ** j) * m[0][j] * _det_py(minor)
        return result

    def _inv_py(m: list) -> list:
        """Matrix inverse via Gaussian elimination with partial pivoting."""
        n = len(m)
        aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
        for col in range(n):
            pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
            aug[col], aug[pivot] = aug[pivot], aug[col]
            if abs(aug[col][col]) < 1e-12:
                raise IE("linalg.minv: matrix is singular (no inverse)")
            div = aug[col][col]
            aug[col] = [x / div for x in aug[col]]
            for row in range(n):
                if row != col:
                    factor = aug[row][col]
                    aug[row] = [aug[row][k] - factor * aug[col][k] for k in range(2 * n)]
        return [row[n:] for row in aug]

    # ------------------------------------------------------------------
    # Vector functions
    # ------------------------------------------------------------------

    def _vec(args: list) -> object:
        """vec(x, y, ...) — construct a vector from scalar components."""
        if not args:
            raise IE("linalg.vec: requires at least one component")
        return _py2v([_to_float(a) for a in args])

    def _vdim(args: list) -> object:
        v = _v2py(args[0])
        return IV(len(v))

    def _vadd(args: list) -> object:
        a, b = _v2py(args[0]), _v2py(args[1])
        _check_same_dim(a, b, "vadd")
        return _py2v([x + y for x, y in zip(a, b, strict=True)])

    def _vsub(args: list) -> object:
        a, b = _v2py(args[0]), _v2py(args[1])
        _check_same_dim(a, b, "vsub")
        return _py2v([x - y for x, y in zip(a, b, strict=True)])

    def _vmul(args: list) -> object:
        """Element-wise (Hadamard) product."""
        a, b = _v2py(args[0]), _v2py(args[1])
        _check_same_dim(a, b, "vmul")
        return _py2v([x * y for x, y in zip(a, b, strict=True)])

    def _vscale(args: list) -> object:
        v = _v2py(args[0])
        s = _to_float(args[1])
        return _py2v([x * s for x in v])

    def _vdot(args: list) -> object:
        a, b = _v2py(args[0]), _v2py(args[1])
        _check_same_dim(a, b, "vdot")
        return _int_or_float(sum(x * y for x, y in zip(a, b, strict=True)))

    def _vcross(args: list) -> object:
        a, b = _v2py(args[0]), _v2py(args[1])
        if len(a) != 3 or len(b) != 3:
            raise IE("linalg.vcross: cross product requires 3-dimensional vectors")
        return _py2v(
            [
                a[1] * b[2] - a[2] * b[1],
                a[2] * b[0] - a[0] * b[2],
                a[0] * b[1] - a[1] * b[0],
            ]
        )

    def _vlen(args: list) -> object:
        v = _v2py(args[0])
        return _int_or_float(_math.sqrt(sum(x * x for x in v)))

    def _vlen_sq(args: list) -> object:
        v = _v2py(args[0])
        return _int_or_float(sum(x * x for x in v))

    def _vnorm(args: list) -> object:
        v = _v2py(args[0])
        length = _math.sqrt(sum(x * x for x in v))
        if length < 1e-15:
            raise IE("linalg.vnorm: cannot normalize zero-length vector")
        return _py2v([x / length for x in v])

    def _vneg(args: list) -> object:
        return _py2v([-x for x in _v2py(args[0])])

    def _vlerp(args: list) -> object:
        a, b = _v2py(args[0]), _v2py(args[1])
        t = _to_float(args[2])
        _check_same_dim(a, b, "vlerp")
        return _py2v([x + t * (y - x) for x, y in zip(a, b, strict=True)])

    # ------------------------------------------------------------------
    # Matrix functions
    # ------------------------------------------------------------------

    def _mat(args: list) -> object:
        """mat(row0, row1, ...) — construct a matrix from row vectors (Lists)."""
        if not args:
            raise IE("linalg.mat: requires at least one row")
        rows = [_v2py(a) for a in args]
        ncols = len(rows[0])
        for i, row in enumerate(rows[1:], 1):
            if len(row) != ncols:
                raise IE(f"linalg.mat: row {i} has {len(row)} columns, expected {ncols}")
        return _py2m(rows)

    def _identity(args: list) -> object:
        n = _require_int(args[0], "linalg.identity")
        if n <= 0:
            raise IE("linalg.identity: size must be positive")
        return _py2m([[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)])

    def _mrows(args: list) -> object:
        return IV(len(_m2py(args[0])))

    def _mcols(args: list) -> object:
        m = _m2py(args[0])
        return IV(len(m[0]) if m else 0)

    def _mget(args: list) -> object:
        m = _m2py(args[0])
        i = _require_int(args[1], "linalg.mget")
        j = _require_int(args[2], "linalg.mget")
        if i < 0 or i >= len(m):
            raise IE(f"linalg.mget: row index {i} out of bounds")
        if j < 0 or j >= len(m[i]):
            raise IE(f"linalg.mget: col index {j} out of bounds")
        return _int_or_float(m[i][j])

    def _mrow(args: list) -> object:
        m = _m2py(args[0])
        i = _require_int(args[1], "linalg.mrow")
        if i < 0 or i >= len(m):
            raise IE(f"linalg.mrow: row index {i} out of bounds")
        return _py2v(m[i])

    def _mcol(args: list) -> object:
        m = _m2py(args[0])
        j = _require_int(args[1], "linalg.mcol")
        if not m or j < 0 or j >= len(m[0]):
            raise IE(f"linalg.mcol: col index {j} out of bounds")
        return _py2v([m[i][j] for i in range(len(m))])

    def _madd(args: list) -> object:
        a, b = _m2py(args[0]), _m2py(args[1])
        _check_same_shape(a, b, "madd")
        return _py2m([[a[i][j] + b[i][j] for j in range(len(a[i]))] for i in range(len(a))])

    def _msub(args: list) -> object:
        a, b = _m2py(args[0]), _m2py(args[1])
        _check_same_shape(a, b, "msub")
        return _py2m([[a[i][j] - b[i][j] for j in range(len(a[i]))] for i in range(len(a))])

    def _mscale(args: list) -> object:
        m = _m2py(args[0])
        s = _to_float(args[1])
        return _py2m([[v * s for v in row] for row in m])

    def _mmul(args: list) -> object:
        a, b = _m2py(args[0]), _m2py(args[1])
        ra, ca = len(a), len(a[0]) if a else 0
        rb, cb = len(b), len(b[0]) if b else 0
        if ca != rb:
            raise IE(f"linalg.mmul: incompatible shapes ({ra}×{ca} · {rb}×{cb})")
        result = [[sum(a[i][k] * b[k][j] for k in range(ca)) for j in range(cb)] for i in range(ra)]
        return _py2m(result)

    def _mvmul(args: list) -> object:
        """Matrix × column-vector."""
        m = _m2py(args[0])
        v = _v2py(args[1])
        cols = len(m[0]) if m else 0
        if len(v) != cols:
            raise IE(f"linalg.mvmul: matrix has {cols} cols but vector has {len(v)} components")
        return _py2v([sum(m[i][k] * v[k] for k in range(cols)) for i in range(len(m))])

    def _mtranspose(args: list) -> object:
        m = _m2py(args[0])
        if not m:
            return _py2m([])
        rows, cols = len(m), len(m[0])
        return _py2m([[m[r][c] for r in range(rows)] for c in range(cols)])

    def _mdet(args: list) -> object:
        m = _m2py(args[0])
        _require_square(m, "mdet")
        return _int_or_float(_det_py(m))

    def _minv(args: list) -> object:
        m = _m2py(args[0])
        _require_square(m, "minv")
        return _py2m(_inv_py(m))

    exports: dict[str, object] = {
        # Vectors
        "vec": BF("vec", _vec, arity=-1),
        "vdim": BF("vdim", _vdim, arity=1),
        "vadd": BF("vadd", _vadd, arity=2),
        "vsub": BF("vsub", _vsub, arity=2),
        "vmul": BF("vmul", _vmul, arity=2),
        "vscale": BF("vscale", _vscale, arity=2),
        "vdot": BF("vdot", _vdot, arity=2),
        "vcross": BF("vcross", _vcross, arity=2),
        "vlen": BF("vlen", _vlen, arity=1),
        "vlen_sq": BF("vlen_sq", _vlen_sq, arity=1),
        "vnorm": BF("vnorm", _vnorm, arity=1),
        "vneg": BF("vneg", _vneg, arity=1),
        "vlerp": BF("vlerp", _vlerp, arity=3),
        # Matrices
        "mat": BF("mat", _mat, arity=-1),
        "identity": BF("identity", _identity, arity=1),
        "mrows": BF("mrows", _mrows, arity=1),
        "mcols": BF("mcols", _mcols, arity=1),
        "mget": BF("mget", _mget, arity=3),
        "mrow": BF("mrow", _mrow, arity=2),
        "mcol": BF("mcol", _mcol, arity=2),
        "madd": BF("madd", _madd, arity=2),
        "msub": BF("msub", _msub, arity=2),
        "mscale": BF("mscale", _mscale, arity=2),
        "mmul": BF("mmul", _mmul, arity=2),
        "mvmul": BF("mvmul", _mvmul, arity=2),
        "mtranspose": BF("mtranspose", _mtranspose, arity=1),
        "mdet": BF("mdet", _mdet, arity=1),
        "minv": BF("minv", _minv, arity=1),
    }
    return MV("linalg", exports)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

NATIVE_MODULES: dict[str, Callable[[], object]] = {
    "math": _build_math_module,
    "str": _build_str_module,
    "std": _build_std_module,
    "list": _build_list_module,
    "io": _build_io_module,
    "random": _build_random_module,
    "time": _build_time_module,
    "linalg": _build_linalg_module,
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
        # Constants
        "pi": _const("pi", FLOAT),
        "e": _const("e", FLOAT),
        "tau": _const("tau", FLOAT),
        "inf": _const("inf", FLOAT),
        "nan": _const("nan", FLOAT),
        # Basic numeric
        "abs": _sym("abs", ret_unk),
        "floor": _sym("floor", ret_int),
        "ceil": _sym("ceil", ret_int),
        "round": _sym("round", ret_int),
        "sign": _sym("sign", ret_int),
        "clamp": _sym("clamp", ret_unk),
        "min": _sym("min", ret_unk),
        "max": _sym("max", ret_unk),
        # Power / logarithm
        "sqrt": _sym("sqrt", ret_float),
        "pow": _sym("pow", ret_unk),
        "exp": _sym("exp", ret_float),
        "log": _sym("log", ret_float),
        "log2": _sym("log2", ret_float),
        "log10": _sym("log10", ret_float),
        # Trigonometry
        "sin": _sym("sin", ret_float),
        "cos": _sym("cos", ret_float),
        "tan": _sym("tan", ret_float),
        "asin": _sym("asin", ret_float),
        "acos": _sym("acos", ret_float),
        "atan": _sym("atan", ret_float),
        "atan2": _sym("atan2", ret_float),
        # Hyperbolic
        "sinh": _sym("sinh", ret_float),
        "cosh": _sym("cosh", ret_float),
        "tanh": _sym("tanh", ret_float),
        # Integer operations
        "gcd": _sym("gcd", ret_int),
        "lcm": _sym("lcm", ret_int),
        # Classification
        "is_nan": _sym("is_nan", ret_bool),
        "is_inf": _sym("is_inf", ret_bool),
        "is_finite": _sym("is_finite", ret_bool),
    }

    ret_any_list = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=ListType(UNKNOWN_TYPE))

    str_syms = {
        # Inspection
        "len": _sym("len", ret_int),
        "is_empty": _sym("is_empty", ret_bool),
        "is_digit": _sym("is_digit", ret_bool),
        "is_alpha": _sym("is_alpha", ret_bool),
        "is_alnum": _sym("is_alnum", ret_bool),
        "is_space": _sym("is_space", ret_bool),
        # Transformation
        "upper": _sym("upper", ret_str),
        "lower": _sym("lower", ret_str),
        "title": _sym("title", ret_str),
        "strip": _sym("strip", ret_str),
        "lstrip": _sym("lstrip", ret_str),
        "rstrip": _sym("rstrip", ret_str),
        "reverse": _sym("reverse", ret_str),
        "repeat": _sym("repeat", ret_str),
        "replace": _sym("replace", ret_str),
        "pad_left": _sym("pad_left", ret_str),
        "pad_right": _sym("pad_right", ret_str),
        # Splitting / joining
        "split": _sym("split", ret_list),
        "join": _sym("join", ret_str),
        "chars": _sym("chars", ret_list),
        # Search
        "starts_with": _sym("starts_with", ret_bool),
        "ends_with": _sym("ends_with", ret_bool),
        "contains": _sym("contains", ret_bool),
        "find": _sym("find", ret_int),
        "count": _sym("count", ret_int),
        # Indexing
        "char_at": _sym("char_at", ret_str),
        "slice": _sym("slice", ret_str),
        # Parsing
        "to_int": _sym("to_int", ret_int),
        "to_float": _sym("to_float", ret_float),
        # Formatting
        "format": _sym("format", ret_str),
    }

    nil_fn = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=NIL_TYPE)
    std_syms = {
        "type_of": _sym("type_of", ret_str),
        "panic": _sym("panic", nil_fn),
        "todo": _sym("todo", FunctionType(param_types=(), return_type=NIL_TYPE)),
        "input": _sym("input", ret_str),
        "exit": _sym("exit", nil_fn),
        "env": _sym("env", ret_unk),
        "env_or": _sym("env_or", ret_str),
        "args": _sym("args", ret_list),
        "assert": _sym("assert", nil_fn),
    }

    list_syms = {
        # Higher-order
        "map": _sym("map", ret_any_list),
        "filter": _sym("filter", ret_any_list),
        "reduce": _sym("reduce", ret_unk),
        "any": _sym("any", ret_bool),
        "all": _sym("all", ret_bool),
        "count": _sym("count", ret_int),
        "sort": _sym("sort", ret_any_list),
        "sort_by": _sym("sort_by", ret_any_list),
        # Aggregate
        "sum": _sym("sum", ret_unk),
        "product": _sym("product", ret_unk),
        # Construction
        "range": _sym("range", ret_any_list),
        "repeat": _sym("repeat", ret_any_list),
        "append": _sym("append", ret_any_list),
        "prepend": _sym("prepend", ret_any_list),
        "concat": _sym("concat", ret_any_list),
        # Access
        "head": _sym("head", ret_unk),
        "tail": _sym("tail", ret_any_list),
        "last": _sym("last", ret_unk),
        "take": _sym("take", ret_any_list),
        "drop": _sym("drop", ret_any_list),
        "len": _sym("len", ret_int),
        # Transformation
        "reverse": _sym("reverse", ret_any_list),
        "flatten": _sym("flatten", ret_any_list),
        "zip": _sym("zip", ret_any_list),
        "enumerate": _sym("enumerate", ret_any_list),
        "unique": _sym("unique", ret_any_list),
        "contains": _sym("contains", ret_bool),
    }

    io_syms = {
        "read_file": _sym("read_file", ret_str),
        "write_file": _sym("write_file", nil_fn),
        "append_file": _sym("append_file", nil_fn),
        "read_lines": _sym("read_lines", ret_list),
        "write_lines": _sym("write_lines", nil_fn),
        "file_exists": _sym("file_exists", ret_bool),
        "is_file": _sym("is_file", ret_bool),
        "is_dir": _sym("is_dir", ret_bool),
        "delete_file": _sym("delete_file", nil_fn),
        "list_dir": _sym("list_dir", ret_list),
        "walk_dir": _sym("walk_dir", ret_any_list),
        "mkdir": _sym("mkdir", nil_fn),
        "print_err": _sym("print_err", nil_fn),
    }

    random_syms = {
        "random": _sym("random", ret_float),
        "rand_int": _sym("rand_int", ret_int),
        "rand_float": _sym("rand_float", ret_float),
        "choice": _sym("choice", ret_unk),
        "shuffle": _sym("shuffle", ret_any_list),
        "sample": _sym("sample", ret_any_list),
        "seed": _sym("seed", nil_fn),
    }

    time_syms = {
        "now": _sym("now", ret_float),
        "now_ms": _sym("now_ms", ret_int),
        "monotonic": _sym("monotonic", ret_float),
        "sleep": _sym("sleep", nil_fn),
        "strftime": _sym("strftime", ret_str),
        "clock": _sym("clock", ret_float),
    }

    ret_vec = FunctionType(param_types=(UNKNOWN_TYPE,), return_type=ListType(UNKNOWN_TYPE))
    ret_mat = FunctionType(
        param_types=(UNKNOWN_TYPE,), return_type=ListType(ListType(UNKNOWN_TYPE))
    )

    linalg_syms = {
        # Vectors
        "vec": _sym("vec", ret_vec),
        "vdim": _sym("vdim", ret_int),
        "vadd": _sym("vadd", ret_vec),
        "vsub": _sym("vsub", ret_vec),
        "vmul": _sym("vmul", ret_vec),
        "vscale": _sym("vscale", ret_vec),
        "vdot": _sym("vdot", ret_unk),
        "vcross": _sym("vcross", ret_vec),
        "vlen": _sym("vlen", ret_float),
        "vlen_sq": _sym("vlen_sq", ret_unk),
        "vnorm": _sym("vnorm", ret_vec),
        "vneg": _sym("vneg", ret_vec),
        "vlerp": _sym("vlerp", ret_vec),
        # Matrices
        "mat": _sym("mat", ret_mat),
        "identity": _sym("identity", ret_mat),
        "mrows": _sym("mrows", ret_int),
        "mcols": _sym("mcols", ret_int),
        "mget": _sym("mget", ret_unk),
        "mrow": _sym("mrow", ret_vec),
        "mcol": _sym("mcol", ret_vec),
        "madd": _sym("madd", ret_mat),
        "msub": _sym("msub", ret_mat),
        "mscale": _sym("mscale", ret_mat),
        "mmul": _sym("mmul", ret_mat),
        "mvmul": _sym("mvmul", ret_vec),
        "mtranspose": _sym("mtranspose", ret_mat),
        "mdet": _sym("mdet", ret_unk),
        "minv": _sym("minv", ret_mat),
    }

    return {  # type: ignore[return-value]
        "math": math_syms,
        "str": str_syms,
        "std": std_syms,
        "list": list_syms,
        "io": io_syms,
        "random": random_syms,
        "time": time_syms,
        "linalg": linalg_syms,
    }


# Populated on first import of this module.
NATIVE_MODULE_SYMBOLS: dict[str, dict[str, object]] = _build_native_symbols()

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
        "linalg": linalg_syms,
    }


# Populated on first import of this module.
NATIVE_MODULE_SYMBOLS: dict[str, dict[str, object]] = _build_native_symbols()

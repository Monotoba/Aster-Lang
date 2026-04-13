"""Tests for the Aster native standard library modules (math, str, std)."""

from __future__ import annotations

import pytest

from aster_lang.interpreter import (
    FloatValue,
    Interpreter,
    InterpreterError,
)
from aster_lang.native_modules import NATIVE_MODULE_SYMBOLS, NATIVE_MODULES
from aster_lang.parser import parse_module

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def run(source: str) -> list[str]:
    """Parse and run an Aster snippet; return captured output lines."""
    m = parse_module(source)
    interp = Interpreter()
    interp.interpret(m)
    return interp.output


def run_expr(expr: str) -> object:
    """Evaluate a single expression and return its value via print."""
    m = parse_module(f"fn main():\n    print({expr})\n")
    interp = Interpreter()
    interp.interpret(m)
    return interp.output[0] if interp.output else None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_math_registered(self) -> None:
        assert "math" in NATIVE_MODULES

    def test_str_registered(self) -> None:
        assert "str" in NATIVE_MODULES

    def test_std_registered(self) -> None:
        assert "std" in NATIVE_MODULES

    def test_math_symbols_registered(self) -> None:
        assert "math" in NATIVE_MODULE_SYMBOLS
        assert "sqrt" in NATIVE_MODULE_SYMBOLS["math"]

    def test_str_symbols_registered(self) -> None:
        assert "str" in NATIVE_MODULE_SYMBOLS
        assert "upper" in NATIVE_MODULE_SYMBOLS["str"]

    def test_std_symbols_registered(self) -> None:
        assert "std" in NATIVE_MODULE_SYMBOLS
        assert "type_of" in NATIVE_MODULE_SYMBOLS["std"]


# ---------------------------------------------------------------------------
# math module — import and constants
# ---------------------------------------------------------------------------


class TestMathImport:
    def test_import_as_namespace(self) -> None:
        src = "use math\nfn main():\n    print(str(math.floor(2)))\n"
        assert run(src) == ["2"]

    def test_import_named(self) -> None:
        src = "use math: floor\nfn main():\n    print(str(floor(3)))\n"
        assert run(src) == ["3"]

    def test_pi_constant(self) -> None:
        src = "use math\nfn main():\n    x := math.pi\n    print(str(x))\n"
        output = run(src)
        assert "3.14" in output[0]

    def test_e_constant(self) -> None:
        src = "use math\nfn main():\n    x := math.e\n    print(str(x))\n"
        output = run(src)
        assert "2.71" in output[0]


# ---------------------------------------------------------------------------
# math — integer-returning functions
# ---------------------------------------------------------------------------


class TestMathIntFunctions:
    def test_floor(self) -> None:
        src = "use math\nfn main():\n    print(str(math.floor(3)))\n"
        assert run(src) == ["3"]

    def test_ceil(self) -> None:
        src = "use math\nfn main():\n    print(str(math.ceil(3)))\n"
        assert run(src) == ["3"]

    def test_round(self) -> None:
        src = "use math\nfn main():\n    print(str(math.round(3)))\n"
        assert run(src) == ["3"]

    def test_sqrt_perfect_square(self) -> None:
        src = "use math\nfn main():\n    print(str(math.sqrt(16)))\n"
        assert run(src) == ["4"]

    def test_abs_positive(self) -> None:
        src = "use math\nfn main():\n    print(str(math.abs(5)))\n"
        assert run(src) == ["5"]

    def test_min(self) -> None:
        src = "use math\nfn main():\n    print(str(math.min(3, 7)))\n"
        assert run(src) == ["3"]

    def test_max(self) -> None:
        src = "use math\nfn main():\n    print(str(math.max(3, 7)))\n"
        assert run(src) == ["7"]

    def test_clamp_within(self) -> None:
        src = "use math\nfn main():\n    print(str(math.clamp(5, 0, 10)))\n"
        assert run(src) == ["5"]

    def test_clamp_below(self) -> None:
        src = "use math\nfn main():\n    print(str(math.clamp(-5, 0, 10)))\n"
        assert run(src) == ["0"]

    def test_clamp_above(self) -> None:
        src = "use math\nfn main():\n    print(str(math.clamp(20, 0, 10)))\n"
        assert run(src) == ["10"]


# ---------------------------------------------------------------------------
# math — float-returning functions
# ---------------------------------------------------------------------------


class TestMathFloatFunctions:
    def test_sqrt_non_square(self) -> None:
        src = "use math\nfn main():\n    x := math.sqrt(2)\n    print(str(x))\n"
        output = run(src)
        assert "1.41" in output[0]

    def test_sin_zero(self) -> None:
        src = "use math\nfn main():\n    x := math.sin(0)\n    print(str(x))\n"
        assert run(src) == ["0.0"]

    def test_cos_zero(self) -> None:
        src = "use math\nfn main():\n    x := math.cos(0)\n    print(str(x))\n"
        assert run(src) == ["1.0"]

    def test_pow_integer_result(self) -> None:
        src = "use math\nfn main():\n    print(str(math.pow(2, 3)))\n"
        assert run(src) == ["8"]

    def test_log_e_is_one(self) -> None:
        src = "use math\nfn main():\n    x := math.log(math.e)\n    print(str(x))\n"
        assert run(src) == ["1.0"]

    def test_log2_of_8(self) -> None:
        src = "use math\nfn main():\n    print(str(math.log2(8)))\n"
        assert run(src) == ["3.0"]

    def test_log10_of_100(self) -> None:
        src = "use math\nfn main():\n    print(str(math.log10(100)))\n"
        assert run(src) == ["2.0"]

    def test_sqrt_domain_error(self) -> None:
        src = "use math\nfn main():\n    x := math.sqrt(-1)\n"
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="domain error"):
            interp.interpret(m)

    def test_log_domain_error(self) -> None:
        src = "use math\nfn main():\n    x := math.log(0)\n"
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="domain error"):
            interp.interpret(m)


# ---------------------------------------------------------------------------
# str module
# ---------------------------------------------------------------------------


class TestStrModule:
    def test_upper(self) -> None:
        src = 'use str\nfn main():\n    print(str.upper("hello"))\n'
        assert run(src) == ["HELLO"]

    def test_lower(self) -> None:
        src = 'use str\nfn main():\n    print(str.lower("WORLD"))\n'
        assert run(src) == ["world"]

    def test_strip(self) -> None:
        src = 'use str\nfn main():\n    print(str.strip("  hi  "))\n'
        assert run(src) == ["hi"]

    def test_lstrip(self) -> None:
        src = 'use str\nfn main():\n    print(str.lstrip("  hi"))\n'
        assert run(src) == ["hi"]

    def test_rstrip(self) -> None:
        src = 'use str\nfn main():\n    print(str.rstrip("hi  "))\n'
        assert run(src) == ["hi"]

    def test_split(self) -> None:
        # print each element directly — str() is shadowed by `use str`
        src = (
            "use str\nfn main():\n"
            '    parts := str.split("a,b,c", ",")\n'
            "    print(parts[0])\n    print(parts[1])\n    print(parts[2])\n"
        )
        assert run(src) == ["a", "b", "c"]

    def test_join(self) -> None:
        src = (
            'use str\nfn main():\n    result := str.join("-", ["x", "y", "z"])\n    print(result)\n'
        )
        assert run(src) == ["x-y-z"]

    def test_starts_with_true(self) -> None:
        src = 'use str\nfn main():\n    x := str.starts_with("hello", "he")\n    print(x)\n'
        assert run(src) == ["true"]

    def test_starts_with_false(self) -> None:
        src = 'use str\nfn main():\n    x := str.starts_with("hello", "wo")\n    print(x)\n'
        assert run(src) == ["false"]

    def test_ends_with_true(self) -> None:
        src = 'use str\nfn main():\n    x := str.ends_with("hello", "lo")\n    print(x)\n'
        assert run(src) == ["true"]

    def test_contains_true(self) -> None:
        src = 'use str\nfn main():\n    x := str.contains("foobar", "oba")\n    print(x)\n'
        assert run(src) == ["true"]

    def test_contains_false(self) -> None:
        src = 'use str\nfn main():\n    x := str.contains("foobar", "xyz")\n    print(x)\n'
        assert run(src) == ["false"]

    def test_find_present(self) -> None:
        src = 'use str\nfn main():\n    i := str.find("hello", "ll")\n    print(i)\n'
        assert run(src) == ["2"]

    def test_find_absent(self) -> None:
        src = 'use str\nfn main():\n    i := str.find("hello", "zz")\n    print(i)\n'
        assert run(src) == ["-1"]

    def test_replace(self) -> None:
        src = 'use str\nfn main():\n    s := str.replace("aabbcc", "bb", "XX")\n    print(s)\n'
        assert run(src) == ["aaXXcc"]

    def test_chars(self) -> None:
        src = 'use str\nfn main():\n    cs := str.chars("abc")\n    print(len(cs))\n'
        assert run(src) == ["3"]

    def test_char_at(self) -> None:
        src = 'use str\nfn main():\n    c := str.char_at("hello", 1)\n    print(c)\n'
        assert run(src) == ["e"]

    def test_char_at_out_of_bounds(self) -> None:
        src = 'use str\nfn main():\n    c := str.char_at("hi", 10)\n'
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="out of bounds"):
            interp.interpret(m)

    def test_repeat(self) -> None:
        src = 'use str\nfn main():\n    s := str.repeat("ab", 3)\n    print(s)\n'
        assert run(src) == ["ababab"]

    def test_slice(self) -> None:
        src = 'use str\nfn main():\n    s := str.slice("hello", 1, 4)\n    print(s)\n'
        assert run(src) == ["ell"]

    def test_pad_left(self) -> None:
        src = 'use str\nfn main():\n    s := str.pad_left("42", 5, "0")\n    print(s)\n'
        assert run(src) == ["00042"]

    def test_pad_right(self) -> None:
        src = 'use str\nfn main():\n    s := str.pad_right("hi", 5, ".")\n    print(s)\n'
        assert run(src) == ["hi..."]


# ---------------------------------------------------------------------------
# std module
# ---------------------------------------------------------------------------


class TestStdModule:
    def test_type_of_int(self) -> None:
        src = "use std\nfn main():\n    print(std.type_of(42))\n"
        assert run(src) == ["Int"]

    def test_type_of_string(self) -> None:
        src = 'use std\nfn main():\n    print(std.type_of("hi"))\n'
        assert run(src) == ["String"]

    def test_type_of_bool(self) -> None:
        src = "use std\nfn main():\n    print(std.type_of(true))\n"
        assert run(src) == ["Bool"]

    def test_type_of_list(self) -> None:
        src = "use std\nfn main():\n    print(std.type_of([1, 2]))\n"
        assert run(src) == ["List"]

    def test_type_of_nil(self) -> None:
        src = "use std\nfn main():\n    print(std.type_of(nil))\n"
        assert run(src) == ["Nil"]

    def test_panic_raises(self) -> None:
        src = 'use std\nfn main():\n    std.panic("oh no")\n'
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="oh no"):
            interp.interpret(m)

    def test_todo_raises(self) -> None:
        src = "use std\nfn main():\n    std.todo()\n"
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="not yet implemented"):
            interp.interpret(m)


# ---------------------------------------------------------------------------
# FloatValue
# ---------------------------------------------------------------------------


class TestFloatValue:
    def test_float_str_conversion(self) -> None:
        assert str(FloatValue(3.14)) == "3.14"

    def test_int_builtin_truncates_float(self) -> None:
        src = "use math\nfn main():\n    x := math.sqrt(2)\n    print(str(int(x)))\n"
        assert run(src) == ["1"]

    def test_str_builtin_on_float(self) -> None:
        # str() builtin delegates to __str__, which works for FloatValue
        assert str(FloatValue(2.5)) == "2.5"

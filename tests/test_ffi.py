"""Tests for the FFI (extern declaration) feature."""

from __future__ import annotations

import ctypes.util
from pathlib import Path

import pytest

from aster_lang import ast
from aster_lang.formatter import Formatter
from aster_lang.interpreter import Interpreter, InterpreterError, interpret_source
from aster_lang.parser import parse_module
from aster_lang.semantic import SemanticAnalyzer, SymbolKind

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse(source: str) -> ast.Module:
    return parse_module(source)


def run(source: str) -> list[str]:
    m = parse_module(source)
    interp = Interpreter()
    interp.interpret(m)
    return interp.output


def fmt(source: str) -> str:
    m = parse_module(source)
    f = Formatter()
    return f.format_module(m).rstrip("\n")


def check(source: str) -> list[object]:
    m = parse_module(source)
    analyzer = SemanticAnalyzer()
    analyzer.analyze(m)
    return analyzer.errors  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------


class TestExternParser:
    def test_basic_extern(self) -> None:
        src = 'extern "libm":\n    fn cos(x: Float) -> Float\n'
        m = parse(src)
        decls = [d for d in m.declarations if isinstance(d, ast.ExternDecl)]
        assert len(decls) == 1
        d = decls[0]
        assert d.library == "libm"
        assert len(d.functions) == 1
        assert d.functions[0].name == "cos"
        assert not d.is_public

    def test_pub_extern(self) -> None:
        src = 'pub extern "libm":\n    fn sin(x: Float) -> Float\n'
        m = parse(src)
        decls = [d for d in m.declarations if isinstance(d, ast.ExternDecl)]
        assert decls[0].is_public

    def test_multiple_functions(self) -> None:
        src = 'extern "libm":\n    fn cos(x: Float) -> Float\n    fn sin(x: Float) -> Float\n'
        m = parse(src)
        decl = next(d for d in m.declarations if isinstance(d, ast.ExternDecl))
        assert len(decl.functions) == 2
        names = [f.name for f in decl.functions]
        assert "cos" in names
        assert "sin" in names

    def test_void_return(self) -> None:
        src = 'extern "libfoo":\n    fn do_thing(x: Int)\n'
        m = parse(src)
        decl = next(d for d in m.declarations if isinstance(d, ast.ExternDecl))
        assert decl.functions[0].return_type is None

    def test_multi_param(self) -> None:
        src = 'extern "libm":\n    fn pow(base: Float, exp: Float) -> Float\n'
        m = parse(src)
        decl = next(d for d in m.declarations if isinstance(d, ast.ExternDecl))
        fn = decl.functions[0]
        assert len(fn.params) == 2
        assert fn.params[0].name == "base"
        assert fn.params[1].name == "exp"


# ---------------------------------------------------------------------------
# Formatter tests
# ---------------------------------------------------------------------------


class TestExternFormatter:
    def test_basic_roundtrip(self) -> None:
        src = 'extern "libm":\n    fn cos(x: Float) -> Float\n'
        assert fmt(src) == 'extern "libm":\n    fn cos(x: Float) -> Float'

    def test_pub_roundtrip(self) -> None:
        src = 'pub extern "libm":\n    fn sin(x: Float) -> Float\n'
        assert fmt(src) == 'pub extern "libm":\n    fn sin(x: Float) -> Float'

    def test_multi_function_roundtrip(self) -> None:
        src = 'extern "libm":\n    fn cos(x: Float) -> Float\n    fn sin(x: Float) -> Float\n'
        result = fmt(src)
        assert 'extern "libm":' in result
        assert "    fn cos(x: Float) -> Float" in result
        assert "    fn sin(x: Float) -> Float" in result

    def test_idempotent(self) -> None:
        src = 'extern "libm":\n    fn cos(x: Float) -> Float\n'
        assert fmt(fmt(src) + "\n") == fmt(src)

    def test_escaped_library_name(self) -> None:
        src = 'extern "lib\\\\foo":\n    fn bar() -> Int\n'
        result = fmt(src)
        assert '"lib\\\\foo"' in result


# ---------------------------------------------------------------------------
# Semantic tests
# ---------------------------------------------------------------------------


class TestExternSemantic:
    def test_function_registered(self) -> None:
        src = 'extern "libm":\n    fn cos(x: Float) -> Float\nfn main():\n    return\n'
        errors = check(src)
        assert not errors

    def test_symbol_kind(self) -> None:
        src = 'extern "libm":\n    fn cos(x: Float) -> Float\n'
        m = parse(src)
        analyzer = SemanticAnalyzer()
        analyzer.analyze(m)
        sym = analyzer.symbol_table.lookup("cos")
        assert sym is not None
        assert sym.kind == SymbolKind.FUNCTION

    def test_duplicate_function_error(self) -> None:
        src = (
            "fn cos(x: Float) -> Float:\n    return x\n"
            'extern "libm":\n    fn cos(x: Float) -> Float\n'
        )
        errors = check(src)
        assert errors

    def test_pub_extern_exports(self, tmp_path: Path) -> None:
        lib_src = 'pub extern "libm":\n    fn cos(x: Float) -> Float\n'
        (tmp_path / "mylib.aster").write_text(lib_src)

        main_src = "use mylib: cos\nfn main():\n    return\n"
        m = parse_module(main_src)
        analyzer = SemanticAnalyzer(base_dir=tmp_path)
        analyzer.analyze(m)
        assert not analyzer.errors
        sym = analyzer.symbol_table.lookup("cos")
        assert sym is not None
        assert sym.kind == SymbolKind.FUNCTION


# ---------------------------------------------------------------------------
# Interpreter / FFI tests
# ---------------------------------------------------------------------------

_HAS_LIBM = ctypes.util.find_library("m") is not None

libm_only: pytest.MarkDecorator = pytest.mark.skipif(
    not _HAS_LIBM, reason="libm not found on this system"
)


class TestFFIInterpreter:
    @libm_only  # type: ignore[misc]
    def test_cos_zero(self) -> None:
        src = (
            'extern "libm":\n'
            "    fn cos(x: Float) -> Float\n"
            "fn main():\n"
            "    print(cos(0))\n"
        )
        result = interpret_source(src)
        assert result.error is None
        assert float(result.output) == pytest.approx(1.0)

    @libm_only  # type: ignore[misc]
    def test_sqrt_four(self) -> None:
        src = (
            'extern "libm":\n'
            "    fn sqrt(x: Float) -> Float\n"
            "fn main():\n"
            "    print(sqrt(4))\n"
        )
        result = interpret_source(src)
        assert result.error is None
        assert float(result.output) == pytest.approx(2.0)

    @libm_only  # type: ignore[misc]
    def test_pow(self) -> None:
        src = (
            'extern "libm":\n'
            "    fn pow(base: Float, exp: Float) -> Float\n"
            "fn main():\n"
            "    print(pow(2, 10))\n"
        )
        result = interpret_source(src)
        assert result.error is None
        assert float(result.output) == pytest.approx(1024.0)

    def test_bad_library_raises(self) -> None:
        src = (
            'extern "__no_such_library_xyz__":\n'
            "    fn foo() -> Int\n"
            "fn main():\n"
            "    foo()\n"
        )
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="FFI"):
            interp.interpret(m)

    @libm_only  # type: ignore[misc]
    def test_pub_extern_importable(self, tmp_path: Path) -> None:
        lib_src = 'pub extern "libm":\n' "    fn cos(x: Float) -> Float\n"
        (tmp_path / "mylib.aster").write_text(lib_src)

        main_src = "use mylib: cos\nfn main():\n    print(cos(0))\n"
        result = interpret_source(main_src, base_dir=tmp_path)
        assert result.error is None
        assert float(result.output) == pytest.approx(1.0)

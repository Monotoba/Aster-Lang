from __future__ import annotations

from aster_lang.hir import dump_hir
from aster_lang.parser import parse_module
from aster_lang.semantic import SemanticAnalyzer


def test_dump_hir_includes_expression_types() -> None:
    module = parse_module("fn add(a: Int, b: Int) -> Int:\n" "    return a + b\n")
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

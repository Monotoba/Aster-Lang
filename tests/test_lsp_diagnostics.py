"""Unit tests for the diagnostics part of the Aster Language Server."""

from aster_lang.lsp.server import (
    AsterLanguageServer,
    definition_for_position,
    hover_for_position,
    to_lsp_diagnostics,
)


def run_server_and_parse(source: str) -> AsterLanguageServer:
    server = AsterLanguageServer()
    # Simulate "didOpen"
    server._analyse_and_publish("file://dummy.aster", source)
    return server


# Test: syntax error yields diagnostic


def test_parse_error_diagnostic() -> None:
    source = "fn (broken"
    server = run_server_and_parse(source)
    result = server.get_result("file://dummy.aster")
    assert result is not None
    diags = to_lsp_diagnostics(result)
    assert len(diags) == 1
    diag = diags[0]
    assert diag.severity == 1  # Error


# Test: valid syntax no diagnostics


def test_no_errors() -> None:
    source = "fn add(a: Int, b: Int) -> Int:\n    return a + b\n"
    server = run_server_and_parse(source)
    result = server.get_result("file://dummy.aster")
    assert result is not None
    diags = to_lsp_diagnostics(result)
    assert diags == []


def test_hover_known_symbol() -> None:
    source = "fn add(a: Int, b: Int) -> Int:\n    return a + b\n"
    server = run_server_and_parse(source)
    result = server.get_result("file://dummy.aster")
    assert result is not None
    # "add" starts at character 3
    hover_text = hover_for_position(result, 0, 3)
    assert hover_text is not None
    assert "add" in hover_text


def test_definition_same_file() -> None:
    source = "fn add(a: Int, b: Int) -> Int:\n    return a + b\n"
    server = run_server_and_parse(source)
    result = server.get_result("file://dummy.aster")
    assert result is not None
    # "add" starts at character 3
    location = definition_for_position(result, 0, 3)
    assert location is not None
    assert location.uri == "file://dummy.aster"
    assert location.range.start.line == 0
    assert location.range.start.character == 3

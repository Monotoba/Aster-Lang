# tests/test_lsp_definition.py
"""Tests for the go-to-definition functionality of the LSP server."""

from aster_lang.lsp.server import AsterLanguageServer, definition_for_position


def run_server_and_parse(source: str) -> AsterLanguageServer:
    server = AsterLanguageServer()
    server._analyse_and_publish("file://dummy.aster", source)
    return server


def test_definition_same_file() -> None:
    source = "fn add(a: Int, b: Int) -> Int:\n    a + b\n"
    server = run_server_and_parse(source)
    result = server.get_result("file://dummy.aster")
    assert result is not None
    # "add" starts at character 3
    location = definition_for_position(result, 0, 3)
    assert location is not None
    assert location.uri == "file://dummy.aster"
    assert location.range.start.line == 0
    assert location.range.start.character == 3

# tests/test_lsp_hover.py
"""Tests for the hover functionality of the LSP server."""

from aster_lang.lsp.server import AsterLanguageServer, hover_for_position


def run_server_and_parse(source: str) -> AsterLanguageServer:
    server = AsterLanguageServer()
    server._analyse_and_publish("file://dummy.aster", source)
    return server


def test_hover_known_symbol() -> None:
    source = "fn add(a: Int, b: Int) -> Int:\n    a + b\n"
    server = run_server_and_parse(source)
    result = server.get_result("file://dummy.aster")
    assert result is not None
    # "add" starts at character 3
    hover_text = hover_for_position(result, 0, 3)
    assert hover_text is not None
    assert "add" in hover_text

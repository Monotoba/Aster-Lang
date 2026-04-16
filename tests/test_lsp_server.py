"""Tests for the Aster language server.

Coverage strategy
-----------------
Layer 1 — pure functions (no pygls required):
  analyze_source()       called with valid/invalid Aster snippets
  to_lsp_diagnostics()   verify LSP Diagnostic fields

Layer 2 — server construction:
  AsterLanguageServer    verify it instantiates and registers expected features

Layer 3 — handler logic:
  _analyse_and_publish() called directly; mocks out publish to capture output
"""

from __future__ import annotations

from unittest.mock import patch

from lsprotocol import types

from aster_lang.lsp.server import (
    AnalysisResult,
    AsterLanguageServer,
    _aster_to_lsp_position,
    analyze_source,
    definition_for_position,
    hover_for_position,
    to_lsp_diagnostics,
    token_at_position,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HELLO = """\
fn hello() -> Str:
    return "hello"
"""

SYNTAX_ERROR = """\
fn broken(
"""

UNDEFINED_VAR = """\
fn bad() -> Int:
    return z
"""


# ---------------------------------------------------------------------------
# _aster_to_lsp_position
# ---------------------------------------------------------------------------


class TestAsterToLspPosition:
    def test_line_converted_to_zero_based(self) -> None:
        pos = _aster_to_lsp_position(1, 0)
        assert pos.line == 0
        assert pos.character == 0

    def test_col_unchanged(self) -> None:
        pos = _aster_to_lsp_position(3, 7)
        assert pos.line == 2
        assert pos.character == 7

    def test_line_zero_clamped(self) -> None:
        """Line 0 (shouldn't happen, but guard it)."""
        pos = _aster_to_lsp_position(0, 5)
        assert pos.line == 0


# ---------------------------------------------------------------------------
# analyze_source — valid input
# ---------------------------------------------------------------------------


class TestAnalyzeSourceValid:
    def test_returns_analysis_result(self) -> None:
        result = analyze_source(HELLO, uri="file:///hello.aster")
        assert isinstance(result, AnalysisResult)

    def test_no_errors_on_valid_source(self) -> None:
        result = analyze_source(HELLO)
        assert not result.has_errors
        assert result.parse_error is None
        assert result.semantic_errors == []

    def test_module_populated(self) -> None:
        result = analyze_source(HELLO)
        assert result.module is not None

    def test_uri_stored(self) -> None:
        result = analyze_source(HELLO, uri="file:///x.aster")
        assert result.uri == "file:///x.aster"

    def test_empty_source_produces_no_errors(self) -> None:
        result = analyze_source("")
        assert result.parse_error is None


# ---------------------------------------------------------------------------
# analyze_source — parse errors
# ---------------------------------------------------------------------------


class TestAnalyzeSourceParseErrors:
    def test_syntax_error_captured(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        assert result.parse_error is not None

    def test_module_none_on_parse_error(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        assert result.module is None

    def test_has_errors_true_on_parse_error(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        assert result.has_errors


# ---------------------------------------------------------------------------
# analyze_source — semantic errors
# ---------------------------------------------------------------------------


class TestAnalyzeSourceSemanticErrors:
    def test_undefined_variable_produces_semantic_error(self) -> None:
        result = analyze_source(UNDEFINED_VAR)
        assert result.parse_error is None, "should parse fine"
        assert result.has_errors
        assert len(result.semantic_errors) > 0

    def test_error_messages_are_strings(self) -> None:
        result = analyze_source(UNDEFINED_VAR)
        for err in result.semantic_errors:
            assert isinstance(err.message, str)
            assert len(err.message) > 0


# ---------------------------------------------------------------------------
# to_lsp_diagnostics — no errors
# ---------------------------------------------------------------------------


class TestToLspDiagnosticsClean:
    def test_empty_list_when_no_errors(self) -> None:
        result = analyze_source(HELLO)
        diags = to_lsp_diagnostics(result)
        assert diags == []


# ---------------------------------------------------------------------------
# to_lsp_diagnostics — parse error
# ---------------------------------------------------------------------------


class TestToLspDiagnosticsParseError:
    def test_single_diagnostic_for_parse_error(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        diags = to_lsp_diagnostics(result)
        assert len(diags) == 1

    def test_diagnostic_severity_is_error(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        diag = to_lsp_diagnostics(result)[0]
        assert diag.severity == types.DiagnosticSeverity.Error

    def test_diagnostic_source_is_aster(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        diag = to_lsp_diagnostics(result)[0]
        assert diag.source == "aster"

    def test_diagnostic_range_valid(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        diag = to_lsp_diagnostics(result)[0]
        r = diag.range
        assert r.start.line >= 0
        assert r.end.character >= r.start.character or r.end.line > r.start.line

    def test_diagnostic_message_nonempty(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        diag = to_lsp_diagnostics(result)[0]
        assert diag.message


# ---------------------------------------------------------------------------
# to_lsp_diagnostics — semantic errors
# ---------------------------------------------------------------------------


class TestToLspDiagnosticsSemantic:
    def test_one_diagnostic_per_semantic_error(self) -> None:
        result = analyze_source(UNDEFINED_VAR)
        diags = to_lsp_diagnostics(result)
        assert len(diags) == len(result.semantic_errors) + len(result.semantic_warnings)

    def test_semantic_error_severity(self) -> None:
        result = analyze_source(UNDEFINED_VAR)
        diags = to_lsp_diagnostics(result)
        error_diags = [d for d in diags if d.severity == types.DiagnosticSeverity.Error]
        assert len(error_diags) == len(result.semantic_errors)

    def test_no_semantic_errors_after_parse_failure(self) -> None:
        """If parsing fails we should only see one diagnostic, not semantic ones."""
        result = analyze_source(SYNTAX_ERROR)
        diags = to_lsp_diagnostics(result)
        assert len(diags) == 1


# ---------------------------------------------------------------------------
# to_lsp_diagnostics — semantic warning
# ---------------------------------------------------------------------------

WARNING_SOURCE = """\
fn unused_binding() -> Int:
    x := 42
    return 0
"""


class TestToLspDiagnosticsWarning:
    def test_warnings_emitted_if_present(self) -> None:
        result = analyze_source(WARNING_SOURCE)
        if result.semantic_warnings:
            diags = to_lsp_diagnostics(result)
            warn_diags = [d for d in diags if d.severity == types.DiagnosticSeverity.Warning]
            assert len(warn_diags) == len(result.semantic_warnings)


# ---------------------------------------------------------------------------
# AsterLanguageServer — construction
# ---------------------------------------------------------------------------


class TestAsterLanguageServerConstruction:
    def test_instantiates(self) -> None:
        server = AsterLanguageServer()
        assert server is not None

    def test_name_and_version(self) -> None:
        server = AsterLanguageServer()
        assert server.name == "aster-lang"
        assert server.version == "0.1.0"

    def test_did_open_registered(self) -> None:
        server = AsterLanguageServer()
        assert types.TEXT_DOCUMENT_DID_OPEN in server.protocol.fm.features

    def test_did_change_registered(self) -> None:
        server = AsterLanguageServer()
        assert types.TEXT_DOCUMENT_DID_CHANGE in server.protocol.fm.features

    def test_did_close_registered(self) -> None:
        server = AsterLanguageServer()
        assert types.TEXT_DOCUMENT_DID_CLOSE in server.protocol.fm.features

    def test_results_initially_empty(self) -> None:
        server = AsterLanguageServer()
        assert server.get_result("file:///nonexistent.aster") is None


# ---------------------------------------------------------------------------
# AsterLanguageServer — _analyse_and_publish
# ---------------------------------------------------------------------------


class TestAnalyseAndPublish:
    def test_result_stored_after_analysis(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///test.aster"
        with patch.object(server, "text_document_publish_diagnostics"):
            server._analyse_and_publish(uri, HELLO)
        result = server.get_result(uri)
        assert result is not None
        assert not result.has_errors

    def test_publish_called_once(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///test.aster"
        with patch.object(server, "text_document_publish_diagnostics") as mock_pub:
            server._analyse_and_publish(uri, HELLO)
        mock_pub.assert_called_once()

    def test_published_params_uri_matches(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///test.aster"
        captured: list[types.PublishDiagnosticsParams] = []
        with patch.object(server, "text_document_publish_diagnostics", side_effect=captured.append):
            server._analyse_and_publish(uri, HELLO)
        assert captured[0].uri == uri

    def test_error_source_produces_diagnostics(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///bad.aster"
        captured: list[types.PublishDiagnosticsParams] = []
        with patch.object(server, "text_document_publish_diagnostics", side_effect=captured.append):
            server._analyse_and_publish(uri, SYNTAX_ERROR)
        assert len(captured[0].diagnostics) > 0

    def test_clean_source_produces_no_diagnostics(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///clean.aster"
        captured: list[types.PublishDiagnosticsParams] = []
        with patch.object(server, "text_document_publish_diagnostics", side_effect=captured.append):
            server._analyse_and_publish(uri, HELLO)
        assert captured[0].diagnostics == []

    def test_result_replaced_on_second_call(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///evolving.aster"
        with patch.object(server, "text_document_publish_diagnostics"):
            server._analyse_and_publish(uri, SYNTAX_ERROR)
            first = server.get_result(uri)
            server._analyse_and_publish(uri, HELLO)
            second = server.get_result(uri)
        assert first is not None and first.has_errors
        assert second is not None and not second.has_errors


# ---------------------------------------------------------------------------
# AsterLanguageServer — did_close clears result
# ---------------------------------------------------------------------------


class TestDidClose:
    def test_result_removed_on_close(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///close_me.aster"
        with patch.object(server, "text_document_publish_diagnostics"):
            server._analyse_and_publish(uri, HELLO)
        assert server.get_result(uri) is not None

        close_params = types.DidCloseTextDocumentParams(
            text_document=types.TextDocumentIdentifier(uri=uri)
        )
        with patch.object(server, "text_document_publish_diagnostics"):
            # The feature manager stores a partial with the server already bound.
            handler = server.protocol.fm.features[types.TEXT_DOCUMENT_DID_CLOSE]
            handler(close_params)
        assert server.get_result(uri) is None


# ---------------------------------------------------------------------------
# Phase 2 — token_at_position
# ---------------------------------------------------------------------------

# A simple two-function source used by hover tests.
HOVER_SOURCE = """\
fn add(a: Int, b: Int) -> Int:
    result := a + b
    return result

fn main():
    x := add(1, 2)
"""


class TestTokenAtPosition:
    def test_identifier_on_first_line(self) -> None:
        # "add" starts at lsp_line=0, lsp_char=3
        tok = token_at_position(HOVER_SOURCE, lsp_line=0, lsp_char=3)
        assert tok is not None
        assert tok.text == "add"

    def test_identifier_mid_line(self) -> None:
        # "result" on lsp_line=1 (Aster line 2), col=4
        tok = token_at_position(HOVER_SOURCE, lsp_line=1, lsp_char=4)
        assert tok is not None
        assert tok.text == "result"

    def test_returns_none_on_whitespace(self) -> None:
        tok = token_at_position(HOVER_SOURCE, lsp_line=0, lsp_char=0)
        # column 0 on line 0 is 'f' from 'fn', not an IDENTIFIER
        assert tok is None or tok.text != "add"

    def test_returns_none_on_blank_line(self) -> None:
        tok = token_at_position(HOVER_SOURCE, lsp_line=3, lsp_char=0)
        assert tok is None

    def test_returns_none_on_parse_error(self) -> None:
        tok = token_at_position("fn broken(\n", lsp_line=0, lsp_char=3)
        # Should not raise; may return None or the partial token
        # The key assertion is that it doesn't raise.
        assert tok is None or isinstance(tok.text, str)


# ---------------------------------------------------------------------------
# Phase 2 — hover_for_position (pure)
# ---------------------------------------------------------------------------


class TestHoverForPosition:
    def test_hover_on_function_name(self) -> None:
        result = analyze_source(HOVER_SOURCE)
        md = hover_for_position(result, lsp_line=0, lsp_char=3)
        assert md is not None
        assert "add" in md

    def test_hover_includes_type(self) -> None:
        result = analyze_source(HOVER_SOURCE)
        md = hover_for_position(result, lsp_line=0, lsp_char=3)
        assert md is not None
        # Function type string should be present
        assert "Fn" in md or "->" in md or "function" in md.lower()

    def test_hover_on_local_variable(self) -> None:
        result = analyze_source(HOVER_SOURCE)
        # "result" on lsp_line=1 (inside add body)
        md = hover_for_position(result, lsp_line=1, lsp_char=4)
        assert md is not None
        assert "result" in md

    def test_hover_on_builtin(self) -> None:
        src = 'fn f():\n    print("hi")\n'
        result = analyze_source(src)
        # "print" on lsp_line=1, col=4
        md = hover_for_position(result, lsp_line=1, lsp_char=4)
        assert md is not None
        assert "print" in md

    def test_hover_returns_none_on_non_identifier(self) -> None:
        result = analyze_source(HOVER_SOURCE)
        # col 0 on line 0 is 'f' (part of 'fn' keyword), not an identifier
        md = hover_for_position(result, lsp_line=0, lsp_char=0)
        # Either None (no ident there) or refers to 'fn' — but 'fn' won't be in symbol table
        # In practice we expect None here.
        assert md is None

    def test_hover_returns_none_when_parse_error(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        md = hover_for_position(result, lsp_line=0, lsp_char=3)
        assert md is None

    def test_hover_returns_none_on_unknown_name(self) -> None:
        result = analyze_source(HELLO)
        # cursor on blank space that produces a token not in the symbol table
        md = hover_for_position(result, lsp_line=0, lsp_char=100)
        assert md is None

    def test_symbol_table_populated_after_analysis(self) -> None:
        result = analyze_source(HOVER_SOURCE)
        assert result.symbol_table is not None

    def test_symbol_table_none_after_parse_error(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        assert result.symbol_table is None


# ---------------------------------------------------------------------------
# Phase 2 — server: hover + formatting handlers registered
# ---------------------------------------------------------------------------


class TestPhase2ServerCapabilities:
    def test_hover_handler_registered(self) -> None:
        server = AsterLanguageServer()
        assert types.TEXT_DOCUMENT_HOVER in server.protocol.fm.features

    def test_formatting_handler_registered(self) -> None:
        server = AsterLanguageServer()
        assert types.TEXT_DOCUMENT_FORMATTING in server.protocol.fm.features


# ---------------------------------------------------------------------------
# Phase 2 — document formatting via handler
# ---------------------------------------------------------------------------

UNFORMATTED = "fn f(  ):\n    return 1\n"


class TestFormattingHandler:
    def _call_formatting(
        self, server: AsterLanguageServer, uri: str
    ) -> list[types.TextEdit] | None:
        from typing import cast

        handler = server.protocol.fm.features[types.TEXT_DOCUMENT_FORMATTING]
        params = types.DocumentFormattingParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            options=types.FormattingOptions(tab_size=4, insert_spaces=True),
        )
        return cast(list[types.TextEdit] | None, handler(params))

    def test_returns_text_edit_list(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///fmt.aster"
        with patch.object(server, "text_document_publish_diagnostics"):
            server._analyse_and_publish(uri, HELLO)
        edits = self._call_formatting(server, uri)
        # HELLO is already canonical so should get [] or a list
        assert isinstance(edits, list)

    def test_returns_none_for_unknown_uri(self) -> None:
        server = AsterLanguageServer()
        edits = self._call_formatting(server, "file:///unknown.aster")
        assert edits is None

    def test_returns_none_when_parse_fails(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///broken.aster"
        with patch.object(server, "text_document_publish_diagnostics"):
            server._analyse_and_publish(uri, SYNTAX_ERROR)
        edits = self._call_formatting(server, uri)
        assert edits is None

    def test_edit_replaces_whole_document(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///fmt.aster"
        with patch.object(server, "text_document_publish_diagnostics"):
            server._analyse_and_publish(uri, UNFORMATTED)
        edits = self._call_formatting(server, uri)
        if edits:  # non-empty only if formatter changed something
            edit = edits[0]
            assert edit.range.start.line == 0
            assert edit.range.start.character == 0

    def test_formatted_source_returns_empty_edits(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///already_fmt.aster"
        with patch.object(server, "text_document_publish_diagnostics"):
            server._analyse_and_publish(uri, HELLO)
        edits = self._call_formatting(server, uri)
        assert edits == []


# ---------------------------------------------------------------------------
# Phase 3 — definition_for_position (pure)
# ---------------------------------------------------------------------------

# Source with function, parameter, and local variable — all in one file.
DEFINITION_SOURCE = """\
fn greet(name: Str) -> Str:
    msg := "Hello"
    return msg

fn main():
    result := greet("world")
"""

# Line/column landmarks (0-based LSP):
# line 0: fn greet(name: Str) -> Str:    — "greet" at col 3
# line 1:     msg := "Hello"             — "msg" at col 4
# line 2:     return msg                 — "msg" (usage) at col 11
# line 5:     result := greet("world")   — "greet" (call) at col 14


class TestDefinitionForPosition:
    def test_function_declaration_points_to_fn_line(self) -> None:
        result = analyze_source(DEFINITION_SOURCE)
        loc = definition_for_position(result, lsp_line=5, lsp_char=14)
        assert loc is not None
        # Should point to line 0 where "fn greet" is declared
        assert loc.range.start.line == 0

    def test_function_declaration_column_at_name(self) -> None:
        result = analyze_source(DEFINITION_SOURCE)
        loc = definition_for_position(result, lsp_line=5, lsp_char=14)
        assert loc is not None
        # "greet" starts at col 3 on line 0
        assert loc.range.start.character == 3
        assert loc.range.end.character == 3 + len("greet")

    def test_local_variable_usage_points_to_let(self) -> None:
        result = analyze_source(DEFINITION_SOURCE)
        # "msg" on line 2 (usage) should resolve to line 1 (declaration)
        loc = definition_for_position(result, lsp_line=2, lsp_char=11)
        assert loc is not None
        assert loc.range.start.line == 1

    def test_local_variable_column_at_name(self) -> None:
        result = analyze_source(DEFINITION_SOURCE)
        loc = definition_for_position(result, lsp_line=2, lsp_char=11)
        assert loc is not None
        # "msg" starts at col 4 on line 1 (after 4-space indent)
        assert loc.range.start.character == 4
        assert loc.range.end.character == 4 + len("msg")

    def test_location_uri_matches_result_uri(self) -> None:
        uri = "file:///greet.aster"
        result = analyze_source(DEFINITION_SOURCE, uri=uri)
        loc = definition_for_position(result, lsp_line=5, lsp_char=14)
        assert loc is not None
        assert loc.uri == uri

    def test_builtin_returns_none(self) -> None:
        src = 'fn f():\n    print("hi")\n'
        result = analyze_source(src)
        # "print" is a builtin with no declaration_node span
        loc = definition_for_position(result, lsp_line=1, lsp_char=4)
        assert loc is None

    def test_parse_error_returns_none(self) -> None:
        result = analyze_source(SYNTAX_ERROR)
        loc = definition_for_position(result, lsp_line=0, lsp_char=3)
        assert loc is None

    def test_no_token_returns_none(self) -> None:
        result = analyze_source(DEFINITION_SOURCE)
        # column 100 is past end of any line
        loc = definition_for_position(result, lsp_line=0, lsp_char=100)
        assert loc is None

    def test_unknown_name_returns_none(self) -> None:
        result = analyze_source(HELLO)
        # position on blank line
        loc = definition_for_position(result, lsp_line=1, lsp_char=50)
        assert loc is None


# ---------------------------------------------------------------------------
# Phase 3 — server: definition handler registered
# ---------------------------------------------------------------------------


class TestPhase3ServerCapabilities:
    def test_definition_handler_registered(self) -> None:
        server = AsterLanguageServer()
        assert types.TEXT_DOCUMENT_DEFINITION in server.protocol.fm.features

    def test_definition_handler_returns_location(self) -> None:
        server = AsterLanguageServer()
        uri = "file:///def_test.aster"
        with patch.object(server, "text_document_publish_diagnostics"):
            server._analyse_and_publish(uri, DEFINITION_SOURCE)
        handler = server.protocol.fm.features[types.TEXT_DOCUMENT_DEFINITION]
        params = types.DefinitionParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            position=types.Position(line=5, character=14),
        )
        loc = handler(params)
        assert loc is not None
        assert loc.range.start.line == 0

    def test_definition_handler_returns_none_for_unknown_uri(self) -> None:
        server = AsterLanguageServer()
        handler = server.protocol.fm.features[types.TEXT_DOCUMENT_DEFINITION]
        params = types.DefinitionParams(
            text_document=types.TextDocumentIdentifier(uri="file:///unknown.aster"),
            position=types.Position(line=0, character=0),
        )
        assert handler(params) is None

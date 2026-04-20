"""Aster Language Server — pygls 2.x implementation.

Architecture
------------
 analyze_source()      Pure analysis pipeline: lexer → parser → semantic.
 to_lsp_diagnostics()  Convert AnalysisResult to a list of lsprotocol Diagnostic.
 hover_for_position()  Return hover Markdown for the identifier at a cursor position.
 AsterLanguageServer   Subclass of pygls LanguageServer with didOpen/didChange/didClose
                       handlers that publish diagnostics, plus hover and formatting.
 start()               Thin boot helper used by the CLI.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from lsprotocol import types
from pygls.lsp.server import LanguageServer

from aster_lang import ast as aster_ast
from aster_lang.lexer import Lexer, TokenKind
from aster_lang.lexer import Token as LexToken
from aster_lang.parser import ParseError, parse_module
from aster_lang.semantic import (
    Scope,
    SemanticAnalyzer,
    SemanticError,
    SemanticWarning,
    Symbol,
    SymbolKind,
    SymbolTable,
)

logger = logging.getLogger(__name__)

# ------
# Analysis pipeline
# ------


@dataclass
class AnalysisResult:
    """Result of running the full Aster analysis pipeline on a source string."""

    source: str
    uri: str
    module: aster_ast.Module | None = None
    parse_error: ParseError | None = None
    semantic_errors: list[SemanticError] = field(default_factory=list)
    semantic_warnings: list[SemanticWarning] = field(default_factory=list)
    symbol_table: SymbolTable | None = None

    @property
    def has_errors(self) -> bool:
        return self.parse_error is not None or bool(self.semantic_errors)


def analyze_source(source: str, uri: str = "") -> AnalysisResult:
    result = AnalysisResult(source=source, uri=uri)
    try:
        module = parse_module(source)
        result.module = module
    except ParseError as exc:
        result.parse_error = exc
        return result
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    result.semantic_errors = list(analyzer.errors)
    result.semantic_warnings = list(analyzer.warnings)
    result.symbol_table = analyzer.symbol_table
    return result


# ------
# Diagnostic conversion
# ------


def _aster_to_lsp_position(line: int, col: int) -> types.Position:
    return types.Position(line=max(0, line - 1), character=col)


def to_lsp_diagnostics(result: AnalysisResult) -> list[types.Diagnostic]:
    diags: list[types.Diagnostic] = []
    if result.parse_error is not None:
        token = result.parse_error.token
        start = _aster_to_lsp_position(token.start.line, token.start.column)
        end = _aster_to_lsp_position(token.end.line, token.end.column)
        if start == end:
            end = types.Position(line=start.line, character=start.character + 1)
        diags.append(
            types.Diagnostic(
                range=types.Range(start=start, end=end),
                message=str(result.parse_error),
                severity=types.DiagnosticSeverity.Error,
                source="aster",
            )
        )
        return diags
    for sem_err in result.semantic_errors:
        diags.append(_sem_diag(sem_err, types.DiagnosticSeverity.Error))
    for sem_warn in result.semantic_warnings:
        diags.append(_sem_diag(sem_warn, types.DiagnosticSeverity.Warning))
    return diags


def _sem_diag(
    item: SemanticError | SemanticWarning, severity: types.DiagnosticSeverity
) -> types.Diagnostic:
    if item.node is not None and item.node.span is not None:
        start_line, end_line = item.node.span
        start = _aster_to_lsp_position(start_line, 0)
        end = _aster_to_lsp_position(end_line, 0)
    else:
        start = end = types.Position(line=0, character=0)
    return types.Diagnostic(
        range=types.Range(start=start, end=end),
        message=item.message,
        severity=severity,
        source="aster",
    )


# ------
# Hover helpers
# ------


def token_at_position(source: str, lsp_line: int, lsp_char: int) -> LexToken | None:
    aster_line = lsp_line + 1
    lexer = Lexer(source)
    try:
        while True:
            tok = lexer.next_token()
            if tok.kind == TokenKind.EOF:
                break
            if tok.kind != TokenKind.IDENTIFIER:
                continue
            if tok.start.line != aster_line:
                continue
            if tok.start.column <= lsp_char < tok.end.column:
                return tok
    except Exception:
        pass
    return None


def _find_symbols_named(scope: Scope, name: str) -> list[Symbol]:
    results: list[Symbol] = []
    sym = scope.symbols.get(name)
    if sym is not None:
        results.append(sym)
    for child in scope.children:
        results.extend(_find_symbols_named(child, name))
    return results


def _pick_symbol_at_line(symbols: list[Symbol], aster_line: int) -> Symbol | None:
    for sym in symbols:
        node = sym.declaration_node
        if node is not None and node.span is not None:
            start, end = node.span
            if start <= aster_line <= end:
                return sym
    return symbols[0] if symbols else None


def _format_symbol_markdown(symbol: Symbol) -> str:
    kind_label = symbol.kind.name.lower().replace("_", " ")
    mut = "mut " if symbol.is_mutable else ""
    return f"**{symbol.name}** *({kind_label})*\n\n```\n{mut}{symbol.name}: {symbol.type}\n```"


def hover_for_position(result: AnalysisResult, lsp_line: int, lsp_char: int) -> str | None:
    if result.symbol_table is None:
        return None
    tok = token_at_position(result.source, lsp_line, lsp_char)
    if tok is None:
        return None
    symbols = _find_symbols_named(result.symbol_table.global_scope, tok.text)
    if not symbols:
        return None
    sym = _pick_symbol_at_line(symbols, lsp_line + 1)
    if sym is None:
        return None
    return _format_symbol_markdown(sym)


# ------
# Go-to-definition helpers
# ------


def _name_column_in_line(line: str, name: str) -> int:
    m = re.search(r"\b" + re.escape(name) + r"\b", line)
    return m.start() if m else 0


def definition_for_position(
    result: AnalysisResult, lsp_line: int, lsp_char: int
) -> types.Location | None:
    if result.symbol_table is None:
        return None
    tok = token_at_position(result.source, lsp_line, lsp_char)
    if tok is None:
        return None
    symbols = _find_symbols_named(result.symbol_table.global_scope, tok.text)
    if not symbols:
        return None
    sym = _pick_symbol_at_line(symbols, lsp_line + 1)
    if sym is None:
        return None
    node = sym.declaration_node
    if node is None or node.span is None:
        return None
    decl_lsp_line = node.span[0] - 1
    source_lines = result.source.splitlines()
    if decl_lsp_line < len(source_lines):
        col = _name_column_in_line(source_lines[decl_lsp_line], sym.name)
    else:
        col = 0
    start = types.Position(line=decl_lsp_line, character=col)
    end = types.Position(line=decl_lsp_line, character=col + len(sym.name))
    return types.Location(uri=result.uri, range=types.Range(start=start, end=end))


# ------
# Language server
# ------

_SERVER_NAME = "aster-lang"
_SERVER_VERSION = "0.1.0"


class AsterLanguageServer(LanguageServer):  
    def __init__(self) -> None:
        super().__init__(
            _SERVER_NAME,
            _SERVER_VERSION,
            text_document_sync_kind=types.TextDocumentSyncKind.Full,
        )
        self._results: dict[str, AnalysisResult] = {}
        self._register_lsp_handlers()

    def _register_lsp_handlers(self) -> None:
        @self.feature(  
            types.TEXT_DOCUMENT_DID_OPEN
        )
        def did_open(_ls: AsterLanguageServer, params: types.DidOpenTextDocumentParams) -> None:
            self._analyse_and_publish(params.text_document.uri, params.text_document.text)

        @self.feature(  
            types.TEXT_DOCUMENT_DID_CHANGE
        )
        def did_change(_ls: AsterLanguageServer, params: types.DidChangeTextDocumentParams) -> None:
            if params.content_changes:
                text = params.content_changes[-1].text
                self._analyse_and_publish(params.text_document.uri, text)

        @self.feature(  
            types.TEXT_DOCUMENT_DID_CLOSE
        )
        def did_close(_ls: AsterLanguageServer, params: types.DidCloseTextDocumentParams) -> None:
            uri = params.text_document.uri
            self._results.pop(uri, None)
            self.text_document_publish_diagnostics(
                types.PublishDiagnosticsParams(uri=uri, diagnostics=[])
            )

        @self.feature(  
            types.TEXT_DOCUMENT_HOVER, types.HoverOptions()
        )
        def hover(_ls: AsterLanguageServer, params: types.HoverParams) -> types.Hover | None:
            uri = params.text_document.uri
            result = self._results.get(uri)
            if result is None:
                return None
            lsp_line, lsp_char = params.position.line, params.position.character
            markdown = hover_for_position(result, lsp_line, lsp_char)
            if markdown is None:
                return None
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=markdown,
                )
            )

        @self.feature(  
            types.TEXT_DOCUMENT_FORMATTING, types.DocumentFormattingOptions()
        )
        def formatting(
            _ls: AsterLanguageServer, params: types.DocumentFormattingParams
        ) -> list[types.TextEdit] | None:
            from aster_lang.formatter import format_source

            uri = params.text_document.uri
            result = self._results.get(uri)
            if result is None:
                return None
            source = result.source
            try:
                formatted = format_source(source)
            except ParseError:
                return None
            if formatted == source:
                return []
            lines = source.splitlines()
            end_line = max(0, len(lines) - 1)
            end_char = len(lines[end_line]) if lines else 0
            return [
                types.TextEdit(
                    range=types.Range(
                        start=types.Position(line=0, character=0),
                        end=types.Position(line=end_line, character=end_char),
                    ),
                    new_text=formatted,
                )
            ]

        @self.feature(  
            types.TEXT_DOCUMENT_DEFINITION, types.DefinitionOptions()
        )
        def definition(
            _ls: AsterLanguageServer, params: types.DefinitionParams
        ) -> types.Location | None:
            uri = params.text_document.uri
            result = self._results.get(uri)
            if result is None:
                return None
            return definition_for_position(result, params.position.line, params.position.character)

        @self.feature(  
            types.TEXT_DOCUMENT_COMPLETION, types.CompletionOptions()
        )
        def completion(
            _ls: AsterLanguageServer, params: types.CompletionParams
        ) -> list[types.CompletionItem] | None:
            uri = params.text_document.uri
            result = self._results.get(uri)
            if result is None or result.symbol_table is None:
                return None
            items: list[types.CompletionItem] = []
            for sym in result.symbol_table.global_scope.symbols.values():
                kind_map = {
                    SymbolKind.VARIABLE: types.CompletionItemKind.Variable,
                    SymbolKind.FUNCTION: types.CompletionItemKind.Function,
                    SymbolKind.TYPE_ALIAS: types.CompletionItemKind.Constant,
                    SymbolKind.TRAIT: types.CompletionItemKind.Interface,
                    SymbolKind.MODULE: types.CompletionItemKind.Module,
                    SymbolKind.EFFECT: types.CompletionItemKind.Keyword,
                    SymbolKind.PARAMETER: types.CompletionItemKind.Variable,
                }
                item = types.CompletionItem(
                    label=sym.name,
                    kind=kind_map.get(sym.kind, types.CompletionItemKind.Text),
                    insert_text=sym.name,
                    documentation=str(sym.type),
                )
                items.append(item)
            return items

    def _analyse_and_publish(self, uri: str, source: str) -> None:
        result = analyze_source(source, uri)
        self._results[uri] = result
        diags = to_lsp_diagnostics(result)
        self.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(uri=uri, diagnostics=diags)
        )
        logger.debug("Published %d diagnostic(s) for %s", len(diags), uri)

    # ------------------------------------------------------------------
    # Public accessors (useful in tests)
    # ------------------------------------------------------------------

    def get_result(self, uri: str) -> AnalysisResult | None:
        """Return the cached :class:`AnalysisResult` for *uri*, if any."""
        return self._results.get(uri)


# ------
# Boot helper
# ------


def start(*, stdio: bool = True, tcp_port: int | None = None) -> None:
    """Launch the language server.

    Parameters
    ----------
    stdio:
        Use stdio transport (default). When *False*, ``tcp_port`` must be set.
    tcp_port:
        TCP port to listen on when ``stdio=False``.
    """
    server = AsterLanguageServer()
    if stdio:
        server.start_io()
    else:
        if tcp_port is None:
            raise ValueError("tcp_port is required when stdio=False")
        server.start_tcp("127.0.0.1", tcp_port)


# ------
# Script entry point
# ------

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="Aster LSP server")
    transport = ap.add_mutually_exclusive_group()
    transport.add_argument(
        "--stdio", action="store_true", default=True, help="stdio transport (default)"
    )
    transport.add_argument("--tcp", type=int, metavar="PORT", help="TCP port")
    a = ap.parse_args()

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    start(stdio=a.tcp is None, tcp_port=a.tcp)

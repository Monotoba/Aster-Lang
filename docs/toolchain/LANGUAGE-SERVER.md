# Aster Language Server

The Aster Language Server implements the [Language Server Protocol (LSP)](https://microsoft.github.io/language-server-protocol/)
to provide IDE features for `.aster` files in any LSP-capable editor.
The primary target is **VS Code** via the companion extension in `editors/vscode/`.

---

## Current status

**Phase 3 — Diagnostics + Hover + Formatting + Go-to-definition — complete.**

| Capability | Status |
|-----------|--------|
| `textDocument/didOpen` → publish diagnostics | ✅ |
| `textDocument/didChange` → publish diagnostics | ✅ |
| `textDocument/didClose` → clear diagnostics | ✅ |
| Parse errors with token-precise ranges | ✅ |
| Semantic errors with span-level ranges | ✅ |
| Semantic warnings | ✅ |
| VS Code extension (syntax highlighting + diagnostics) | ✅ |
| `textDocument/hover` → symbol name, kind, type | ✅ |
| `textDocument/formatting` → canonical Aster source | ✅ |
| `textDocument/definition` → jump to declaration | ✅ |

Phases 4–5 (completion, find-references/rename) are documented below as
design targets.

---

## Architecture

```
Editor (VS Code)
     │  LSP (JSON-RPC over stdio)
     ▼
AsterLanguageServer          pygls 2.x LanguageServer subclass
     │  src/aster_lang/lsp/server.py
     │
     ├── analyze_source(source, uri) → AnalysisResult
     │       ├── parse_module()        → Module AST   (catches ParseError)
     │       └── SemanticAnalyzer()    → errors, warnings, symbol_table
     │
     ├── to_lsp_diagnostics(result) → list[Diagnostic]
     │       ├── ParseError   → token.start.{line,column} → precise range
     │       └── SemanticError/Warning → node.span.{start_line} → line range
     │
     ├── hover_for_position(result, lsp_line, lsp_char) → str | None
     │       ├── token_at_position()   → streaming lexer, find IDENTIFIER at cursor
     │       ├── _find_symbols_named() → DFS over scope tree
     │       ├── _pick_symbol_at_line() → prefer span-matching symbol
     │       └── _format_symbol_markdown() → name, kind, type as Markdown
     │
     ├── definition_for_position(result, lsp_line, lsp_char) → Location | None
     │       ├── token_at_position()   → find IDENTIFIER at cursor
     │       ├── _find_symbols_named() + _pick_symbol_at_line()
     │       └── _name_column_in_line() → word-boundary regex for precise column
     │
     └── handlers
           ├── didOpen      → analyze + publishDiagnostics
           ├── didChange    → analyze + publishDiagnostics  (Full sync)
           ├── didClose     → evict result + clear diagnostics
           ├── hover        → hover_for_position → Hover{MarkupContent}
           ├── formatting   → format_source → single TextEdit (whole doc)
           └── definition   → definition_for_position → Location
```

**Key design decisions:**

- **Full re-parse on every change.** Aster source files are small; a full
  lexer + parser + semantic pass on each `didChange` is fast enough.
  Incremental parsing is deferred.
- **No separate DocumentStore.** pygls manages open document text in
  `server.workspace`; the server adds a `_results: dict[str, AnalysisResult]`
  cache alongside it.
- **Pure analysis function.** `analyze_source()` never raises; all errors are
  captured in `AnalysisResult`.  This makes it trivially testable without any
  LSP plumbing.
- **stdio transport.** The server speaks JSON-RPC over stdin/stdout.
  TCP is also supported for debugging (`aster lsp --tcp PORT`).

---

## Package layout

```
src/aster_lang/lsp/
    __init__.py
    server.py          # Everything: AnalysisResult, analyze_source(),
                       # to_lsp_diagnostics(), AsterLanguageServer, start()
```

The single-file layout was chosen for Phase 1 simplicity.  Once hover,
definition, and completion providers are added each will move to its own
module.

---

## Position mapping

Aster source positions use **1-based** lines, **0-based** columns.
LSP uses **0-based** lines and characters.

```python
lsp_line = aster_line - 1   # line is 1-based in Aster
lsp_char = aster_col        # column is already 0-based
```

`ParseError` provides `token.start.{line, column}` and `token.end.{line, column}`
for precise character-level ranges.

`SemanticError` / `SemanticWarning` provide `node.span = (start_line, end_line)`.
Column information is not available, so diagnostics span the full line.

---

## CLI entry point

```bash
aster lsp              # stdio mode (used by editors)
aster lsp --tcp 2087   # TCP mode (used for debugging)
```

The `lsp` subcommand lazy-imports `aster_lang.lsp.server` so that `pygls`
is not required for any other `aster` subcommand.

---

## Dependencies

`pygls` is an optional dependency:

```toml
# pyproject.toml
[project.optional-dependencies]
lsp = ["pygls>=2.0"]
```

Install with:

```bash
pip install -e ".[lsp]"
```

---

## Testing

Tests live in `tests/test_lsp_server.py` (69 tests, five layers):

| Layer | What is tested |
|-------|---------------|
| Position helpers | `_aster_to_lsp_position` boundary cases |
| `analyze_source()` | valid input, parse errors, semantic errors |
| `to_lsp_diagnostics()` | severity, range, source field, one-diag-per-error |
| Server construction | name/version, feature registration (Phases 1–3) |
| `_analyse_and_publish()` | result stored, publish called, uri matches, error count |
| `didClose` handler | result evicted, diagnostics cleared |
| `token_at_position()` | identifier found at cursor, None for non-identifier positions |
| `hover_for_position()` | function/variable/builtin symbols, parse-error guard |
| formatting handler | TextEdit coverage, idempotent source returns `[]`, None on error |
| `definition_for_position()` | precise line+column, URI, builtin→None, parse-error→None |
| definition handler | registered, returns Location, None for unknown URI |

Run with:

```bash
pytest tests/test_lsp_server.py
```

---

## VS Code extension

The companion extension lives in `editors/vscode/`.
See [`editors/vscode/README.md`](../../editors/vscode/README.md) for full
installation and usage documentation.

**Summary:**
- Spawns `aster lsp --stdio` as a subprocess on activation.
- Connects via `vscode-languageclient` (TypeScript).
- Contributes the `aster` language for `.aster` files.
- Provides TextMate grammar (syntax highlighting) and language configuration
  (bracket matching, auto-indent, comment toggling) independently of the server.

---

## Planned phases

### Phase 2 — Hover and formatting ✅ complete

**Hover** (`textDocument/hover`): streams the Aster lexer to find the
IDENTIFIER token at the cursor, DFS-searches the scope tree for all symbols
with that name, picks the one whose declaration span contains the cursor line,
and returns name / kind / type as Markdown.

**Formatting** (`textDocument/formatting`): passes the document through
`format_source()`, returns a single `TextEdit` replacing the whole document.
Returns `[]` (no edit needed) when source is already canonical.

### Phase 3 — Go-to-definition

Identify the symbol at the cursor, look it up in the symbol table, return a
`Location` pointing to the declaration node.  Cross-file definitions use
`ModuleResolution`.

### Phase 4 — Completion

Build a `CompletionItem` list from scope-visible identifiers, imported module
exports, `NATIVE_MODULE_SYMBOLS` stdlib members, and Aster keywords.
Trigger on `.` for member completions.

### Phase 5 — Find references, rename, code actions

Requires workspace-wide indexing.  Deferred until Phase 3 is proven stable.

---

## Open questions

1. **UTF-16 character offsets** — Phase 1 diagnostics use byte column offsets.
   For non-ASCII source (identifiers with Unicode, string content) this diverges
   from the LSP spec.  A `utf16_column()` helper is needed before the extension
   is published publicly.
2. **Semantic token provider** — provides richer editor-controlled highlighting
   beyond the TextMate grammar.  Useful but deferred to Phase 4+.
3. **Cross-file completion** — Phase 4 completion covers only the current file.
   A workspace-wide symbol index is a Phase 5+ concern.

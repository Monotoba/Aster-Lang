# Aster Language Server

The Aster Language Server implements the [Language Server Protocol (LSP)](https://microsoft.github.io/language-server-protocol/)
to provide IDE features — diagnostics, hover, completion, go-to-definition, and formatting —
for any LSP-capable editor.  The primary target is **VS Code** via a companion extension.

---

## Architecture

The language server is a thin shell around the existing Aster pipeline.
No new parsing or analysis infrastructure is needed.

```
Editor (VS Code)
     │  LSP (JSON-RPC over stdio)
     ▼
aster_lang.lsp.server   ←── pygls AsterLanguageServer
     │
     ├── textDocument/didOpen | didChange | didSave
     │       │
     │       ▼
     │   DocumentStore           (in-memory source text per URI)
     │       │
     │       ├── Lexer + Parser  → Module AST  (parse errors → Diagnostics)
     │       │
     │       └── SemanticAnalyzer → symbol table, type map, error list
     │                                        (semantic errors → Diagnostics)
     │
     ├── textDocument/hover      → symbol table lookup → hover text
     ├── textDocument/definition → symbol table + module resolution → Location
     ├── textDocument/completion → scope walk → CompletionItem list
     └── textDocument/formatting → Formatter.format_source() → TextEdit list
```

**Key design decisions:**

- **Full re-parse on every change.** Aster source files are small; a full
  lexer + parser + semantic pass on each `textDocument/didChange` is fast enough.
  Incremental parsing is deferred to a future phase.
- **stdio transport.** The server process communicates over stdin/stdout.
  The VS Code extension spawns the process and connects to it.
- **`pygls`** is the server library.  It handles JSON-RPC framing, capability
  negotiation, and request/notification dispatch.
- **Package location:** `src/aster_lang/lsp/` (new subdirectory).
- **Entry point:** `aster lsp` CLI subcommand launches the server.

---

## Existing components and what they power

| Existing component | Reused for |
|--------------------|------------|
| `Lexer` | Token positions for semantic token hints |
| `Parser` / `ParseError` | Diagnostics (syntax errors) |
| `SemanticAnalyzer` / `analyzer.errors` | Diagnostics (semantic errors) |
| `SemanticAnalyzer.symbol_table` | Hover type info, completion candidates, go-to-definition |
| `ModuleResolution` | Cross-file go-to-definition |
| `Formatter.format_source()` | Document formatting |
| `NATIVE_MODULE_SYMBOLS` | Completion for stdlib module members |

---

## Feature phases

### Phase 1 — Diagnostics (highest value, lowest effort)

Re-run the full pipeline on every `didChange`/`didSave`.
Publish parse errors and semantic errors as LSP `Diagnostic` objects.

```
ParseError { message, token.line, token.col }
    → Diagnostic { range: {line-1, col-1} to EOL, severity: Error, message }

SemanticAnalyzer.errors  (list of strings with "at line N" suffix)
    → parse line number from error string
    → Diagnostic { range, severity: Error, message }
```

**LSP capabilities declared:**
```json
{ "textDocumentSync": { "change": 1 } }
```

**Deliverable:** errors appear inline in VS Code as squiggles within one keystroke.

---

### Phase 2 — Hover and document formatting

**Hover** (`textDocument/hover`):
Look up the identifier under the cursor in the semantic symbol table.
Return the symbol's name, kind, and type as a Markdown string.

```
cursor position → token at position → identifier name
    → symbol_table.lookup(name) → Symbol { kind, type }
    → "**fn** sum_to(n: Int) -> Int"
```

**Formatting** (`textDocument/formatting`):
Pass the full document text through `format_source(text)`.
Return the diff as a single `TextEdit` replacing the entire document.

**LSP capabilities declared:**
```json
{ "hoverProvider": true, "documentFormattingProvider": true }
```

---

### Phase 3 — Go-to-definition

**`textDocument/definition`:**
1. Identify the symbol name at the cursor position.
2. Look it up in the symbol table to find its declaration node.
3. If the declaration is in the current file, return a `Location` pointing to
   the declaration's source position.
4. If it is in an imported module, resolve the module path via
   `ModuleResolution` and return a cross-file `Location`.

```
cursor → identifier → symbol_table.lookup → Symbol.declaration_node
    → ast node source position → Location { uri, range }
```

**LSP capabilities declared:**
```json
{ "definitionProvider": true }
```

---

### Phase 4 — Completion

**`textDocument/completion`:**
Build a `CompletionItem` list from:
- All identifiers currently in scope (from `symbol_table` scope chain)
- All exported names of imported modules
- All `NATIVE_MODULE_SYMBOLS` members for known stdlib modules
- Aster keywords (`fn`, `mut`, `return`, `if`, `while`, `for`, `match`, …)

Trigger on `.` to filter to module/record member completions only.

**LSP capabilities declared:**
```json
{ "completionProvider": { "triggerCharacters": ["."] } }
```

---

### Phase 5 — Find references, rename, code actions (future)

- **Find references:** collect all `Identifier` nodes matching a name across
  the open document (and optionally the whole project).
- **Rename:** find references → batch `TextEdit` per file.
- **Code actions:** "add `mut`", "add type annotation", quick-fix from error index.

These require either a project-wide index or at minimum a full re-analysis of
all open files.  Defer until Phase 3 is proven stable.

---

## Line and column mapping

Aster source positions use **1-based** lines and columns (`token.line`, `token.col`).
LSP uses **0-based** lines and characters.

All position conversions follow the same rule:

```python
lsp_line = aster_line - 1
lsp_char = aster_col - 1
```

Characters are UTF-16 code units per LSP spec.  For ASCII-only source (the common
case) UTF-16 and UTF-8 character offsets are identical.  Non-ASCII character handling
is a known gap for Phase 1; a future fix can add a `utf16_offset(line, col)` helper.

---

## Package layout

```
src/aster_lang/lsp/
    __init__.py
    server.py          # AsterLanguageServer (pygls Application subclass)
    document_store.py  # DocumentStore: URI → source text + cached analysis result
    analysis.py        # AnalysisResult: AST, symbol table, error list for one file
    positions.py       # Aster ↔ LSP position conversion utilities
    providers/
        diagnostics.py # publish_diagnostics() helper
        hover.py       # hover_at(result, position) → HoverResult
        definition.py  # definition_at(result, position) → Location | None
        completion.py  # completions_at(result, position) → list[CompletionItem]
        formatting.py  # format_document(source) → list[TextEdit]
```

---

## VS Code extension

A minimal companion extension lives in `editors/vscode/`:

```
editors/vscode/
    package.json       # extension manifest: activationEvents, contributes.languages
    extension.js       # activates on *.aster, spawns `aster lsp`, connects client
    language-config.json  # comment chars, brackets, indentation rules
    syntaxes/
        aster.tmLanguage.json   # TextMate grammar for basic syntax highlighting
```

`extension.js` is ~30 lines:

```js
const { LanguageClient, TransportKind } = require('vscode-languageclient/node');

function activate(context) {
    const serverOptions = {
        command: 'python',
        args: ['-m', 'aster_lang.lsp', '--stdio'],
        transport: TransportKind.stdio,
    };
    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'aster' }],
    };
    const client = new LanguageClient('aster', 'Aster Language Server', serverOptions, clientOptions);
    client.start();
    context.subscriptions.push(client);
}

module.exports = { activate };
```

---

## CLI entry point

```bash
aster lsp          # start in stdio mode (used by editors)
aster lsp --tcp 2087   # start in TCP mode (used for debugging)
```

Add to `cli.py`:

```python
if args.command == "lsp":
    from aster_lang.lsp.server import start
    start(tcp_port=getattr(args, "tcp", None))
```

---

## Testing strategy

### Unit tests (`tests/test_lsp_*.py`)

Use `pygls`'s `LanguageServerProtocol` test helpers to send mock messages directly
without starting a subprocess:

```python
from aster_lang.lsp.server import AsterLanguageServer

def test_diagnostics_reported_for_parse_error():
    server = AsterLanguageServer()
    server.bf_text_document_did_open(make_did_open("fn (broken"))
    published = server.last_published_diagnostics()
    assert len(published) == 1
    assert published[0]["severity"] == 1  # Error
```

### Integration smoke test

A shell script opens a `.aster` file, sends a `didOpen`, waits for `publishDiagnostics`,
and checks the response — usable in CI without VS Code installed.

### Manual testing

1. `pip install pygls`
2. `python -m aster_lang.lsp --stdio`  (pipe LSP messages via stdin)
3. Or: install the VS Code extension in development mode (`F5` in VS Code)

---

## Implementation order

| Step | What to build | Estimated scope |
|------|--------------|-----------------|
| 1 | `pygls` dependency, `lsp/` package skeleton, `aster lsp` CLI stub | ~50 lines |
| 2 | `DocumentStore` + `AnalysisResult` (parse + analyze one file) | ~80 lines |
| 3 | `textDocument/didOpen|didChange|didClose` + `publishDiagnostics` | ~60 lines |
| 4 | Position utilities + `hover` provider | ~80 lines |
| 5 | `formatting` provider (trivial — wraps Formatter) | ~20 lines |
| 6 | `definition` provider (single-file; cross-file deferred) | ~60 lines |
| 7 | `completion` provider (scope identifiers + keywords) | ~100 lines |
| 8 | VS Code extension (`package.json` + `extension.js` + TM grammar) | ~150 lines |

Total implementation: roughly **700 lines** of new Python across the `lsp/` package
plus a small JS extension.  This fits comfortably in a single focused session.

---

## Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
lsp = ["pygls>=1.3"]
```

Install with `pip install -e ".[lsp]"`.  The core `aster_lang` package remains
importable without `pygls` installed; the `lsp/` subpackage imports `pygls`
only when the `aster lsp` command is invoked.

---

## Open questions

1. **`pygls` version compatibility** — `pygls` 1.x has a different API from 0.x.
   Pin to `>=1.3` and test against the latest release.
2. **UTF-16 character offsets** — Phase 1 ignores non-ASCII; add a proper
   `utf16_len()` helper before publishing the extension publicly.
3. **Cross-file analysis in completion** — Phase 4 completion only covers the
   current file's scope.  Workspace-wide symbol indexing is a Phase 5+ concern.
4. **Semantic token provider** — token-by-token syntax highlighting beyond the
   TextMate grammar is useful but can wait until Phase 4.

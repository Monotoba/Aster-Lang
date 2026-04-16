# Aster Language Server Development

## Overview

The Aster Language Server implements the Language Server Protocol (LSP) to provide IDE features such as diagnostics, hover, completion, go‑to‑definition, and formatting for Aster source files. It leverages the existing compiler pipeline (lexer, parser, semantic analyzer, formatter) so that core language behaviour remains a single source of truth.

The server runs as a separate process that communicates with an LSP client (e.g. VS Code) over **stdio** or **TCP**.

## Core architecture

```
Editor (VS Code)
 +   └─ LSP client (vscode-languageclient)
        │  JSON‑RPC over stdio/TCP
        ▼
AsterLanguageServer (pygls Application)
 ├─ DocumentStore       # Keeps source text per URI
 ├─ AnalysisResult
 │    ├─ AST
 │    ├─ SymbolTable
 │    └─ SemanticErrors
 ├─ Providers            # Request handlers
 │    ├─ diagnostics.py
 │    ├─ hover.py
 │    ├─ definition.py
 │    ├─ completion.py
 │    └─ formatting.py
 ├─ positions.py         # line/col ↔ LSP positions
 └─ utils.py             # helpers, conversions, LSP helpers
```

### Design decisions

1. **Full re‑parse on every change** – Aster files are typically short; the combined cost of lexer, parser, and semantic analysis is negligible compared to I/O. Incremental parsing is left for future phases.
2. **No separate index** – For diagnostics, hover, definition, completion we only store per‑document analysis. Cross‑file lookups use `ModuleResolution` on demand.
3. **Position mapping** – Aster uses 1‑based lines/cols; LSP uses 0‑based. The helper in `positions.py` performs the conversion and includes a stub for UTF‑16 offsets.
4. **Dependency isolation** – `pygls` is an optional dependency activated only when the `aster lsp` command is invoked.
5. **Testing strategy** – `pygls` provides a `LanguageServerProtocol` helper that allows unit tests to send synthetic requests without spawning a subprocess.

## Implementation roadmap

1. **Project scaffolding**
   * Add `src/aster_lang/lsp/__init__.py` and package metadata.
   * Add `[project.optional-dependencies].lsp = ["pygls>=1.3"]` to `pyproject.toml`.
2. **CLI entry point**
   * Update `src/aster_lang/cli.py` to expose a `lsp` subcommand.
3. **Server bootstrap**
   * Create `lsp/server.py` with a `AsterLanguageServer` subclass of `Application`.
   * Register capability options.
4. **Document store**
   * Implement `DocumentStore` to hold text and cached `AnalysisResult`.
5. **Analysis pipeline**
   * Wrap lexer/parser/semantic analyzer into a single callable.
   * Capture diagnostics.
6. **Providers**
   * Diagnostics: publish on `didOpen`, `didChange`, `didSave`.
   * Hover: lookup type from symbol table.
   * Definition: resolve symbol declaration location.
   * Formatting: call `Formatter.format_source()`.
   * Completion: scope‑based identifiers and keywords.
7. **Tests**
   * Unit tests for each provider using `LanguageServerProtocol`.
   * Smoke test script for CI.
8. **VS Code extension** (outside Python repo)
   * `editors/vscode/` directory provides a minimal extension that spins up the server.
9. **Documentation**
   * Update `docs/toolchain/LANGUAGE-SERVER.md` with architecture diagram.

## Testing & CI

* **Unit** – `pytest` will automatically discover tests in `tests/test_lsp_*.py`.
* **Integration** – A simple shell script can open a file, send LSP messages and assert diagnostics.
* **CI** – Add a job in `.github/workflows/build.yml` to run `pytest`, `ruff check`, and `mypy --strict`.

## Contribution checklist

- [ ] Add server package and CLI hook.
- [ ] Implement DocumentStore and AnalysisResult.
- [ ] Wire diagnostics provider.
- [ ] Add hover provider.
- [ ] Add definition provider.
- [ ] Add formatting and completion providers.
- [ ] Write unit tests for each provider.
- [ ] Verify that the VS Code extension can start the server.
- [ ] Update docs.

---

> **Note**: The implementation details can be expanded further in the design doc as code is written. Each provider should be accompanied by a short test suite.

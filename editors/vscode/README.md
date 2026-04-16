# Aster Language — VS Code Extension

Syntax highlighting, indentation support, and live diagnostics for the
[Aster programming language](https://github.com/aster-lang/aster-lang).

---

## Features

### Syntax highlighting

Full TextMate grammar for `.aster` files covering:

- Keywords (`fn`, `if`, `while`, `match`, `return`, `mut`, `pub`, `use`, …)
- Operators (`:=`, `<-`, `->`, `==`, `!=`, bitwise, reference types)
- Built-in types (`Int`, `Str`, `Bool`, `Float`, `List`)
- Constants (`true`, `false`, `nil`)
- String literals including escape sequences
- F-string interpolation (`f"hello {name}"`)
- Raw strings (`r"no \escapes"`)
- Integers (decimal, hex `0x…`, binary `0b…`), floats
- Line comments (`#`)
- Function names at definition and call sites

### Language configuration

- Auto-close brackets, parens, and quotes
- Indentation increases after `fn`, `if`, `else`, `while`, `for`, `match` lines ending in `:`
- `#` toggles line comments (`Ctrl+/` / `Cmd+/`)

### Live diagnostics (requires `aster` on PATH)

The extension spawns `aster lsp --stdio` as a background process and
communicates with it over the Language Server Protocol.

Errors and warnings appear as squiggles directly in the editor:

| Source | Severity | Example |
|--------|----------|---------|
| Parse error | Error (red) | `Expected `)` at line 3, column 12` |
| Semantic error | Error (red) | `Undefined variable 'x'` |
| Semantic warning | Warning (yellow) | Unused binding |

Diagnostics update on every keystroke.

---

## Requirements

| Requirement | Minimum version | Notes |
|-------------|----------------|-------|
| VS Code | 1.85 | |
| Python | 3.11 | Must be on `PATH` or in a venv |
| `aster` CLI | any | Install: `pip install aster-lang` or `pip install -e .` from the repo |
| `pygls` | 2.x | Installed automatically with `aster-lang[lsp]` |

If `aster` is not on your `PATH`, set `aster.serverPath` (see Settings below).

---

## Installation

### From a local build (development)

```bash
# 1. Clone the repo and install the Aster CLI with LSP extras
git clone https://github.com/aster-lang/aster-lang
cd aster-lang
pip install -e ".[lsp]"

# 2. Build the extension
cd editors/vscode
npm install
npm run compile

# 3a. Launch the Extension Development Host (no packaging needed)
#     Open editors/vscode/ in VS Code and press F5.

# 3b. Or install as a .vsix package
npm run package          # produces aster-lang-0.1.0.vsix
code --install-extension aster-lang-0.1.0.vsix
```

### From the VS Code Marketplace _(coming soon)_

Search for **Aster Language** in the Extensions panel.

---

## Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `aster.serverPath` | string | `"aster"` | Path to the `aster` executable. Useful when `aster` is not on `PATH` (e.g. inside a virtual environment). Example: `"/home/me/.venv/bin/aster"` |
| `aster.trace.server` | `"off"` \| `"messages"` \| `"verbose"` | `"off"` | Log JSON-RPC traffic between the extension and the language server. Use `"verbose"` when reporting bugs. Logs appear in *Output → Aster Language Server Trace*. |

---

## Commands

| Command | Description |
|---------|-------------|
| **Aster: Restart Language Server** (`aster.restartServer`) | Stop and restart the server process. Useful if the server becomes unresponsive. |

Access via the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`).

---

## Troubleshooting

### No diagnostics / "server failed to start"

1. Open the **Output** panel and select **Aster Language Server**.
2. Check whether `aster lsp --stdio` can be run manually in a terminal.
3. If `aster` is in a virtual environment, set `aster.serverPath` to the full
   path of the binary.

### Diagnostics are stale

Run **Aster: Restart Language Server** from the Command Palette.

### Enabling verbose logging

Set `aster.trace.server` to `"verbose"` in your VS Code settings, then check
the **Aster Language Server Trace** output channel.

---

## Roadmap

The extension automatically picks up new capabilities as the language server
gains them.  Planned additions:

| Phase | Feature | Status |
|-------|---------|--------|
| 2 | Hover — show inferred type and documentation for identifiers | ✅ |
| 2 | Document formatting (`Shift+Alt+F`) via the Aster formatter | ✅ |
| 3 | Go-to-definition (`F12`) for single-file and cross-module symbols | ✅ |
| 4 | Completion (`Ctrl+Space`) — scope identifiers, stdlib members, keywords | ✅ |
| 5 | Find references, rename symbol | planned |

---

## Development

```
editors/vscode/
├── src/
│   └── extension.ts          # Extension entry point (TypeScript)
├── syntaxes/
│   └── aster.tmLanguage.json # TextMate grammar
├── language-configuration/
│   └── aster.json            # Bracket matching, comment tokens, indent rules
├── package.json              # Extension manifest
├── tsconfig.json
└── out/                      # Compiled JS (git-ignored)
```

```bash
npm run compile   # one-shot build
npm run watch     # rebuild on save
npm run lint      # ESLint
npm run package   # produce .vsix
```

Tests for the language server itself live in the Python repo at
`tests/test_lsp_server.py`.  Run them with `pytest tests/test_lsp_server.py`.
